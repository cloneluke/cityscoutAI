from elasticsearch import Elasticsearch
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch operations"""
    
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.index = "events"
    
    def search(
        self,
        query: str = "*",
        filters: Optional[Dict] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """Search events with optional filters"""
        try:
            # Build query based on input
            if query == "*":
                search_body = {
                    'query': {'match_all': {}},
                    'from': offset,
                    'size': limit
                }
            else:
                search_body = {
                    'query': {
                        'bool': {
                            'must': [
                                {'multi_match': {
                                    'query': query,
                                    'fields': ['title^3', 'description', 'location', 'organizer']
                                }}
                            ]
                        }
                    },
                    'from': offset,
                    'size': limit
                }
            
            # Add filters if provided
            if filters:
                if 'query' not in search_body:
                    search_body['query'] = {'bool': {'must': []}}
                if 'bool' not in search_body['query']:
                    search_body['query'] = {'bool': {'must': [search_body['query']]}}
                    
                for field, value in filters.items():
                    if field == 'tags' and isinstance(value, list):
                        search_body['query']['bool'].setdefault('filter', []).append({
                            'terms': {'tags': value}
                        })
                    elif isinstance(value, str):
                        search_body['query']['bool'].setdefault('filter', []).append({
                            'term': {field: value}
                        })
            
            results = self.es.search(index=self.index, body=search_body)
            
            events = []
            for hit in results['hits']['hits']:
                event = hit['_source']
                event['event_id'] = hit['_id']
                events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"Error searching Elasticsearch: {e}")
            return []
    
    def search_by_source(
        self,
        source: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """Search events by source"""
        return self.search(
            query="*",
            filters={'source': source},
            limit=limit,
            offset=offset
        )
    
    def get_by_event_id(self, event_id: str) -> Optional[Dict]:
        """Get event by event_id"""
        try:
            result = self.es.get(index=self.index, id=event_id)
            event = result['_source']
            event['event_id'] = result['_id']
            return event
        except Exception as e:
            logger.error(f"Error getting event {event_id}: {e}")
            return None
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags from events"""
        try:
            agg_body = {
                'aggs': {
                    'unique_tags': {
                        'terms': {
                            'field': 'tags',
                            'size': 1000
                        }
                    }
                }
            }
            
            results = self.es.search(index=self.index, body=agg_body)
            
            tags = [
                bucket['key'] 
                for bucket in results['aggregations']['unique_tags']['buckets']
            ]
            return sorted(tags)
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []
    
    def index_exists(self) -> bool:
        """Check if events index exists"""
        try:
            return self.es.indices.exists(index=self.index)
        except Exception as e:
            logger.error(f"Error checking index: {e}")
            return False
