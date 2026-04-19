# SCET - Smart Copyright Expiry Tag System

SCET is a multi-page web app for discovering copyright-related metadata, estimating protection status, and generating shareable validation reports for creative works.

It combines:

- A static frontend built with HTML, CSS, and vanilla JavaScript
- A Python serverless API for search, smart-tag generation, report data, and YouTube music-risk checks
- Public metadata and registry sources such as Open Library, Wikipedia, and copyright office search portals

## Features

### Search and discovery

- Fuzzy title matching with similarity-based ranking
- Type-aware filtering for books, music, film, artwork, software, and related categories
- Query correction and related suggestions
- Jurisdiction and source filtering
- Search-page recent report history stored in `localStorage`

### Copyright analysis

- Rule-based status prediction for `PROTECTED`, `PUBLIC_DOMAIN`, and `UNKNOWN` cases
- Jurisdiction-aware expiry estimates
- Confidence scoring and reasoning summaries
- Quick actions for verification, sharing, downloading, and opening full reports

### Report flow

- Shareable report pages via `/report`
- Printable report layout
- Allowed-use summary and consulted-source rendering

### YouTube music check

- Metadata-based copyright risk estimation for music usage
- MusicBrainz enrichment by default
- Optional Spotify metadata support through environment variables
- No hardcoded YouTube API key in the frontend

## Project structure

```text
SCET/
├── api/
│   ├── index.py
│   ├── pyproject.toml
│   └── requirements.txt
├── css/
│   └── styles.css
├── js/
│   ├── app-v3.js
│   ├── report.js
│   └── youtube-check.js
├── about.html
├── disclaimer.html
├── how-it-works.html
├── index.html
├── report.html
├── search.html
├── sources.html
├── vercel.json
├── youtube-check.html
└── README.md
```

## API endpoints

### Search

```bash
GET /api/v1/search?q={query}&jurisdiction={jurisdiction}&type={type}&source={source}
```

Returns ranked matches, correction hints, suggestions, and search explanation metadata.

### Detailed smart tag

```bash
GET /api/v1/tag/detailed?title={title}&year={year}&creator={creator}&jurisdiction={jurisdiction}&type={type}
```

Returns smart-tag data, recommendations, risk assessment, and legal checklist items.

### Report data

```bash
GET /api/v1/report?title={title}&year={year}&creator={creator}&type={type}&jurisdiction={jurisdiction}&source={source}
```

Returns structured data used by `report.html`.

### YouTube music risk check

```bash
GET /api/youtube-check?title={title}&artist={artist}
```

Returns a metadata-based risk estimate for using a song on YouTube.

### Health check

```bash
GET /api/v1/health
```

## Local development

### Frontend

Open `index.html` directly for static page work, or serve the repo root with any local static server if you want cleaner routing behavior.

### Backend

Install Python dependencies from the repo root or from `api/` depending on your setup:

```bash
pip install -r requirements.txt
```

Optional environment variables:

```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

These are only needed for Spotify metadata enrichment in the YouTube music checker.

## Deployment

The app is configured for Vercel:

- Static pages are served directly
- `/api/:path*` is rewritten to the Python serverless handler
- `/youtube-check` and `/report` are rewritten to their HTML pages

## Notes

- This project provides informational analysis, not legal advice.
- Official records and qualified legal review should be used for any real legal decision.
