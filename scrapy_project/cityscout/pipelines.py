import logging
from itemadapter import ItemAdapter
from elasticsearch import Elasticsearch
from datetime import datetime


class DeduplicationPipeline:
    """Check for duplicate events in Elasticsearch and update or insert"""
    
    def __init__(self, es_host):
        self.es = Elasticsearch([es_host])
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        es_host = crawler.settings.get('ELASTICSEARCH_HOST', 'localhost:9200')
        return cls(es_host=es_host)
    
    def open_spider(self, spider):
        """Called when spider is opened"""
        self.logger.info(f"Connecting to Elasticsearch at {self.es}")
        
        # Create index if it doesn't exist
        try:
            if not self.es.indices.exists(index='events'):
                self.es.indices.create(
                    index='events',
                    body={
                        'mappings': {
                            'properties': {
                                'title': {'type': 'text'},
                                'date': {'type': 'keyword'},
                                'start_time': {'type': 'keyword'},
                                'end_time': {'type': 'keyword'},
                                'location': {'type': 'text'},
                                'address': {'type': 'text'},
                                'description': {'type': 'text'},
                                'image_url': {'type': 'keyword'},
                                'organizer': {'type': 'text'},
                                'attendee_count': {'type': 'integer'},
                                'source': {'type': 'keyword'},
                                'event_id': {'type': 'keyword'},
                                'url': {'type': 'keyword'},
                                'scraped_at': {'type': 'date'},
                                'tags': {'type': 'keyword'},
                            }
                        }
                    }
                )
                self.logger.info("Created 'events' index in Elasticsearch")
        except Exception as e:
            self.logger.error(f"Error creating index: {e}")
    
    def close_spider(self, spider):
        """Called when spider is closed"""
        self.logger.info("Closing Elasticsearch connection")
    
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            event_id = adapter.get('event_id')
            title = adapter.get('title', 'Unknown')
            
            # Check if event already exists
            result = self.es.search(
                index='events',
                body={
                    'query': {
                        'term': {
                            'event_id': event_id
                        }
                    }
                }
            )
            
            item_dict = dict(adapter)
            item_dict['scraped_at'] = datetime.now().isoformat()
            
            if result['hits']['total']['value'] > 0:
                # Event exists, update it
                existing_event = result['hits']['hits'][0]
                self.es.update(
                    index='events',
                    id=existing_event['_id'],
                    body={'doc': item_dict, 'doc_as_upsert': True}
                )
                self.logger.info(f"Updated existing event: {title}")
            else:
                # New event, index it
                self.es.index(index='events', document=item_dict)
                self.logger.info(f"Indexed new event: {title}")
        
        except Exception as e:
            self.logger.error(f"Error processing item {adapter.get('title')}: {e}")
            raise
        
        return item
