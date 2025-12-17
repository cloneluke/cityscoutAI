"""Configuration-based spider for custom event scraping per website"""

import scrapy
from cityscout.items import EventItem
from datetime import datetime
import hashlib
import logging
import re
import json
from urllib.parse import urlparse


class ConfigurableWebsiteSpider(scrapy.Spider):
    """Spider that uses per-website configuration for custom CSS selectors"""
    
    name = 'configurable'
    allowed_domains = []
    
    # Default fallback patterns if no config found
    DEFAULT_PATTERNS = {
        'event_container': [
            'div.event', 'div[class*="event"]', 'article.event', 'li.event',
            'div.card', 'div[class*="card"]', 'article[class*="card"]',
        ],
        'title': ['h2', 'h3', 'h4', 'a[class*="title"]', '[class*="name"]'],
        'date': ['[class*="date"]', 'time', 'span[class*="date"]', '[class*="start"]'],
        'location': ['[class*="location"]', '[class*="venue"]', '[class*="place"]'],
    }
    
    def __init__(self, urls=None, config_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events_count = 0
        self.config = {}
        
        if config_file:
            self.load_config(config_file)
        
        if urls:
            self.start_urls = urls if isinstance(urls, list) else [urls]
        else:
            self.start_urls = []
        
        self.allowed_domains = list(set([urlparse(url).netloc for url in self.start_urls]))
    
    def load_config(self, config_file):
        """Load website configurations from JSON file"""
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            self.logger.info(f"✅ Loaded config for {len(self.config)} websites from {config_file}")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load config file {config_file}: {e}")
    
    def get_selectors_for_url(self, url):
        """Get selectors for a specific URL from config"""
        domain = urlparse(url).netloc
        
        if domain in self.config:
            return self.config[domain].get('selectors', self.DEFAULT_PATTERNS)
        
        # Return defaults if no config found
        return self.DEFAULT_PATTERNS
    
    def parse(self, response):
        """Parse event listings using configured selectors"""
        
        selectors = self.get_selectors_for_url(response.url)
        event_patterns = selectors.get('event_container', self.DEFAULT_PATTERNS['event_container'])
        
        events_found = False
        
        # Try each event container selector
        for container_selector in event_patterns:
            event_containers = response.css(container_selector)
            
            if not event_containers or len(event_containers) < 1:
                continue
            
            # Filter reasonable containers
            containers_to_process = []
            for container in event_containers:
                text_length = len(container.get())
                if 100 < text_length < 100000:
                    containers_to_process.append(container)
            
            if len(containers_to_process) < 1:
                containers_to_process = list(event_containers)
            
            if len(containers_to_process) < 1:
                continue
            
            self.logger.info(f"🔍 [{self.name}] Found {len(containers_to_process)} potential events using '{container_selector}'")
            events_found = True
            
            for event_container in containers_to_process:
                try:
                    # Extract title
                    title = self._extract_field(
                        event_container, 
                        selectors.get('title', self.DEFAULT_PATTERNS['title'])
                    )
                    
                    if not title or len(title) < 3:
                        continue
                    
                    # Extract date
                    date = self._extract_date_field(
                        event_container, 
                        selectors.get('date', self.DEFAULT_PATTERNS['date'])
                    )
                    
                    if not date:
                        continue
                    
                    # Extract location
                    location = self._extract_field(
                        event_container, 
                        selectors.get('location', self.DEFAULT_PATTERNS['location']),
                        default='TBD'
                    )
                    
                    # Extract URL
                    url = event_container.css('a::attr(href)').get()
                    if url:
                        url = response.urljoin(url)
                    else:
                        url = response.url
                    
                    # Create event
                    event = self._create_event(title, date, None, location, url)
                    yield event
                
                except Exception as e:
                    self.logger.debug(f"Error parsing event container: {e}")
                    continue
            
            if events_found:
                break
        
        if not events_found:
            self.logger.warning(f"⚠️ [{self.name}] No events found on {response.url}")
    
    def _extract_field(self, container, selectors, default=None):
        """Extract text field from container using multiple selectors"""
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                text = container.css(selector + '::text').get()
                if text:
                    return text.strip()
                
                # Try attributes
                elem = container.css(selector)
                if elem:
                    text = elem.attrib.get('title') or elem.attrib.get('aria-label')
                    if text:
                        return text.strip()
            except:
                pass
        
        return default
    
    def _extract_date_field(self, container, selectors):
        """Extract and validate date field"""
        date = self._extract_field(container, selectors)
        
        if date and self._looks_like_date(date):
            return date
        
        return None
    
    def _looks_like_date(self, text):
        """Check if text looks like a date"""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'[A-Za-z]+\s+\d{1,2}',
            r'\d{1,2}\s+[A-Za-z]+',
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _extract_date(self, date_str):
        """Normalize date strings"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%A, %B %d, %Y', '%m-%d-%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str
    
    def _generate_event_id(self, title, date, location):
        """Generate consistent event ID"""
        combined = f"{title}{date}{location}".lower()
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _create_event(self, title, date, time, location, url):
        """Create standardized EventItem"""
        event = EventItem()
        event['title'] = title
        event['date'] = self._extract_date(date)
        event['start_time'] = time or 'TBD'
        event['location'] = location
        event['url'] = url or 'N/A'
        event['link'] = url or 'N/A'
        event['organizer'] = location
        event['description'] = f"Event from {urlparse(url or '').netloc}"
        event['event_id'] = self._generate_event_id(title, event['date'] or date, location)
        event['source'] = self.name
        event['scraped_at'] = datetime.now().isoformat()
        
        self.events_count += 1
        self.logger.info(f"✅ [{self.name}] Extracted: {title} @ {location} on {event['date']}")
        
        return event
    
    def closed(self, reason):
        """Called when spider finishes"""
        self.logger.info(f"🏁 [{self.name}] Spider finished - extracted {self.events_count} events")
