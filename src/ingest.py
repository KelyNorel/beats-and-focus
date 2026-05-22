"""
ingest.py
---------
Spotify API ingestion pipeline for beats-and-focus.

Downloads tracks and audio features for three groups using track search:
  A — Focus:   tracks associated with focus / deep work / ADHD music (treatment)
  B — Context: tracks associated with relax / chill / mood (control 1)
  C — Popular: trending / top / viral tracks (control 2)

- Spotify API: track search
- Musicae.io via RapidAPI: audio features (BPM, energy, valence, etc.) + popularity

Saves raw data to data/raw/tracks.csv
"""

import os
import time
import logging
import requests
import spotipy
import pandas as pd
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

TRACKS_PER_QUERY = 10
OUTPUT_DIR = "data/raw"

SEARCH_QUERIES = {
    "A_focus": [
        "ADHD focus music",
        "deep work music",
        "concentration beats",
        "study focus instrumental",
        "brain focus music",
        "flow state work music",
        "productivity music beats",
    ],
    "B_context": [
        "chill relax music",
        "acoustic mood music",
        "indie relax vibes",
        "evening wind down music",
        "coffee shop background music",
        "r&b chill vibes",
        "mellow instrumental music",
    ],
    "C_popular": [
        "top hits 2025",
        "viral music 2025",
        "pop hits chart",
        "trending music now",
        "billboard hot songs",
        "most streamed songs",
        "mainstream hits 2025",
    ],
}


# ── Spotify client ────────────────────────────────────────────────────────────
def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

    auth = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
    )
    return spotipy.Spotify(auth_manager=auth)


# ── RapidAPI headers ──────────────────────────────────────────────────────────
def get_rapidapi_headers():
    return {
        "x-rapidapi-key":  os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": os.getenv("RAPIDAPI_HOST"),
        "Content-Type":    "application/json",
    }


# ── Track search via Spotify ──────────────────────────────────────────────────
def search_tracks(sp, query, limit=10):
    tracks = []
    try:
        results = sp.search(q=query, type="track", limit=limit)
        items = results.get("tracks", {}).get("items", [])
        for track in items:
            if track is None or track.get("id") is None:
                continue
            artists = ", ".join([a["name"] for a in track.get("artists", [])])
            tracks.append({
                "track_id":    track["id"],
                "track_name":  track["name"],
                "artists":     artists,
                "duration_ms": track.get("duration_ms"),
                "explicit":    track.get("explicit"),
            })
    except Exception as e:
        log.warning(f"  Search error for '{query}': {e}")
    return tracks


# ── Audio features via Musicae.io ─────────────────────────────────────────────
def get_audio_features(track_ids):
    headers = get_rapidapi_headers()
    host = os.getenv("RAPIDAPI_HOST")
    features = []

    for track_id in track_ids:
        url = f"https://{host}/v1/audio-features/{track_id}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            f = response.json()
            if f is None:
                continue
            features.append({
                "track_id":         f.get("id"),
                "tempo":            f.get("tempo"),
                "energy":           f.get("energy"),
                "valence":          f.get("valence"),
                "danceability":     f.get("danceability"),
                "acousticness":     f.get("acousticness"),
                "instrumentalness": f.get("instrumentalness"),
                "speechiness":      f.get("speechiness"),
                "loudness":         f.get("loudness"),
                "mode":             f.get("mode"),
                "time_signature":   f.get("time_signature"),
            })
        except Exception as e:
            log.warning(f"  Audio features error for track {track_id}: {e}")
        time.sleep(0.3)

    return features


# ── Popularity via Musicae.io /v1/tracks/{id} ─────────────────────────────────
def get_popularity(track_ids):
    headers = get_rapidapi_headers()
    host = os.getenv("RAPIDAPI_HOST")
    popularity_data = []

    for track_id in track_ids:
        url = f"https://{host}/v1/tracks/{track_id}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            t = response.json()
            if t is None:
                continue
            popularity_data.append({
                "track_id":   t.get("id"),
                "popularity": t.get("popularity"),
            })
        except Exception as e:
            log.warning(f"  Popularity error for track {track_id}: {e}")
        time.sleep(0.3)

    return popularity_data


# ── Group ingestion ───────────────────────────────────────────────────────────
def ingest_group(sp, group_label, queries):
    log.info(f"\n{'='*50}")
    log.info(f"Group {group_label}")
    log.info(f"{'='*50}")

    all_tracks = []
    for query in queries:
        log.info(f"  Searching tracks: '{query}'")
        tracks = search_tracks(sp, query, limit=TRACKS_PER_QUERY)
        log.info(f"  Found {len(tracks)} tracks")
        all_tracks.extend(tracks)
        time.sleep(0.3)

    if not all_tracks:
        log.warning(f"  No tracks found for group {group_label}, skipping.")
        return pd.DataFrame()

    tracks_df = pd.DataFrame(all_tracks).drop_duplicates(subset="track_id")
    log.info(f"  Unique tracks after dedup: {len(tracks_df)}")
    track_ids = tracks_df["track_id"].tolist()

    # Audio features
    log.info(f"  Fetching audio features via Musicae.io...")
    features = get_audio_features(track_ids)
    if not features:
        log.warning(f"  No audio features returned for group {group_label}.")
        return pd.DataFrame()
    features_df = pd.DataFrame(features)

    # Popularity
    log.info(f"  Fetching popularity via Musicae.io...")
    popularity = get_popularity(track_ids)
    if not popularity:
        log.warning(f"  No popularity returned for group {group_label}.")
        return pd.DataFrame()
    popularity_df = pd.DataFrame(popularity)

    # Merge all
    merged = tracks_df.merge(features_df, on="track_id", how="inner")
    merged = merged.merge(popularity_df, on="track_id", how="left")
    merged["group"] = group_label
    log.info(f"  Tracks with full data: {len(merged)}")

    return merged


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sp = get_spotify_client()
    log.info("Spotify client initialized ✓")

    all_groups = []
    for group_label, queries in SEARCH_QUERIES.items():
        df = ingest_group(sp, group_label, queries)
        if not df.empty:
            all_groups.append(df)

    if not all_groups:
        log.error("No data collected. Check API credentials.")
        return

    final_df = pd.concat(all_groups, ignore_index=True)

    output_path = os.path.join(OUTPUT_DIR, "tracks.csv")
    final_df.to_csv(output_path, index=False)

    log.info(f"\n{'='*50}")
    log.info(f"✓ Saved {len(final_df)} tracks → {output_path}")
    log.info(f"\nGroup summary:")
    log.info(final_df.groupby("group")["track_id"].count().to_string())
    log.info(f"\nBPM summary by group:")
    log.info(final_df.groupby("group")["tempo"].describe()[["mean", "std", "min", "max"]].to_string())
    log.info(f"\nPopularity summary by group:")
    log.info(final_df.groupby("group")["popularity"].describe()[["mean", "std", "min", "max"]].to_string())


if __name__ == "__main__":
    main()
