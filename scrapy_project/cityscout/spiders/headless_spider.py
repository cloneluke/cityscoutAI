"""Headless spider for scraping dynamically-rendered event websites"""

import scrapy
from cityscout.items import EventItem
from datetime import datetime
import hashlib
import logging
import re
from urllib.parse import urlparse
from scrapy_splash import SplashRequest


class HeadlessWebsiteSpider(scrapy.Spider):
    """Spider that uses headless browser to render JavaScript-heavy event websites"""
    
    name = 'headless'
    allowed_domains = []
    
    # Common event-related patterns
    EVENT_PATTERNS = [
        'div.event', 'div[class*="event"]', 'article.event', 'li.event',
        'div.card', 'div[class*="card"]', 'article[class*="card"]',
        'div[class*="item"]', 'div[class*="listing"]',
        'div[role="article"]', 'article', 'div[class*="tile"]', 'div[class*="box"]',
    ]
    
    TITLE_PATTERNS = [
        'h2', 'h3', 'h4', 'h1', 'a[class*="title"]', 'span[class*="title"]',
        '[class*="name"]', 'a', '.event-title', '.event-name', '[role="heading"]'
    ]
    
    DATE_PATTERNS = [
        '[class*="date"]', 'time', 'span[class*="date"]', '[class*="when"]',
        '[class*="start"]', '[class*="schedule"]', '.date', '[class*="time"]'
    ]
    
    LOCATION_PATTERNS = [
        '[class*="location"]', '[class*="venue"]', '[class*="place"]',
        '[class*="address"]', 'span[class*="location"]', '.location', '[class*="city"]'
    ]
    
    def __init__(self, urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events_count = 0
        
        if urls:
            self.start_urls = urls if isinstance(urls, list) else [urls]
        else:
            self.start_urls = []
        
        # Extract domain from URLs for allowed_domains
        self.allowed_domains = list(set([urlparse(url).netloc for url in self.start_urls]))
    
    def start_requests(self):
        """Use Splash to render JavaScript"""
        for url in self.start_urls:
            # Use Splash to wait for dynamic content to load
            yield SplashRequest(
                url,
                callback=self.parse,
                args={
                    'wait': 3,  # Wait 3 seconds for JS to render
                    'html': 1,
                },
                meta={'dont_cache': True}
            )
    
    def parse(self, response):
        """Parse event listings from rendered HTML"""
        
        events_found = False
        
        # Try each event container selector
        for container_selector in self.EVENT_PATTERNS:
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
                    title = None
                    for title_selector in self.TITLE_PATTERNS:
                        # Try direct text
                        title_elem = event_container.css(title_selector + '::text').get()
                        if title_elem:
                            title_text = title_elem.strip()
                            if len(title_text) > 3 and len(title_text) < 300:
                                title = title_text
                                break
                        
                        # Try from attributes
                        if not title:
                            try:
                                title_attr = event_container.css(title_selector).attrib.get('title')
                                if not title_attr:
                                    title_attr = event_container.css(title_selector).attrib.get('aria-label')
                                if title_attr and len(title_attr) > 3:
                                    title = title_attr
                                    break
                            except:
                                pass
                    
                    if not title:
                        self.logger.debug(f"Skipping event container - no title found")
                        continue
                    
                    # Extract date
                    date = None
                    for date_selector in self.DATE_PATTERNS:
                        date_elem = event_container.css(date_selector + '::text').get()
                        if date_elem:
                            date_text = date_elem.strip()
                            if self._looks_like_date(date_text):
                                date = date_text
                                break
                        
                        # Try from attributes
                        if not date:
                            try:
                                date_attr = event_container.css(date_selector).attrib.get('data-date')
                                if not date_attr:
                                    date_attr = event_container.css(date_selector).attrib.get('datetime')
                                if date_attr and self._looks_like_date(date_attr):
                                    date = date_attr
                                    break
                            except:
                                pass
                    
                    if not date:
                        self.logger.debug(f"Skipping event '{title}' - no date found")
                        continue
                    
                    # Extract location
                    location = 'TBD'
                    for location_selector in self.LOCATION_PATTERNS:
                        location_elem = event_container.css(location_selector + '::text').get()
                        if location_elem:
                            location = location_elem.strip()
                            if location and len(location) > 2:
                                break
                    
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
        
        # Check for pagination
        next_page = response.css('a[rel="next"]::attr(href), a:contains("next")::attr(href)').get()
        if next_page:
            yield SplashRequest(
                response.urljoin(next_page),
                callback=self.parse,
                args={
                    'wait': 3,
                    'html': 1,
                },
                meta={'dont_cache': True}
            )
    
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
            r'TBD|TBA|Time TBD',
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
