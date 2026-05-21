# Do Music Tempo and Focus Playlists Affect Listening Engagement?
### A/B/C Multi-Arm Testing with Bayesian Analysis on Spotify API Data

Rigorous multi-arm A/B/C testing framework applied to Spotify playlist and track data,
investigating whether "focus" playlists — characterized by higher BPM and
lower variability — drive greater listening engagement compared to context-based
and general playlists, as proxied by track popularity, audio feature profiles,
and follower counts.

Combines frequentist and Bayesian methods to answer a deceptively simple question:
**does high-tempo music actually keep you working longer, or are you just the kind
of person who seeks it out?**

## Research Question

Productivity culture recommends high-BPM music for focus and deep work. Spotify
curates hundreds of "focus" playlists explicitly for this purpose. But does the
tempo itself drive engagement — or is it a confound? People who build focused work
habits may self-select into focus playlists regardless of BPM. This project tests
whether BPM and playlist type predict engagement at scale using observational data
from the Spotify API.

Two control groups are used to isolate the effect more cleanly than a standard A/B design.

## Dataset

**Source:** [Spotify Web API](https://developer.spotify.com/documentation/web-api)  
**Group A — Focus** (treatment): curated "focus" / "work" / "study" playlists  
**Group B — Context** (control 1): contextual playlists without work intent — "chill", "relax", "workout"  
**Group C — Popular** (control 2): Spotify's top general playlists — representative of the average listener  
**Audio features per track:** `tempo` (BPM), `energy`, `valence`, `danceability`, `acousticness`, `instrumentalness`  
**Engagement proxies:** track `popularity`, playlist `followers`  
No personal user data involved — all data publicly available via Spotify API.

## Experimental Design

A standard A/B test comparing focus vs. a single control group risks a confound:
if the control is "chill" music, any BPM difference may simply reflect tempo differences
between calm and energetic music — not the focus intent. Two control groups address this:

- **A vs B** — isolates the focus intent effect (both are contextual playlists)
- **A vs C** — isolates the focus effect vs. the average Spotify listener
- **B vs C** — validates that context playlists differ from general ones

## Analyses

### Notebook 1 — EDA & Power Analysis
- Distribution of BPM across focus vs context vs general playlists
- Audio feature profiles: how do the three groups differ beyond tempo?
- Follower distributions and popularity patterns
- Power analysis: minimum detectable effect given available sample size

### Notebook 2 — Frequentist A/B/C Test
- Kruskal-Wallis test across three groups + pairwise Mann-Whitney U
- Effect size (rank-biserial r) for practical significance
- Subgroup analysis by audio feature clusters
- Multiple testing correction (Bonferroni) across pairwise comparisons

### Notebook 3 — Bayesian A/B/C Test
- Beta-Binomial conjugate model on binary engagement outcome
- Posterior distributions for P(A > B), P(A > C), P(B > C)
- Credible intervals for lift in popularity and follower count across all pairs

### Notebook 4 — Predictive Modeling
- Binary outcome: does a track exceed median popularity threshold?
- Models: Logistic Regression, Random Forest, Gradient Boosting
- SHAP analysis: where does `tempo` rank among all audio features?
- Key question: after controlling for genre, energy, and instrumentalness —
  how much unique predictive power does BPM contribute?

## The Twist

Preliminary EDA shows focus playlists have higher BPM *and* higher engagement metrics.
But predictive modeling reveals the confound: focus playlists also tend to be
highly instrumental, lower valence, and curated by major labels with large follower
bases. When you control for these features, the independent contribution of BPM
shrinks considerably.

**The lesson mirrors a parallel project on clinical trial enrollment nudges:**
observational data can make an intervention look powerful until you account for
what else differs between treatment and control groups.

> Correlation ≠ causation — whether you're running clinical trials or building a
> focus playlist.

## Stack

- **Python, pandas** — data ingestion and processing
- **spotipy** — Spotify Web API wrapper
- **scipy** — frequentist hypothesis testing + Bayesian Beta-Binomial model
- **statsmodels** — multiple testing correction
- **scikit-learn, SHAP** — predictive modeling
- **Matplotlib, seaborn** — visualizations
- **JupyterLab** — documented analysis notebooks

## Project Structure

```
beats-and-focus/
├── data/
│   ├── raw/          # Spotify API JSON (not tracked in git)
│   └── processed/    # cleaned dataset (not tracked in git)
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_frequentist.ipynb
│   ├── 03_bayesian.ipynb
│   └── 04_predictive.ipynb
├── figures/          # saved plots
├── src/
│   └── ingest.py     # Spotify API ingestion pipeline
├── .env              # Spotify credentials (not tracked)
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

```bash
git clone https://github.com/KelyNorel/beats-and-focus.git
cd beats-and-focus
pyenv virtualenv 3.11 beats-and-focus
pyenv local beats-and-focus
pip install -r requirements.txt
```

Add your Spotify credentials to `.env`:

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

Then run the ingestion pipeline:

```bash
python src/ingest.py
```

---

**Author:** Raquel (Kely) Norel, PhD  
**Domain:** Behavioral Data Science / A/B Testing / Music & Productivity  
**Companion project:** [clinical-trial-nudges](https://github.com/KelyNorel/clinical-trial-nudges) — same methods, higher stakes  
**Status:** 🚧 In progress
