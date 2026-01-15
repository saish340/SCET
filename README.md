# SCET - Smart Copyright Expiry Tag System

## AI-Based Title Search and Self-Updating ML Model

<p align="center">
  <img src="docs/logo.png" alt="SCET Logo" width="200">
</p>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Overview

SCET (Smart Copyright Expiry Tag) is a research-grade AI system that:

- **Determines copyright ownership, permissions, and expiry**
- **Uses AI-based Title Search** (semantic search, spell correction, fuzzy matching)
- **Automatically collects, updates, and learns data from the internet**
- **Does NOT use any ready-made or static datasets**
- **Generates dynamic Smart Copyright Expiry Tags**

---

## 🎯 Key Features

### 1. AI-Based Title Search
- Natural language understanding for title queries
- Spell correction (e.g., "harry poter" → "Harry Potter")
- Semantic similarity matching using embeddings
- Fuzzy string matching for partial titles
- Multi-source search aggregation

### 2. Self-Updating Data Collection

- Live web scraping from multiple sources:
  - Open Library (books)
  - Wikipedia (general)
  - MusicBrainz (music)
  - IMDb (films)
- On-demand data fetching
- Periodic verification and updates
- Stores only metadata (no copyrighted content)

### 3. Machine Learning Model
- NLP-based feature extraction
- Incremental learning (improves with usage)
- No pre-trained copyright datasets
- Predicts:
  - Copyright status probability
  - Expiry timeline
  - Confidence scores

### 4. Smart Copyright Rule Engine
- Multi-jurisdiction support (US, EU, UK, CA, AU, JP, IN)
- Applies legal rules based on:
  - Publication year
  - Creator death year
  - Work type (corporate, anonymous)
- Calculates expiry dates

### 5. Smart Copyright Expiry Tag
- Human-readable output
- Status with emojis (🌍 ✅ 🔁 ❌)
- Allowed uses summary
- AI reasoning and confidence
- Auto-updating capability

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              SCET System                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │  Frontend   │    │   FastAPI   │    │  Database   │                  │
│  │  (Web UI)   │◄──►│   Backend   │◄──►│  (SQLite)   │                  │
│  └─────────────┘    └──────┬──────┘    └─────────────┘                  │
│                            │                                             │
│         ┌──────────────────┼──────────────────┐                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │  AI Search  │    │   ML Model  │    │    Rule     │                  │
│  │   Engine    │    │  Predictor  │    │   Engine    │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                  │                         │
│         │           ┌──────┴──────┐           │                         │
│         │           │  Smart Tag  │◄──────────┘                         │
│         │           │  Generator  │                                     │
│         │           └─────────────┘                                     │
│         ▼                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │    Spell    │    │  Semantic   │    │    Fuzzy    │                  │
│  │  Corrector  │    │   Matcher   │    │   Matcher   │                  │
│  └─────────────┘    └─────────────┘    └─────────────┘                  │
│                            │                                             │
│                     ┌──────┴──────┐                                     │
│                     │    Data     │                                     │
│                     │  Collector  │                                     │
│                     └──────┬──────┘                                     │
│                            │                                             │
│         ┌─────────────┬────┴────┬─────────────┐                         │
│         ▼             ▼         ▼             ▼                         │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐               │
│   │   Open    │ │ Wikipedia │ │MusicBrainz│ │   IMDb    │               │
│   │  Library  │ │           │ │           │ │           │               │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘               │
│                       (Live Web Sources)                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites
- Python 3.9 or higher
- pip package manager

### Backend Setup

```bash
# Clone or navigate to the project directory
cd SCET

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies (full)
pip install -r backend/requirements.txt

# OR minimal (no transformer models)
pip install -r backend/requirements-minimal.txt
```

### Run the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend Setup

The frontend is a static HTML/CSS/JS application. Simply open `frontend/index.html` in a browser, or serve it:

```bash
cd frontend
python -m http.server 3000
```

Then open http://localhost:3000

---

## 🚀 Usage

### Web Interface

1. Open the frontend in your browser
2. Enter a title in the search box (e.g., "Harry Potter", "Romeo and Juliet")
3. Select content type and jurisdiction if needed
4. Click Search
5. View results and click any result to generate a Smart Tag

### API Usage

#### Search for a Work

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "pride and prejudice", "max_results": 5}'
```

#### Generate Smart Tag

```bash
curl -X POST "http://localhost:8000/api/v1/tag" \
  -H "Content-Type: application/json" \
  -d '{"query": "romeo and juliet", "jurisdiction": "US"}'
```

#### Analyze Copyright

```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "creator": "George Orwell",
    "publication_year": 1949,
    "jurisdiction": "US"
  }'
```

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search` | POST | AI-powered title search |
| `/api/v1/search` | GET | Quick search with query params |
| `/api/v1/tag` | POST | Generate Smart Copyright Tag |
| `/api/v1/tag/html` | GET | Generate HTML-formatted tag |
| `/api/v1/analyze` | POST | Detailed copyright analysis |
| `/api/v1/works` | GET | List works in database |
| `/api/v1/jurisdictions` | GET | List supported jurisdictions |
| `/api/v1/ml/status` | GET | ML model status |
| `/api/v1/data/status` | GET | Data collection status |
| `/api/v1/health` | GET | System health check |

---

## 🧠 How the ML Model Works

### Feature Extraction

The model extracts features from work metadata:

1. **Year-based features**: Publication age, death year, time periods
2. **Title features**: Length, word count, edition indicators
3. **Creator features**: Corporate/individual, historical figures
4. **Content type**: One-hot encoded work types
5. **Likelihood features**: Rule-based probability estimates

### Incremental Learning

The model learns from:

1. **User feedback**: When users confirm correct results
2. **Verified data**: High-confidence scraped data
3. **Rule-based examples**: Known public domain works

### No Pre-trained Datasets

The model is initialized with domain knowledge weights (not trained data) and improves through actual usage. This ensures:

- No reliance on static copyright databases
- Continuous improvement
- Adaptability to new data

---

## 🌍 Supported Jurisdictions

| Code | Country | Duration (Standard) |
|------|---------|---------------------|
| US | United States | Life + 70 years |
| EU | European Union | Life + 70 years |
| UK | United Kingdom | Life + 70 years |
| CA | Canada | Life + 70 years |
| AU | Australia | Life + 70 years |
| JP | Japan | Life + 70 years |
| IN | India | Life + 60 years |

---

## 📋 Novelty Statement

> **"This system does not rely on pre-existing datasets. It uses AI-based live data acquisition and machine learning to dynamically infer copyright status and expiry, making it adaptive, scalable, and legally informative."**

### What Makes SCET Original:

1. **No Static Datasets**: All data is collected dynamically
2. **AI-Powered Search**: Not keyword matching, but semantic understanding
3. **Self-Learning**: ML model improves with each search
4. **Multi-Source Aggregation**: Combines multiple web sources
5. **Confidence Scoring**: Transparent about uncertainty
6. **Explainable AI**: Shows reasoning for predictions

---

## ⚠️ Disclaimer

This tool is for **informational and educational purposes only**. It does not constitute legal advice. Copyright law is complex and varies by jurisdiction. Always consult a qualified legal professional for definitive guidance on copyright matters.

---

## 🛠️ Development

### Project Structure

```
SCET/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── ai_search/        # Search engine, spell correction, semantic matching
│   │   ├── data_collection/  # Web scrapers, collectors, schedulers
│   │   ├── database/         # SQLAlchemy models, connections
│   │   ├── ml_model/         # ML predictor, features, trainer
│   │   ├── rule_engine/      # Copyright rules, smart tag generator
│   │   ├── config.py         # Configuration
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── utils.py          # Utility functions
│   │   └── main.py           # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── css/styles.css
│   ├── js/app.js
│   └── index.html
├── docs/                     # Documentation
└── README.md
```

### Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

**Built with ❤️ for Academic Research**
