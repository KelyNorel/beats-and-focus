# Do Music Tempo and Focus Playlists Affect Listening Engagement?
### A/B/C Multi-Arm Testing with Bayesian Analysis on Spotify API Data

Rigorous multi-arm A/B/C testing framework applied to Spotify track metadata,
investigating whether "focus" tracks — characterized by higher BPM —
drive greater listening engagement compared to context-based and general tracks,
as proxied by track popularity and audio feature profiles.

Combines frequentist and Bayesian methods to answer a deceptively simple question:
**does high-tempo music actually keep you working longer, or are you just the kind
of person who seeks it out?**

## Research Question

Productivity culture recommends high-BPM music for focus and deep work. Spotify
curates hundreds of "focus" playlists explicitly for this purpose. But does the
tempo itself drive engagement — or is it a confound? People who build focused work
habits may self-select into focus playlists regardless of BPM. This project tests
whether BPM and playlist type predict engagement at scale using observational data.

Two control groups are used to isolate the effect more cleanly than a standard A/B design.

## Dataset

**Source:** Spotify Web API (track search) + Musicae.io via RapidAPI (audio features)  
**Group A — Focus** (treatment): tracks matching queries like "ADHD focus music", "deep work music", "concentration beats"  
**Group B — Context** (control 1): tracks matching queries like "chill relax music", "coffee shop background music", "mellow instrumental"  
**Group C — Popular** (control 2): tracks matching queries like "top hits 2025", "viral music", "billboard hot songs"  
**Audio features per track:** `tempo` (BPM), `energy`, `valence`, `danceability`, `acousticness`, `instrumentalness`, `speechiness`, `loudness`  
**Engagement proxy:** track `popularity` (Spotify's 0-100 score)  
**Tracks collected:** 204 (A: 66, B: 68, C: 70)  
No audio files downloaded — metadata only. No personal user data involved.

## Data Pipeline

### Why two APIs?

Spotify deprecated its `/v1/audio-features` endpoint in November 2024, restricting
access to apps created before that date. New developer apps return a 403 Forbidden
error on this endpoint regardless of authentication.

The solution uses two APIs in tandem:

- **Spotify Web API** — track search is still available for free. Used to find
  tracks by query and retrieve basic metadata (name, artists, popularity, duration).
- **Musicae.io via RapidAPI** — an independent API that provides the same audio
  features Spotify deprecated (BPM, energy, valence, etc.), using Spotify track IDs
  as identifiers. Acts as a drop-in replacement.

This approach minimizes cost: Spotify handles the unlimited free search, while
Musicae.io is only called for audio features (one request per track).

### Why not use playlist data?

The original design planned to download focus playlists directly. Spotify's
November 2024 and February 2026 API changes also restricted playlist item access
for development mode apps, returning 403 errors even with OAuth authentication.
Track search (`/v1/search?type=track`) remains available and provides equivalent
data for this analysis.

### A note on sample size

With 204 tracks (~68 per group), the power analysis in Notebook 1 will determine
the minimum detectable effect. A second ingestion run with expanded queries and
pagination is planned to increase the sample to ~1,000+ tracks per group.

## Experimental Design

A standard A/B test comparing focus vs. a single control group risks a confound:
if the control is "chill" music, any BPM difference may simply reflect tempo differences
between calm and energetic music — not the focus intent. Two control groups address this:

- **A vs B** — isolates the focus intent effect (both are contextual playlists)
- **A vs C** — isolates the focus effect vs. the average Spotify listener
- **B vs C** — validates that context playlists differ from general ones

### Preliminary BPM snapshot (n=204)

| Group | Mean BPM | Std | Min | Max |
|-------|----------|-----|-----|-----|
| A — Focus | 114.6 | 37.2 | 57.5 | 194.8 |
| B — Context | 107.8 | 33.8 | 54.9 | 176.2 |
| C — Popular | 123.0 | 26.5 | 53.6 | 171.9 |

Interestingly, Group C (popular/mainstream) has the highest mean BPM — not Group A.
This early signal suggests the relationship between focus intent and tempo may be
more nuanced than expected.

## Analyses

### Notebook 1 — EDA & Power Analysis
- Distribution of BPM across focus vs context vs general tracks
- Audio feature profiles: how do the three groups differ beyond tempo?
- Popularity distributions across groups
- Power analysis: minimum detectable effect given current sample size

### Notebook 2 — Frequentist A/B/C Test
- Kruskal-Wallis test across three groups + pairwise Mann-Whitney U
- Effect size (rank-biserial r) for practical significance
- Subgroup analysis by audio feature clusters
- Multiple testing correction (Bonferroni) across pairwise comparisons

### Notebook 3 — Bayesian A/B/C Test
- Beta-Binomial conjugate model on binary engagement outcome
- Posterior distributions for P(A > B), P(A > C), P(B > C)
- Credible intervals for lift in popularity across all pairs

### Notebook 4 — Predictive Modeling
- Binary outcome: does a track exceed median popularity threshold?
- Models: Logistic Regression, Random Forest, Gradient Boosting
- SHAP analysis: where does `tempo` rank among all audio features?
- Key question: after controlling for energy, danceability, and speechiness —
  how much unique predictive power does BPM contribute?

## The Twist

Preliminary EDA shows focus tracks do not have the highest BPM — popular/mainstream
tracks do. And predictive modeling is expected to reveal further confounds: tracks
in each group differ not just in tempo but in energy, instrumentalness, and
speechiness. When you control for these features, the independent contribution of
BPM may shrink considerably.

**The lesson mirrors a parallel project on clinical trial enrollment nudges:**
observational data can make an intervention look powerful until you account for
what else differs between treatment and control groups.

> Correlation ≠ causation — whether you're running clinical trials or building a
> focus playlist.

## Stack

- **Python, pandas** — data ingestion and processing
- **spotipy** — Spotify Web API wrapper
- **requests** — Musicae.io API calls via RapidAPI
- **scipy** — frequentist hypothesis testing + Bayesian Beta-Binomial model
- **statsmodels** — multiple testing correction
- **scikit-learn, SHAP** — predictive modeling
- **Matplotlib, seaborn** — visualizations
- **JupyterLab** — documented analysis notebooks

## Project Structure

```
beats-and-focus/
├── data/
│   ├── raw/          # track metadata + audio features (not tracked in git)
│   └── processed/    # cleaned dataset (not tracked in git)
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_frequentist.ipynb
│   ├── 03_bayesian.ipynb
│   └── 04_predictive.ipynb
├── figures/          # saved plots
├── src/
│   └── ingest.py     # ingestion pipeline: Spotify search + Musicae.io features
├── .env              # API credentials (not tracked)
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

```bash
git clone https://github.com/KelyNorel/beats-and-focus.git
cd beats-and-focus
pyenv virtualenv 3.11 beats-and-focus
pyenv activate beats-and-focus
pip install -r requirements.txt
```

Add your API credentials to `.env`:

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_HOST=spotify-extended-audio-features-api.p.rapidapi.com
```

Then run the ingestion pipeline:

```bash
python src/ingest.py
```

---

**Author:** Raquel (Kely) Norel, PhD  
**Domain:** Behavioral Data Science / A/B Testing / Music & Productivity  
**Companion project:** [clinical-trial-nudges](https://github.com/KelyNorel/clinical-trial-nudges) — same methods, higher stakes  
**Status:** 🚧 In progress — data collected, notebooks pending
