"""Dynamic spider for scraping events from user-specified URLs"""

import scrapy
from cityscout.items import EventItem
from datetime import datetime
import hashlib
import logging
import re
from urllib.parse import urlparse


class DynamicWebsiteSpider(scrapy.Spider):
    """Generic spider that adapts to different website structures"""
    
    name = 'dynamic'
    allowed_domains = []
    
    # Common event-related patterns
    EVENT_PATTERNS = [
        # Container selectors - ordered by specificity
        'a.event-item',  # Experience Sioux Falls - <a> tags with event-item class
        '.event-item',   # Generic event-item class (any element)
        'div.event', 'div[class*="event"]', 'article.event', 'li.event',
        'div.card', 'div[class*="card"]', 'article[class*="card"]',
        'div[class*="item"]', 'div[class*="listing"]',
        'div[role="article"]', 'article',
    ]
    
    TITLE_PATTERNS = [
        'h2', 'h3', 'h4', 'a[class*="title"]', 'span[class*="title"]',
        '[class*="name"]', 'a', '.event-title', '.event-name'
    ]
    
    DATE_PATTERNS = [
        '[class*="date"]', 'time', 'span[class*="date"]', '[class*="when"]',
        '[class*="start"]', '[class*="schedule"]', '.date'
    ]
    
    LOCATION_PATTERNS = [
        '[class*="location"]', '[class*="venue"]', '[class*="place"]',
        '[class*="address"]', 'span[class*="location"]', '.location'
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
    
    def parse(self, response):
        """Parse event listings - adapts to different structures"""
        
        events_found = False
        
        # Try each event container selector
        for container_selector in self.EVENT_PATTERNS:
            event_containers = response.css(container_selector)
            
            if not event_containers or len(event_containers) < 1:
                continue
            
            # Filter out containers that are too large (likely not individual events)
            # But be lenient on size - sometimes event items are small
            containers_to_process = []
            for container in event_containers:
                text_length = len(container.get())
                # Accept containers that are reasonable size for an event
                # Minimum 100 chars, maximum 100KB
                if 100 < text_length < 100000:
                    containers_to_process.append(container)
            
            if len(containers_to_process) < 1:
                # Try without strict size filtering
                containers_to_process = list(event_containers)
            
            self.logger.info(f"🔍 [{self.name}] Found {len(containers_to_process)} potential events using '{container_selector}'")
            events_found = True
            
            for event_container in containers_to_process:
                try:
                    # Special handling for .event-item format (Experience Sioux Falls)
                    if 'event-item' in container_selector:
                        event = self._parse_event_item(event_container, response)
                        if event:
                            yield event
                        continue
                    
                    # Extract title - try multiple strategies
                    title = None
                    for title_selector in self.TITLE_PATTERNS:
                        # Try direct child selector first
                        title_elem = event_container.css(title_selector + '::text').get()
                        if title_elem:
                            title_text = title_elem.strip()
                            # Accept titles 3+ chars
                            if len(title_text) > 3 and len(title_text) < 300:
                                title = title_text
                                break
                        
                        # Try with attribute selectors (for data-title, aria-label, etc)
                        if not title:
                            title_attr = event_container.css(title_selector).attrib.get('title')
                            if not title_attr:
                                title_attr = event_container.css(title_selector).attrib.get('aria-label')
                            if title_attr and len(title_attr) > 3:
                                title = title_attr
                                break
                    
                    if not title:
                        self.logger.debug(f"Skipping event container - no title found")
                        continue
                    
                    # Extract date - try multiple strategies
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
                            date_attr = event_container.css(date_selector).attrib.get('data-date')
                            if not date_attr:
                                date_attr = event_container.css(date_selector).attrib.get('datetime')
                            if date_attr and self._looks_like_date(date_attr):
                                date = date_attr
                                break
                    
                    if not date:
                        self.logger.debug(f"Skipping event '{title}' - no date found")
                        continue  # Skip events without dates
                    
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
                break  # Stop trying selectors once we found events
        
        if not events_found:
            self.logger.warning(f"⚠️ [{self.name}] No events found on {response.url}")
        
        # Check for pagination links
        next_page = response.css('a[rel="next"]::attr(href), a:contains("next")::attr(href)').get()
        if next_page:
            yield scrapy.Request(response.urljoin(next_page), callback=self.parse)
    
    def _looks_like_date(self, text):
        """Check if text looks like a date"""
        # Common date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
            r'[A-Za-z]+\s+\d{1,2}',      # Month DD
            r'\d{1,2}\s+[A-Za-z]+',      # DD Month
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)',
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # DD-MM-YYYY variants
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # Abbreviated months
            r'TBD|TBA|Time TBD',  # For flexible dates
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _parse_event_item(self, event_container, response):
        """Parse event from .event-item format (Experience Sioux Falls style)
        Format: Date Time Title Location
        Example: "Dec 16 1:00 PM Rosemaling Demonstration... Old Courthouse Museum"
        """
        try:
            # Get all text from the container
            full_text = event_container.css('::text').getall()
            text = ' '.join([t.strip() for t in full_text if t.strip()])
            
            if not text or len(text) < 5:
                return None
            
            # Extract date (start of text, format: "Mon DD" or "MonDD")
            date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', text)
            if not date_match:
                self.logger.debug(f"No date found in: {text[:50]}")
                return None
            
            date_str = f"{date_match.group(1)} {date_match.group(2)}"
            date_pos = date_match.end()
            
            # Extract time if present (HH:MM AM/PM)
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', text[date_pos:], re.IGNORECASE)
            time_str = None
            title_start = date_pos
            
            if time_match:
                time_str = f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3)}"
                title_start = date_pos + time_match.end()
            
            # Handle "All Day" pattern
            if 'All Day' in text[date_pos:title_start+10]:
                time_str = 'All Day'
                title_start = text.find('All Day', date_pos) + len('All Day')
            
            # Rest of text is title + location
            remaining = text[title_start:].strip()
            
            if not remaining or len(remaining) < 2:
                return None
            
            # Try to split title and location
            # Usually they're separated by multiple spaces or special characters
            # For now, use the whole remaining text as title (location may be in it)
            lines = [l.strip() for l in remaining.split('\n') if l.strip()]
            title = lines[0] if lines else remaining
            location = lines[1] if len(lines) > 1 else 'TBD'
            
            # Clean up title and location
            title = title.strip()
            if len(title) > 300:
                title = title[:300]
            
            if not title or len(title) < 3:
                return None
            
            # Extract URL
            url = event_container.css('a::attr(href)').get()
            if url:
                url = response.urljoin(url)
            else:
                url = response.url
            
            return self._create_event(title, date_str, time_str, location, url)
        
        except Exception as e:
            self.logger.debug(f"Error parsing event-item: {e}")
            return None
    
    
    def _extract_date(self, date_str):
        """Normalize date strings to YYYY-MM-DD"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try common date formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%B %d', '%b %d', '%A, %B %d, %Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If year not specified, assume current year
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Handle "Dec 16" format (month day without year)
        parts = date_str.split()
        if len(parts) >= 2:
            try:
                # Try "Month Day" format
                dt = datetime.strptime(f"{parts[0]} {parts[1]}", '%b %d')
                dt = dt.replace(year=datetime.now().year)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # If no format matched, return None (we can't index without a valid date)
        return None
    
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

