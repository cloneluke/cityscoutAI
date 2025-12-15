from fastapi import APIRouter, Depends, HTTPException, Query
from app.config import get_settings
from app.services.elasticsearch_service import ElasticsearchService
from app.models import Event, EventSearchResponse
from typing import List, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=EventSearchResponse)
async def search_events(
    q: Optional[str] = Query(None, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    source: Optional[str] = Query(None, description="Event source (facebook, eventbrite, google)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings = Depends(get_settings)
):
    """Search events by query, tags, and source"""
    es_service = ElasticsearchService(settings.ELASTICSEARCH_HOST)
    
    try:
        # Parse tags if provided
        tag_list = [t.strip() for t in tags.split(',')] if tags else []
        
        # Build search filters
        filters = {}
        if source:
            filters['source'] = source
        if tag_list:
            filters['tags'] = tag_list
        
        # Perform search
        results = es_service.search(
            query=q or "*",
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        return EventSearchResponse(
            total=len(results),
            events=results,
            query=q or "*",
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise HTTPException(status_code=500, detail="Error searching events")


@router.get("/tags", response_model=List[str])
async def get_available_tags(
    settings = Depends(get_settings)
):
    """Get all available event tags"""
    es_service = ElasticsearchService(settings.ELASTICSEARCH_HOST)
    
    try:
        tags = es_service.get_all_tags()
        return tags
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving tags")
