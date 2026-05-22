"""
ingest.py
---------
Spotify data ingestion pipeline for beats-and-focus.

Uses Musicae.io via RapidAPI exclusively:
  - /v1/search      → track IDs + popularity
  - /v1/audio-features/{id} → BPM, energy, valence, etc.

Two groups only (A/B test):
  A — Focus:   tracks associated with focus / deep work / ADHD music (treatment)
  B — Context: tracks associated with relax / chill / mood (control)

Saves raw data to data/raw/tracks.csv
"""

import os
import time
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

TRACKS_PER_QUERY = 50   # Musicae.io supports up to 50
TARGET_PER_GROUP = 1200
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
        "focus instrumental beats",
        "work concentration music",
        "study beats instrumental",
        "deep concentration music",
        "focus binaural beats",
        "work music no lyrics",
        "study lofi focus",
        "cognitive focus music",
        "focus ambient music",
        "deep work instrumental",
        "study music concentration",
        "focus electronic music",
        "work productivity beats",
        "attention focus music",
        "study music 2025",
        "focus music for work",
        "instrumental study music",
        "deep focus ambient",
    ],
    "B_context": [
        "chill relax music",
        "acoustic mood music",
        "indie relax vibes",
        "evening wind down music",
        "coffee shop background music",
        "r&b chill vibes",
        "mellow instrumental music",
        "relaxing evening music",
        "calm background music",
        "indie folk relax",
        "soft acoustic songs",
        "chill jazz music",
        "ambient relax music",
        "evening chill playlist",
        "slow relaxing music",
        "peaceful background music",
        "soft piano relax",
        "chill bedroom music",
        "relaxing indie music",
        "mellow r&b music",
        "calm acoustic music",
        "background chill music",
        "relax evening songs",
        "soft background instrumental",
        "chill vibes music 2025",
    ],
}


# ── RapidAPI headers ──────────────────────────────────────────────────────────
def get_headers():
    return {
        "x-rapidapi-key":  os.getenv("RAPIDAPI_KEY"),
        "x-rapidapi-host": os.getenv("RAPIDAPI_HOST"),
        "Content-Type":    "application/json",
    }


# ── Search tracks via Musicae.io ──────────────────────────────────────────────
def search_tracks(query, limit=50):
    host = os.getenv("RAPIDAPI_HOST")
    url = f"https://{host}/v1/search"
    params = {"q": query, "type": "track", "limit": str(limit)}
    tracks = []
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        response.raise_for_status()
        items = response.json().get("tracks", {}).get("items", [])
        for track in items:
            if track is None or track.get("id") is None:
                continue
            artists = ", ".join([a["name"] for a in track.get("artists", [])])
            tracks.append({
                "track_id":    track["id"],
                "track_name":  track["name"],
                "artists":     artists,
                "popularity":  track.get("popularity"),
                "duration_ms": track.get("duration_ms"),
                "explicit":    track.get("explicit"),
            })
    except Exception as e:
        log.warning(f"  Search error for '{query}': {e}")
    return tracks


# ── Audio features via Musicae.io ─────────────────────────────────────────────
def get_audio_features(track_id):
    host = os.getenv("RAPIDAPI_HOST")
    url = f"https://{host}/v1/audio-features/{track_id}"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        f = response.json()
        if f is None:
            return None
        return {
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
        }
    except Exception as e:
        log.warning(f"  Audio features error for {track_id}: {e}")
        return None


# ── Group ingestion ───────────────────────────────────────────────────────────
def ingest_group(group_label, queries):
    log.info(f"\n{'='*50}")
    log.info(f"Group {group_label}")
    log.info(f"{'='*50}")

    # 1. Search tracks
    all_tracks = []
    seen_ids = set()
    for query in queries:
        if len(all_tracks) >= TARGET_PER_GROUP:
            break
        log.info(f"  Searching: '{query}'")
        tracks = search_tracks(query, limit=TRACKS_PER_QUERY)
        for t in tracks:
            if t["track_id"] not in seen_ids:
                seen_ids.add(t["track_id"])
                all_tracks.append(t)
        log.info(f"  Unique so far: {len(all_tracks)}")
        time.sleep(0.3)

    tracks_df = pd.DataFrame(all_tracks)
    log.info(f"  Total unique tracks: {len(tracks_df)}")

    # 2. Audio features
    log.info(f"  Fetching audio features...")
    features = []
    for i, track_id in enumerate(tracks_df["track_id"].tolist()):
        if i % 50 == 0:
            log.info(f"  Progress: {i}/{len(tracks_df)}")
        feat = get_audio_features(track_id)
        if feat:
            features.append(feat)
        time.sleep(0.3)

    features_df = pd.DataFrame(features)
    merged = tracks_df.merge(features_df, on="track_id", how="inner")
    merged["group"] = group_label
    log.info(f"  Tracks with full data: {len(merged)}")

    return merged


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_groups = []
    for group_label, queries in SEARCH_QUERIES.items():
        df = ingest_group(group_label, queries)
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
