# SCET Technical Documentation

## System Components

### 1. AI Search Engine (`app/ai_search/`)

#### Search Engine (`search_engine.py`)
The main orchestrator for intelligent search:

- **Multi-strategy search**: Combines exact, fuzzy, and semantic matching
- **Spell correction integration**: Automatically corrects typos
- **Web data collection**: Fetches new data when needed
- **Ranking**: Uses weighted scoring from multiple signals
- **Explanation generation**: Creates human-readable explanations

#### Spell Corrector (`spell_corrector.py`)
Handles misspellings and typos:

- **Known corrections**: Pre-defined common misspellings
- **Edit distance**: Levenshtein-based word correction
- **Phonetic matching**: Soundex algorithm for pronunciation-based errors
- **Learning**: Updates vocabulary from successful searches
- **Word splitting**: Handles concatenated words (e.g., "harrypotter")

#### Semantic Matcher (`semantic_search.py`)
Provides semantic similarity search:

- **Embeddings**: Uses sentence-transformers for text embeddings
- **TF-IDF fallback**: Works without transformer models
- **Cosine similarity**: Finds semantically similar titles
- **Batch processing**: Efficient embedding computation

### 2. Data Collection (`app/data_collection/`)

#### Scrapers (`scrapers.py`)
Web scrapers for different sources:

- **OpenLibraryScraper**: Books from Open Library API
- **WikipediaScraper**: General information from Wikipedia
- **MusicBrainzScraper**: Music metadata from MusicBrainz
- **IMDbScraper**: Film information from IMDb
- **WebScraper**: Unified interface for all scrapers

Features:
- Rate limiting to respect servers
- Error handling and retries
- Confidence scoring
- Async operation

#### Collector (`collector.py`)
Orchestrates data collection:

- **On-demand collection**: Triggered by searches
- **Deduplication**: Prevents duplicate entries
- **Confidence-based updates**: Higher confidence data wins
- **Metadata-only storage**: No copyrighted content stored

#### Scheduler (`scheduler.py`)
Periodic data updates:

- **Stale data detection**: Finds outdated entries
- **Re-verification**: Checks sources for updates
- **Background operation**: Non-blocking updates

### 3. ML Model (`app/ml_model/`)

#### Feature Extractor (`features.py`)
Extracts features for ML:

Features extracted:
1. **Year features** (11 features): Age, decades, time periods, death year
2. **Title features** (6 features): Length, word count, edition markers
3. **Creator features** (4 features): Corporate, classical, alive probability
4. **Type features** (8 features): One-hot content type
5. **Likelihood features** (4 features): Rule-based probabilities

Total: 33 features

#### Predictor (`predictor.py`)
ML model for copyright prediction:

- **Binary classification**: Predicts public domain probability
- **Domain-initialized weights**: Not random, uses legal knowledge
- **Incremental learning**: Updates with each verified example
- **Confidence scoring**: Based on prediction and data quality
- **Explainability**: Shows feature importance

#### Trainer (`trainer.py`)
Manages model training:

- **Sample collection**: Accumulates training examples
- **Batch training**: Trains when threshold reached
- **Feedback integration**: Learns from user corrections
- **Bootstrapping**: Initial training from legal rules

### 4. Rule Engine (`app/rule_engine/`)

#### Rule Engine (`rule_engine.py`)
Applies copyright law:

Jurisdiction rules:
- Standard duration (life + X years)
- Corporate work duration
- Anonymous work duration
- Public domain thresholds
- Registration requirements

Analysis includes:
- Status determination
- Expiry calculation
- Allowed uses
- ML integration
- Uncertainty identification

#### Smart Tag Generator (`smart_tag.py`)
Creates output tags:

Tag contents:
- Title and creator info
- Status with emoji
- Expiry timeline
- Allowed uses summary
- Confidence score
- AI reasoning
- Legal disclaimer

Output formats:
- Full SmartTag object
- Compact single-line
- HTML for embedding

### 5. Database (`app/database/`)

#### Models (`models.py`)
SQLAlchemy ORM models:

- **WorkMetadata**: Creative work information
- **SearchLog**: Search history for learning
- **MLModelState**: Model training state
- **CopyrightRule**: Jurisdiction rules
- **DataSource**: Source reliability tracking

### 6. API (`app/api/`)

#### Routes (`routes.py`)
FastAPI endpoints:

Categories:
- System (health, stats)
- Search (AI search, feedback)
- Analysis (copyright analysis)
- Smart Tag (generation)
- Data Collection (status, triggers)
- ML Model (status, training)
- Works (database access)
- Jurisdictions (rule info)

---

## Data Flow

### Search Flow

```
User Query
    ↓
Spell Correction
    ↓
Database Search ─── Semantic Matching
    ↓                    ↓
Insufficient Results?
    ↓ Yes
Web Scraping
    ↓
Result Ranking
    ↓
AI Explanation Generation
    ↓
Response
```

### Tag Generation Flow

```
Work Data
    ↓
┌───────────────────┬───────────────────┐
│   ML Prediction   │   Rule Analysis   │
│   (Probability)   │   (Legal Logic)   │
└─────────┬─────────┴─────────┬─────────┘
          │                   │
          └─────────┬─────────┘
                    ↓
           Combined Analysis
                    ↓
            Status Determination
                    ↓
           Expiry Calculation
                    ↓
           Allowed Uses Check
                    ↓
           Confidence Scoring
                    ↓
            Smart Tag Output
```

---

## Configuration

### Environment Variables

Create `.env` file in backend directory:

```env
DEBUG=True
DATABASE_URL=sqlite:///./scet_database.db
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MIN_SIMILARITY_THRESHOLD=0.6
SCRAPING_DELAY=1.0
MAX_SEARCH_RESULTS=20
DATA_UPDATE_INTERVAL_HOURS=24
DEFAULT_COPYRIGHT_DURATION_YEARS=70
```

### Model Configuration

In `config.py`:

```python
# ML Model Settings
MODEL_PATH = Path("./models")
FUZZY_MATCH_THRESHOLD = 70
RETRAIN_THRESHOLD = 100  # Samples before retraining
MIN_CONFIDENCE_SCORE = 0.5
```

---

## Extending the System

### Adding a New Scraper

1. Create class extending `BaseScraper`
2. Implement `search()` and `get_details()` methods
3. Add to `WebScraper.scrapers` dictionary

```python
class NewSourceScraper(BaseScraper):
    BASE_URL = "https://example.com"
    
    @property
    def source_name(self) -> str:
        return "New Source"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        # Implementation
        pass
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        # Implementation
        pass
```

### Adding a New Jurisdiction

Add to `JURISDICTION_RULES` in `rule_engine.py`:

```python
"XX": JurisdictionRules(
    code="XX",
    name="Country Name",
    standard_duration=70,
    corporate_duration=95,
    anonymous_duration=95,
    public_domain_before=None,
    requires_registration=False,
    notes="Special rules..."
)
```

### Adding New Features to ML

1. Add feature extraction in `features.py`
2. Update `get_feature_names()` and `get_feature_count()`
3. Add initial weight in `predictor.py._get_initial_weights()`

---

## Performance Considerations

### Caching
- Embeddings are cached in memory
- Database queries use indexes
- Repeated searches benefit from stored data

### Rate Limiting
- Web scrapers have configurable delays
- Parallel scraping is limited
- Respects robots.txt and API limits

### Scalability
- SQLite suitable for single-server
- PostgreSQL recommended for production
- Async operations throughout
- Background task processing

---

## Security Notes

- No copyrighted content is stored
- Web scraping respects rate limits
- User input is sanitized
- Database uses parameterized queries
- API has error handling

---

## Troubleshooting

### Common Issues

1. **"sentence-transformers not found"**
   - Install full requirements or use minimal mode
   - System falls back to TF-IDF automatically

2. **"No results found"**
   - Check internet connectivity
   - Web sources may be rate-limited
   - Try different search terms

3. **"Low confidence scores"**
   - Normal for unknown works
   - More data improves accuracy
   - Check if year/creator info is available

4. **"API not reachable"**
   - Ensure backend is running
   - Check port 8000 is available
   - Verify CORS settings
