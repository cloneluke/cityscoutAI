import scrapy
from scrapy_splash import SplashRequest
import logging
from cityscout.items import EventItem
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class PlaywrightWebsiteSpider(scrapy.Spider):
    """
    Spider using Playwright for JavaScript-heavy websites.
    Requires async await support in Scrapy (2.7+).
    """
    name = 'playwright'
    allowed_domains = []
    
    # Event container patterns
    EVENT_PATTERNS = [
        'div[class*="event"]',
        'div[class*="Event"]',
        'div[class*="card"]',
        'div[class*="Card"]', 
        'article[class*="event"]',
        'article[class*="listing"]',
        'section[class*="event"]',
        'li[class*="event"]',
        'tr[class*="event"]',
        '.event',
        '.event-item',
        '.event-card',
        '.upcoming-events > *',
        '[data-event]',
    ]
    
    # Title patterns
    TITLE_PATTERNS = [
        'h2', 'h3', 'h4',
        '[class*="title"]',
        '[class*="Title"]',
        '[class*="name"]',
        '[class*="Name"]',
        '[data-event-name]',
        '[aria-label]',
    ]
    
    # Date patterns
    DATE_PATTERNS = [
        '[class*="date"]',
        '[class*="Date"]',
        '[class*="time"]',
        '[class*="Time"]',
        'time',
        '[data-date]',
        '[data-start-date]',
        'span.date',
        'span.time',
    ]
    
    # Location patterns
    LOCATION_PATTERNS = [
        '[class*="location"]',
        '[class*="Location"]',
        '[class*="venue"]',
        '[class*="Venue"]',
        '[class*="address"]',
        '[data-location]',
        '[data-venue]',
    ]
    
    def start_requests(self):
        """Generate requests from allowed_domains if set via meta."""
        urls = getattr(self, 'urls_to_scrape', [])
        for url in urls:
            self.allowed_domains.append(url.split('/')[2])
            # Use regular request - will be handled by Playwright middleware
            yield scrapy.Request(url, callback=self.parse, meta={'playwright': True, 'playwright_include_page': True})
    
    async def parse(self, response):
        """Parse events from page using Playwright."""
        page = response.meta.get('playwright_page')
        if not page:
            logger.error(f"⚠️ [playwright] No page object for {response.url}")
            return
        
        try:
            # Wait for potential dynamic content
            await page.wait_for_timeout(3000)  # 3 seconds for JS to load
            
            events_found = 0
            
            for pattern in self.EVENT_PATTERNS:
                try:
                    elements = await page.query_selector_all(pattern)
                    if elements:
                        logger.info(f"🔍 [playwright] Found {len(elements)} potential events using '{pattern}'")
                        
                        for element in elements:
                            try:
                                event = await self._extract_event(element, pattern)
                                if event and event.get('title') and event.get('date'):
                                    events_found += 1
                                    yield event
                            except Exception as e:
                                logger.debug(f"Error extracting event: {e}")
                                continue
                        
                        if events_found > 0:
                            break
                except:
                    continue
            
            logger.info(f"🏁 [playwright] Spider finished - extracted {events_found} events")
        
        except Exception as e:
            logger.error(f"⚠️ [playwright] Error parsing {response.url}: {e}")
        
        finally:
            if page:
                await page.close()
    
    async def _extract_event(self, element, container_pattern):
        """Extract event data from element."""
        event = EventItem()
        
        # Extract title
        title = None
        for pattern in self.TITLE_PATTERNS:
            try:
                el = await element.query_selector(pattern)
                if el:
                    title = await el.text_content()
                    if title:
                        title = title.strip()
                        break
            except:
                continue
        
        if not title:
            return None
        
        event['title'] = title
        event['url'] = ''  # Will be set by pipeline
        
        # Extract date
        date = None
        for pattern in self.DATE_PATTERNS:
            try:
                el = await element.query_selector(pattern)
                if el:
                    date = await el.text_content()
                    if date and self._looks_like_date(date):
                        event['date'] = date.strip()
                        break
            except:
                continue
        
        if not event.get('date'):
            return None
        
        # Extract location
        for pattern in self.LOCATION_PATTERNS:
            try:
                el = await element.query_selector(pattern)
                if el:
                    location = await el.text_content()
                    if location:
                        event['location'] = location.strip()
                        break
            except:
                continue
        
        event['location'] = event.get('location', 'Unknown')
        event['image_url'] = ''
        event['website'] = 'Extracted'
        
        return event
    
    def _looks_like_date(self, text):
        """Check if text looks like a date."""
        import re
        
        date_patterns = [
            r'\d{1,2}/\d{1,2}',  # MM/DD or M/D
            r'\d{1,2}-\d{1,2}',  # MM-DD or M-D
            r'[A-Za-z]+ \d{1,2}',  # Month D
            r'\d{1,2} [A-Za-z]+',  # D Month
            r'[A-Za-z]+day',  # Monday, Tuesday, etc.
            r'Today|Tomorrow|TBD|TBA',  # Relative dates
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
