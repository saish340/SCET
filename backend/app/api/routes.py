"""
FastAPI Routes for SCET
All API endpoints for search, analysis, and tag generation
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging

from ..database.connection import get_db
from ..database.models import WorkMetadata, SearchLog
from ..ai_search.search_engine import get_search_engine
from ..data_collection.collector import get_collector
from ..data_collection.scheduler import get_scheduler
from ..ml_model.predictor import get_predictor
from ..ml_model.trainer import get_trainer
from ..rule_engine.rule_engine import get_rule_engine
from ..rule_engine.smart_tag import get_tag_generator
from ..schemas import (
    SearchRequest, SearchResponse, SearchResult,
    CopyrightAnalysisRequest, CopyrightAnalysisResponse,
    SmartTagRequest, SmartTag, ContentType, CopyrightStatus,
    TrainingFeedback, ModelStatus, DataCollectionStatus,
    HealthCheck, ErrorResponse, AllowedUsage
)
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Health & Status ============

@router.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check(db: Session = Depends(get_db)):
    """Check system health status"""
    try:
        # Check database
        db.execute("SELECT 1")
        db_connected = True
    except:
        db_connected = False
    
    # Check ML model
    predictor = get_predictor()
    ml_loaded = predictor.get_model_stats().get('feature_count', 0) > 0
    
    # Check data collection
    collector = get_collector()
    collection_status = collector.get_status()
    
    return HealthCheck(
        status="healthy" if db_connected and ml_loaded else "degraded",
        version=settings.APP_VERSION,
        database_connected=db_connected,
        ml_models_loaded=ml_loaded,
        data_collection_active=collection_status.get('is_running', False),
        timestamp=datetime.utcnow()
    )


@router.get("/stats", tags=["System"])
async def get_system_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    work_count = db.query(WorkMetadata).count()
    search_count = db.query(SearchLog).count()
    
    predictor = get_predictor()
    ml_stats = predictor.get_model_stats()
    
    search_engine = get_search_engine()
    search_stats = search_engine.get_stats()
    
    collector = get_collector()
    collection_stats = collector.get_status()
    
    return {
        "database": {
            "total_works": work_count,
            "total_searches": search_count
        },
        "ml_model": ml_stats,
        "search_engine": search_stats,
        "data_collection": collection_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============ AI Search ============

@router.post("/search", response_model=SearchResponse, tags=["Search"])
async def ai_search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    AI-powered title search
    - Handles misspellings and partial titles
    - Returns semantically similar results
    - Collects new data from web if needed
    """
    search_engine = get_search_engine()
    
    try:
        response = await search_engine.search(
            query=request.query,
            content_type=request.content_type.value if request.content_type else None,
            max_results=request.max_results,
            include_web_results=request.include_similar,
            session_id=request.session_id,
            db=db
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse, tags=["Search"])
async def quick_search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    type: Optional[str] = Query(None, description="Content type filter"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    db: Session = Depends(get_db)
):
    """Quick search endpoint with query parameters"""
    search_engine = get_search_engine()
    
    response = await search_engine.search(
        query=q,
        content_type=type,
        max_results=limit,
        include_web_results=True,
        db=db
    )
    
    return response


@router.post("/search/feedback", tags=["Search"])
async def submit_search_feedback(
    feedback: TrainingFeedback,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit feedback on search results for model improvement"""
    search_engine = get_search_engine()
    
    # Record selection for learning
    log = db.query(SearchLog).filter(SearchLog.id == feedback.search_id).first()
    if log:
        search_engine.learn_from_selection(log.query_text, feedback.selected_result_id, db)
    
    # Update log with feedback
    search_engine.provide_feedback(
        search_id=feedback.search_id,
        rating=feedback.rating or 0,
        was_correct=feedback.was_correct,
        db=db
    )
    
    # Queue for ML training
    if feedback.was_correct:
        trainer = get_trainer()
        work = db.query(WorkMetadata).filter(WorkMetadata.id == feedback.selected_result_id).first()
        if work and work.copyright_status:
            try:
                status = CopyrightStatus(work.copyright_status)
                trainer.add_training_sample(
                    title=work.title,
                    actual_status=status,
                    creator=work.creator,
                    publication_year=work.publication_year,
                    creator_death_year=work.creator_death_year,
                    content_type=work.content_type,
                    source="user_feedback"
                )
            except ValueError:
                pass
    
    return {"status": "feedback_recorded"}


# ============ Copyright Analysis ============

@router.post("/analyze", response_model=CopyrightAnalysisResponse, tags=["Analysis"])
async def analyze_copyright(
    request: CopyrightAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze copyright status for a work
    Combines ML prediction with legal rules
    """
    # If work_id provided, get from database
    if request.work_id:
        work = db.query(WorkMetadata).filter(WorkMetadata.id == request.work_id).first()
        if not work:
            raise HTTPException(status_code=404, detail="Work not found")
        
        title = work.title
        creator = work.creator
        publication_year = work.publication_year
        creator_death_year = work.creator_death_year
        content_type = work.content_type
    else:
        title = request.title or "Unknown"
        creator = request.creator
        publication_year = request.publication_year
        creator_death_year = None
        content_type = request.content_type.value if request.content_type else None
    
    # Get ML prediction
    predictor = get_predictor()
    ml_prediction = predictor.predict(
        title=title,
        creator=creator,
        publication_year=publication_year,
        creator_death_year=creator_death_year,
        content_type=content_type,
        jurisdiction=request.jurisdiction
    )
    
    # Get rule-based analysis
    rule_engine = get_rule_engine()
    rule_analysis = rule_engine.analyze(
        title=title,
        creator=creator,
        publication_year=publication_year,
        creator_death_year=creator_death_year,
        content_type=content_type,
        jurisdiction=request.jurisdiction,
        ml_prediction=ml_prediction
    )
    
    # Build response
    allowed_uses = []
    for use in rule_analysis.get('allowed_uses', []):
        allowed_uses.append(AllowedUsage(
            use_type=use['use_type'],
            is_allowed=use['is_allowed'],
            conditions=use.get('conditions'),
            confidence=use.get('confidence', 0.5)
        ))
    
    return CopyrightAnalysisResponse(
        work_title=title,
        creator=creator,
        publication_year=publication_year,
        content_type=content_type,
        status=rule_analysis['status'],
        expiry_date=rule_analysis.get('expiry_date'),
        years_until_expiry=rule_analysis.get('years_until_expiry'),
        allowed_uses=allowed_uses,
        confidence_score=rule_analysis['confidence'],
        reasoning=rule_analysis['reasoning'],
        uncertainties=rule_analysis.get('uncertainties', []),
        disclaimer=f"This analysis is based on {request.jurisdiction} copyright law. "
                   "Consult a legal professional for definitive advice.",
        jurisdiction=request.jurisdiction
    )


@router.get("/analyze/{work_id}", response_model=CopyrightAnalysisResponse, tags=["Analysis"])
async def analyze_work_by_id(
    work_id: int,
    jurisdiction: str = Query("US", description="Jurisdiction for copyright rules"),
    db: Session = Depends(get_db)
):
    """Analyze copyright for a specific work by ID"""
    request = CopyrightAnalysisRequest(work_id=work_id, jurisdiction=jurisdiction)
    return await analyze_copyright(request, db)


# ============ Smart Tag Generation ============

@router.post("/tag", response_model=SmartTag, tags=["Smart Tag"])
async def generate_smart_tag(
    request: SmartTagRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a Smart Copyright Expiry Tag
    The main output of the SCET system
    """
    # First, search for the work
    search_engine = get_search_engine()
    search_result = await search_engine.search(
        query=request.query,
        content_type=request.content_type.value if request.content_type else None,
        max_results=1,
        include_web_results=True,
        db=db
    )
    
    # Get the best match
    if search_result.results:
        best = search_result.results[0]
        work = db.query(WorkMetadata).filter(WorkMetadata.id == best.id).first()
        
        if work:
            tag_generator = get_tag_generator()
            
            return tag_generator.generate(
                title=work.title,
                creator=work.creator,
                publication_year=work.publication_year,
                creator_death_year=work.creator_death_year,
                content_type=work.content_type,
                jurisdiction=request.jurisdiction,
                source_urls=[work.source_url] if work.source_url else None,
                include_ai_reasoning=request.include_ai_reasoning
            )
    
    # No match found - generate tag from query alone
    tag_generator = get_tag_generator()
    return tag_generator.generate(
        title=request.query,
        content_type=request.content_type.value if request.content_type else None,
        jurisdiction=request.jurisdiction,
        include_ai_reasoning=request.include_ai_reasoning
    )


@router.get("/tag/detailed", tags=["Smart Tag"])
async def generate_detailed_tag(
    title: str = Query(..., description="Work title"),
    creator: Optional[str] = Query(None, description="Creator/author"),
    year: Optional[int] = Query(None, description="Publication year"),
    type: Optional[str] = Query(None, description="Content type"),
    jurisdiction: str = Query("US", description="Jurisdiction")
):
    """
    Generate a detailed Smart Tag with recommendations, risk assessment, and legal checklist
    Enhanced output for comprehensive copyright analysis
    """
    tag_generator = get_tag_generator()
    
    result = tag_generator.generate_detailed_tag(
        title=title,
        creator=creator,
        publication_year=year,
        content_type=type,
        jurisdiction=jurisdiction
    )
    
    # Convert SmartTag to dict for JSON response
    tag_dict = result["tag"].model_dump() if hasattr(result["tag"], 'model_dump') else result["tag"].__dict__
    
    return {
        "tag": tag_dict,
        "recommendations": result["recommendations"],
        "quick_actions": result["quick_actions"],
        "risk_assessment": result["risk_assessment"],
        "summary": result["summary"],
        "legal_checklist": result["legal_checklist"]
    }


@router.get("/tag/html", response_class=HTMLResponse, tags=["Smart Tag"])
async def generate_html_tag(
    title: str = Query(..., description="Work title"),
    creator: Optional[str] = Query(None, description="Creator/author"),
    year: Optional[int] = Query(None, description="Publication year"),
    type: Optional[str] = Query(None, description="Content type"),
    jurisdiction: str = Query("US", description="Jurisdiction")
):
    """Generate an HTML-formatted Smart Tag for embedding"""
    tag_generator = get_tag_generator()
    
    html = tag_generator.generate_html_tag(
        title=title,
        creator=creator,
        publication_year=year,
        content_type=type,
        jurisdiction=jurisdiction
    )
    
    return HTMLResponse(content=html)


@router.get("/tag/compact", tags=["Smart Tag"])
async def generate_compact_tag(
    title: str = Query(..., description="Work title"),
    creator: Optional[str] = Query(None, description="Creator/author"),
    year: Optional[int] = Query(None, description="Publication year"),
    type: Optional[str] = Query(None, description="Content type"),
    jurisdiction: str = Query("US", description="Jurisdiction")
):
    """Generate a compact, single-line tag"""
    tag_generator = get_tag_generator()
    
    compact = tag_generator.generate_compact_tag(
        title=title,
        creator=creator,
        publication_year=year,
        content_type=type,
        jurisdiction=jurisdiction
    )
    
    return {"tag": compact}


# ============ Data Collection ============

@router.get("/data/status", response_model=DataCollectionStatus, tags=["Data Collection"])
async def get_collection_status():
    """Get data collection status"""
    collector = get_collector()
    scheduler = get_scheduler()
    
    collector_status = collector.get_status()
    scheduler_status = scheduler.get_status()
    
    return DataCollectionStatus(
        is_running=collector_status.get('is_running', False),
        total_sources_checked=collector_status.get('total_collected', 0),
        new_entries_found=collector_status.get('total_collected', 0),
        last_run_at=datetime.fromisoformat(collector_status['last_run']) if collector_status.get('last_run') else None,
        next_scheduled_run=datetime.fromisoformat(scheduler_status['next_check']) if scheduler_status.get('next_check') else None,
        current_source=None
    )


@router.post("/data/collect", tags=["Data Collection"])
async def trigger_collection(
    query: str = Query(..., description="Query to collect data for"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Manually trigger data collection for a query"""
    collector = get_collector()
    
    collected = await collector.collect_for_query(query, content_type, db)
    
    return {
        "status": "collection_complete",
        "works_collected": len(collected),
        "query": query
    }


@router.post("/data/update/{work_id}", tags=["Data Collection"])
async def update_work_data(
    work_id: int,
    db: Session = Depends(get_db)
):
    """Force update data for a specific work"""
    scheduler = get_scheduler()
    
    success = await scheduler.force_update(work_id)
    
    if success:
        return {"status": "updated", "work_id": work_id}
    else:
        raise HTTPException(status_code=404, detail="Work not found or update failed")


# ============ ML Model ============

@router.get("/ml/status", response_model=ModelStatus, tags=["ML Model"])
async def get_model_status():
    """Get ML model status"""
    predictor = get_predictor()
    trainer = get_trainer()
    
    stats = predictor.get_model_stats()
    trainer_status = trainer.get_status()
    
    return ModelStatus(
        model_name="copyright_predictor",
        model_type="binary_classifier",
        version="1.0",
        is_active=True,
        training_samples=stats.get('training_samples', 0),
        accuracy=stats.get('rolling_accuracy'),
        last_trained=datetime.fromisoformat(stats['last_trained']) if stats.get('last_trained') else None,
        next_retrain_at=trainer_status.get('training_threshold', 100) - trainer_status.get('pending_samples', 0)
    )


@router.post("/ml/train", tags=["ML Model"])
async def trigger_training(background_tasks: BackgroundTasks):
    """Manually trigger model training"""
    trainer = get_trainer()
    
    # Run training in background
    background_tasks.add_task(trainer.run_training)
    
    return {"status": "training_scheduled"}


@router.post("/ml/bootstrap", tags=["ML Model"])
async def bootstrap_model(background_tasks: BackgroundTasks):
    """Bootstrap model with rule-based training data"""
    trainer = get_trainer()
    
    # Run bootstrap in background
    background_tasks.add_task(trainer.bootstrap_model)
    
    return {"status": "bootstrap_scheduled"}


@router.post("/ml/train-csv", tags=["ML Model"])
async def train_from_csv(
    csv_path: Optional[str] = Query(None, description="Path to CSV file. Uses default if not provided.")
):
    """Train model from CSV dataset file"""
    trainer = get_trainer()
    
    # Run training synchronously to return results
    result = await trainer.train_from_csv(csv_path)
    
    if result.get("success"):
        return {
            "status": "training_complete",
            "samples_processed": result.get("samples_processed", 0),
            "samples_skipped": result.get("samples_skipped", 0),
            "model_stats": result.get("model_stats", {})
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Training failed"))


# ============ Works Database ============

@router.get("/works", tags=["Works"])
async def list_works(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    content_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List works in database"""
    query = db.query(WorkMetadata)
    
    if content_type:
        query = query.filter(WorkMetadata.content_type == content_type)
    
    total = query.count()
    works = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "works": [
            {
                "id": w.id,
                "title": w.title,
                "creator": w.creator,
                "publication_year": w.publication_year,
                "content_type": w.content_type,
                "copyright_status": w.copyright_status,
                "source": w.source_name
            }
            for w in works
        ]
    }


@router.get("/works/{work_id}", tags=["Works"])
async def get_work(
    work_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific work by ID"""
    work = db.query(WorkMetadata).filter(WorkMetadata.id == work_id).first()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    return {
        "id": work.id,
        "title": work.title,
        "creator": work.creator,
        "publication_year": work.publication_year,
        "creator_death_year": work.creator_death_year,
        "content_type": work.content_type,
        "copyright_status": work.copyright_status,
        "expiry_date": work.expiry_date,
        "allowed_uses": work.allowed_uses,
        "source_url": work.source_url,
        "source_name": work.source_name,
        "data_confidence": work.data_confidence,
        "prediction_confidence": work.prediction_confidence,
        "created_at": work.created_at,
        "updated_at": work.updated_at,
        "last_verified_at": work.last_verified_at
    }


# ============ Jurisdictions ============

@router.get("/jurisdictions", tags=["Jurisdictions"])
async def list_jurisdictions():
    """List supported jurisdictions"""
    rule_engine = get_rule_engine()
    return rule_engine.list_jurisdictions()


@router.get("/jurisdictions/{code}", tags=["Jurisdictions"])
async def get_jurisdiction(code: str):
    """Get jurisdiction details"""
    rule_engine = get_rule_engine()
    info = rule_engine.get_jurisdiction_info(code)
    
    if not info:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")
    
    return info
