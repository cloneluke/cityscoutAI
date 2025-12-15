from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.config import get_settings
from app.services.elasticsearch_service import ElasticsearchService
from app.models import Event, EventSearchQuery, EventSearchResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[Event])
async def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings = Depends(get_settings)
):
    """List all events with pagination"""
    es_service = ElasticsearchService(settings.ELASTICSEARCH_HOST)
    
    try:
        events = es_service.search(
            query="*",
            limit=limit,
            offset=offset
        )
        return events
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving events")


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: str,
    settings = Depends(get_settings)
):
    """Get a specific event by ID"""
    es_service = ElasticsearchService(settings.ELASTICSEARCH_HOST)
    
    try:
        event = es_service.get_by_event_id(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving event")


@router.get("/source/{source}", response_model=List[Event])
async def get_events_by_source(
    source: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings = Depends(get_settings)
):
    """Get events from a specific source (facebook, eventbrite, google)"""
    es_service = ElasticsearchService(settings.ELASTICSEARCH_HOST)
    
    try:
        events = es_service.search_by_source(
            source=source,
            limit=limit,
            offset=offset
        )
        return events
    except Exception as e:
        logger.error(f"Error getting events by source: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving events")
