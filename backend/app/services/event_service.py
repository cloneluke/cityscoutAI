from app.services.elasticsearch_service import ElasticsearchService
from app.services.ollama_service import OllamaService
from app.utils.normalizer import EventNormalizer
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class EventService:
    """High-level event service combining Elasticsearch and Ollama"""
    
    def __init__(self, es_host: str = "localhost:9200", ollama_host: str = "http://localhost:11434"):
        self.es_service = ElasticsearchService(es_host)
        self.ollama_service = OllamaService(ollama_host)
        self.normalizer = EventNormalizer()
    
    def enrich_event(self, event: Dict) -> Dict:
        """Enrich event with AI-generated tags and normalization"""
        try:
            # Normalize fields
            event['title'] = self.normalizer.clean_text(event.get('title', 'Unknown'))
            event['date'] = self.normalizer.normalize_date(event.get('date', 'TBA'))
            event['location'] = self.normalizer.normalize_location(event.get('location', 'TBA'))
            event['description'] = self.normalizer.clean_text(event.get('description', ''))
            
            # Generate tags if Ollama is available
            if self.ollama_service.health_check():
                description = event.get('description', '')
                title = event.get('title', '')
                
                tags = self.ollama_service.generate_tags(title, description)
                category = self.ollama_service.categorize_event(title, description)
                
                event['tags'] = tags + [category] if category else tags
            else:
                logger.warning("Ollama service not available, skipping AI tagging")
                event['tags'] = []
            
            return event
        except Exception as e:
            logger.error(f"Error enriching event: {e}")
            return event
    
    def search_events(
        self,
        query: str = "*",
        tags: List[str] = None,
        source: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """Search events with optional filters"""
        filters = {}
        if source:
            filters['source'] = source
        if tags:
            filters['tags'] = tags
        
        events = self.es_service.search(
            query=query,
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        return {
            'total': len(events),
            'events': events,
            'query': query,
            'limit': limit,
            'offset': offset
        }
