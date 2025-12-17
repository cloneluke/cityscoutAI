"""Base spider class for website event scraping"""

import scrapy
from cityscout.items import EventItem
from datetime import datetime
import hashlib
import logging
import re


class BaseWebsiteSpider(scrapy.Spider):
    """Base spider for scraping events from websites
    
    Subclasses should override:
    - allowed_domains: List of domains to scrape
    - start_urls: List of URLs to start scraping from
    - parse_event(): Extract event data from response
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.events_count = 0
    
    def parse_event(self, response):
        """Parse a single event page - override in subclass"""
        raise NotImplementedError("Subclasses must implement parse_event()")
    
    def extract_date(self, date_str):
        """Helper to normalize date strings"""
        if not date_str:
            return None
        
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%A, %B %d, %Y']:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str
    
    def extract_time(self, time_str):
        """Helper to normalize time strings"""
        if not time_str:
            return None
        return time_str.strip()
    
    def generate_event_id(self, title, date, location):
        """Generate consistent event ID"""
        combined = f"{title}{date}{location}".lower()
        return hashlib.md5(combined.encode()).hexdigest()
    
    def create_event_item(self, title, date, time, location, url, organizer=None, description=None):
        """Create a standardized EventItem"""
        event = EventItem()
        event['title'] = title
        event['date'] = date
        event['start_time'] = time
        event['location'] = location
        event['url'] = url
        event['organizer'] = organizer or location
        event['description'] = description or f"Event from {self.name}"
        event['event_id'] = self.generate_event_id(title, date, location)
        event['source'] = self.name
        event['scraped_at'] = datetime.now().isoformat()
        
        self.events_count += 1
        self.logger.info(f"✅ [{self.name}] Extracted: {title} @ {location} on {date}")
        
        return event
    
    def closed(self, reason):
        """Called when spider finishes"""
        self.logger.info(f"🏁 [{self.name}] Spider finished - extracted {self.events_count} events - reason: {reason}")
