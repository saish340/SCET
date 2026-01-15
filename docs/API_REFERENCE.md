# SCET API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently no authentication required. For production, implement appropriate security measures.

---

## Endpoints

### System

#### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database_connected": true,
  "ml_models_loaded": true,
  "data_collection_active": false,
  "timestamp": "2026-01-10T12:00:00Z"
}
```

#### System Statistics

```http
GET /stats
```

**Response:**
```json
{
  "database": {
    "total_works": 150,
    "total_searches": 500
  },
  "ml_model": {
    "training_samples": 75,
    "rolling_accuracy": 0.85
  },
  "search_engine": {
    "cached_embeddings": 200
  },
  "data_collection": {
    "is_running": false,
    "total_collected": 150
  }
}
```

---

### Search

#### AI-Powered Search

```http
POST /search
```

**Request Body:**
```json
{
  "query": "harry potter",
  "content_type": "book",
  "max_results": 10,
  "include_similar": true,
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "query": "harry potter",
  "corrected_query": null,
  "results": [
    {
      "id": 1,
      "title": "Harry Potter and the Philosopher's Stone",
      "creator": "J.K. Rowling",
      "publication_year": 1997,
      "content_type": "book",
      "copyright_status": "active",
      "similarity_score": 0.95,
      "source": "Open Library"
    }
  ],
  "total_found": 5,
  "search_time_ms": 250,
  "ai_explanation": "Found 5 results. Best match: 'Harry Potter and the Philosopher's Stone' with 95% relevance.",
  "suggestions": ["Works by J.K. Rowling", "More books"]
}
```

#### Quick Search (GET)

```http
GET /search?q=romeo+juliet&type=book&limit=5
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| q | string | Yes | Search query |
| type | string | No | Content type filter |
| limit | integer | No | Max results (1-50) |

#### Submit Search Feedback

```http
POST /search/feedback
```

**Request Body:**
```json
{
  "search_id": 123,
  "selected_result_id": 45,
  "was_correct": true,
  "correct_answer": null,
  "rating": 5
}
```

---

### Copyright Analysis

#### Analyze Copyright

```http
POST /analyze
```

**Request Body (by work_id):**
```json
{
  "work_id": 123,
  "jurisdiction": "US"
}
```

**Request Body (by details):**
```json
{
  "title": "Pride and Prejudice",
  "creator": "Jane Austen",
  "publication_year": 1813,
  "content_type": "book",
  "jurisdiction": "US"
}
```

**Response:**
```json
{
  "work_title": "Pride and Prejudice",
  "creator": "Jane Austen",
  "publication_year": 1813,
  "content_type": "book",
  "status": "public_domain",
  "expiry_date": null,
  "years_until_expiry": 0,
  "allowed_uses": [
    {
      "use_type": "personal",
      "is_allowed": true,
      "conditions": null,
      "confidence": 0.95
    },
    {
      "use_type": "commercial",
      "is_allowed": true,
      "conditions": null,
      "confidence": 0.95
    }
  ],
  "confidence_score": 0.95,
  "reasoning": "Work published in 1813, before 1929 (public domain threshold for US)",
  "uncertainties": [],
  "disclaimer": "This analysis is based on US copyright law...",
  "jurisdiction": "US"
}
```

#### Analyze by Work ID

```http
GET /analyze/{work_id}?jurisdiction=US
```

---

### Smart Tag

#### Generate Smart Tag

```http
POST /tag
```

**Request Body:**
```json
{
  "query": "romeo and juliet",
  "content_type": "book",
  "jurisdiction": "US",
  "include_ai_reasoning": true
}
```

**Response:**
```json
{
  "title": "Romeo and Juliet",
  "creator": "William Shakespeare",
  "publication_year": 1597,
  "content_type": "book",
  "status_emoji": "🌍",
  "status_text": "Public Domain - Free to Use",
  "status_color": "green",
  "expiry_date": null,
  "expiry_timeline": "Expired over 400 years ago",
  "allowed_uses_summary": [
    "✓ 👤 Personal Use",
    "✓ 📚 Educational Use",
    "✓ 💼 Commercial Use",
    "✓ 🔄 Remix/Adaptation"
  ],
  "confidence_score": 0.95,
  "confidence_level": "High",
  "ai_reasoning": "Analyzing 'Romeo and Juliet' by William Shakespeare. Creator is a historical/classical figure. Work published before 1900 (very likely public domain).",
  "data_sources": ["Wikipedia", "Live web scraping"],
  "generated_at": "2026-01-10T12:00:00Z",
  "tag_version": "1.0",
  "auto_update_enabled": true,
  "next_verification_date": "2026-02-10T12:00:00Z",
  "disclaimer": "This analysis is based on US copyright law...",
  "jurisdiction": "US"
}
```

#### Generate HTML Tag

```http
GET /tag/html?title=Romeo+and+Juliet&creator=Shakespeare&year=1597&jurisdiction=US
```

**Response:** HTML content suitable for embedding

#### Generate Compact Tag

```http
GET /tag/compact?title=Romeo+and+Juliet&jurisdiction=US
```

**Response:**
```json
{
  "tag": "🌍 [Public Domain - Free to Use] | Expired over 400 years ago | ● High confidence | US"
}
```

---

### Data Collection

#### Get Collection Status

```http
GET /data/status
```

**Response:**
```json
{
  "is_running": false,
  "total_sources_checked": 150,
  "new_entries_found": 150,
  "last_run_at": "2026-01-10T11:00:00Z",
  "next_scheduled_run": "2026-01-11T11:00:00Z",
  "current_source": null
}
```

#### Trigger Data Collection

```http
POST /data/collect?query=shakespeare&content_type=book
```

**Response:**
```json
{
  "status": "collection_complete",
  "works_collected": 12,
  "query": "shakespeare"
}
```

#### Force Update Work

```http
POST /data/update/{work_id}
```

---

### ML Model

#### Get Model Status

```http
GET /ml/status
```

**Response:**
```json
{
  "model_name": "copyright_predictor",
  "model_type": "binary_classifier",
  "version": "1.0",
  "is_active": true,
  "training_samples": 75,
  "accuracy": 0.85,
  "last_trained": "2026-01-10T10:00:00Z",
  "next_retrain_at": 25
}
```

#### Trigger Training

```http
POST /ml/train
```

#### Bootstrap Model

```http
POST /ml/bootstrap
```

---

### Works Database

#### List Works

```http
GET /works?skip=0&limit=20&content_type=book
```

**Response:**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 20,
  "works": [
    {
      "id": 1,
      "title": "Pride and Prejudice",
      "creator": "Jane Austen",
      "publication_year": 1813,
      "content_type": "book",
      "copyright_status": "public_domain",
      "source": "Open Library"
    }
  ]
}
```

#### Get Work by ID

```http
GET /works/{work_id}
```

---

### Jurisdictions

#### List Jurisdictions

```http
GET /jurisdictions
```

**Response:**
```json
[
  {"code": "US", "name": "United States"},
  {"code": "EU", "name": "European Union"},
  {"code": "UK", "name": "United Kingdom"},
  {"code": "CA", "name": "Canada"},
  {"code": "AU", "name": "Australia"},
  {"code": "JP", "name": "Japan"},
  {"code": "IN", "name": "India"}
]
```

#### Get Jurisdiction Details

```http
GET /jurisdictions/{code}
```

**Response:**
```json
{
  "code": "US",
  "name": "United States",
  "standard_duration": 70,
  "corporate_duration": 95,
  "anonymous_duration": 95,
  "public_domain_before": 1929,
  "requires_registration": false,
  "notes": "Copyright term varies based on publication date and registration status"
}
```

---

## Error Responses

All errors return consistent format:

```json
{
  "error": "Error description",
  "detail": "Detailed error message",
  "code": "ERROR_CODE"
}
```

**Common Status Codes:**
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

---

## Content Types

Valid content types:
- `book`
- `music`
- `film`
- `article`
- `image`
- `software`
- `artwork`

---

## Copyright Statuses

- `public_domain` - Free to use
- `expired` - Copyright has expired
- `likely_expired` - Probably expired, verify before commercial use
- `unknown` - Insufficient data
- `likely_active` - Probably protected
- `active` - Under copyright protection
