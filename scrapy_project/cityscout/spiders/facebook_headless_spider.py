import scrapy
from cityscout.items import EventItem
from datetime import datetime
import hashlib
import logging
import os
from playwright.sync_api import sync_playwright
import time


class FacebookHeadlessSpider(scrapy.Spider):
    """Spider for scraping Facebook events using headless browser
    
    Uses Playwright to render JavaScript and extract events from Facebook
    pages that are dynamically loaded.
    """
    
    name = 'facebook_headless'
    allowed_domains = ['facebook.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = []
        self.venues = {}
        self.load_facebook_urls()
        self.load_venue_info()
        self.logger.info(f"Initialized Facebook Headless spider for {len(self.start_urls)} pages")
    
    def load_facebook_urls(self):
        """Load Facebook URLs from data/facebook_urls.txt"""
        try:
            spider_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(spider_dir)))
            
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '../../data/facebook_urls.txt'),
                os.path.join(project_root, 'data/facebook_urls.txt'),
                '/home/luke/git-repos/cityscoutAI/data/facebook_urls.txt',
                './data/facebook_urls.txt',
            ]
            
            self.logger.info(f"Looking for facebook_urls.txt...")
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self.logger.info(f"Found facebook_urls.txt at: {abs_path}")
                    with open(abs_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Add both main page and events section
                                if '/events' not in line:
                                    self.start_urls.append(f"{line}/events")
                                else:
                                    self.start_urls.append(line)
                    
                    self.logger.info(f"Loaded {len(self.start_urls)} URLs from {abs_path}")
                    return
            
            self.logger.warning("facebook_urls.txt not found")
            self.start_urls = []
        except Exception as e:
            self.logger.error(f"Error loading Facebook URLs: {e}")
            self.start_urls = []
    
    def load_venue_info(self):
        """Load venue information from data/facebook_urls.txt
        
        Extracts venue names directly from the URLs being scraped.
        """
        for url in self.start_urls:
            # Skip /events URLs, only process main page URLs
            if '/events' in url:
                continue
            
            # Extract venue name from URL
            # e.g., https://www.facebook.com/SeveranceBrewing -> Severance Brewing
            parts = url.rstrip('/').split('/')
            if parts[-1]:
                name = parts[-1].replace('-', ' ').title()
                # Clean up common patterns
                if name == 'Facebook.com' or name == 'Www.facebook.com':
                    continue
                self.venues[url] = {
                    'name': name,
                    'address': 'Sioux Falls, SD'  # Default for Sioux Falls
                }
        
        if self.venues:
            self.logger.info(f"Loaded {len(self.venues)} venues from facebook_urls.txt")
    
    def start_requests(self):
        """Generate requests for each Facebook URL"""
        for url in self.start_urls:
            self.logger.info(f"🌐 HEADLESS: Queuing {url} for browser rendering")
            yield scrapy.Request(
                url,
                callback=self.parse_with_browser,
                meta={'dont_obey_robotstxt': True, 'url': url},
                errback=self.errback
            )
    
    def parse_with_browser(self, response):
        """Parse using headless browser to render JavaScript"""
        url = response.meta.get('url', response.url)
        self.logger.info(f"🌐 HEADLESS: Opening browser for {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set user agent
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                self.logger.info(f"🌐 HEADLESS: Navigating to {url}")
                try:
                    page.goto(url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    self.logger.warning(f"🌐 HEADLESS: Navigation timeout (page may have loaded): {e}")
                    # Continue anyway - page might have partially loaded
                
                # Wait for events to render
                self.logger.info(f"🌐 HEADLESS: Waiting for content to render...")
                time.sleep(2)
                
                # Get page content
                html = page.content()
                
                # Parse with BeautifulSoup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for event elements
                # Facebook events typically have specific selectors
                event_count = 0
                
                # Try to find event links/items
                event_links = soup.find_all('a', href=True)
                for link in event_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for event page links
                    if '/events/' in href and len(text) > 0:
                        self.logger.info(f"🌐 HEADLESS: Found event: {text}")
                        event_count += 1
                        
                        # Create event item
                        item = EventItem()
                        item['title'] = text[:100]
                        item['location'] = self._get_venue_name(url)
                        item['address'] = self._get_venue_address(url)
                        item['date'] = datetime.now().strftime('%B %d, %Y')
                        item['start_time'] = '19:00'
                        item['end_time'] = None
                        item['description'] = f"Event from Facebook page"
                        item['image_url'] = None
                        item['organizer'] = self._get_venue_name(url)
                        item['url'] = url
                        item['link'] = href if href.startswith('http') else f"https://facebook.com{href}"
                        item['source'] = 'facebook'
                        item['scraped_at'] = datetime.now().isoformat()
                        item['event_id'] = hashlib.md5(
                            f"{item['title']}{item['date']}{url}".encode()
                        ).hexdigest()
                        item['tags'] = ['event', 'sioux-falls', 'facebook']
                        
                        yield item
                
                if event_count == 0:
                    self.logger.info(f"🌐 HEADLESS: No events found on {url}")
                else:
                    self.logger.info(f"✅ HEADLESS: Extracted {event_count} events from {url}")
                
                browser.close()
        
        except Exception as e:
            self.logger.error(f"❌ HEADLESS: Error processing {url}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _get_venue_name(self, url):
        """Extract venue name from URL or venue mapping"""
        for venue_url, venue_data in self.venues.items():
            if venue_url in url:
                return venue_data['name']
        
        # Fallback: extract from URL
        parts = url.rstrip('/').split('/')
        return parts[-1].replace('-', ' ').title() if parts[-1] else 'Unknown Venue'
    
    def _get_venue_address(self, url):
        """Get venue address from mapping"""
        for venue_url, venue_data in self.venues.items():
            if venue_url in url:
                return venue_data.get('address', 'Sioux Falls, SD')
        return 'Sioux Falls, SD'
    
    def errback(self, failure):
        """Handle request errors"""
        self.logger.warning(f"❌ HEADLESS: Failed to fetch {failure.request.url}: {failure.value}")
