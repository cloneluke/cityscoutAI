#!/usr/bin/env python3
"""
Direct Playwright-based event scraper for JavaScript-heavy websites.
Bypasses Scrapy for better control over browser rendering.
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from elasticsearch import Elasticsearch
from datetime import datetime
import hashlib
import re
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PlaywrightScraper:
    def __init__(self, es_host='localhost:9200'):
        self.es = Elasticsearch([f'http://{es_host}'])
        
    async def scrape_events(self, url, site_name='Unknown'):
        """Scrape events from a URL using Playwright."""
        logger.info(f"🌐 Scraping {site_name}: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            try:
                # Use load wait for less strict waiting
                await page.goto(url, wait_until='load', timeout=45000)
                logger.info(f"✓ Page loaded: {site_name}")
                
                # Wait for potential dynamic content
                await page.wait_for_timeout(3000)
                
                # Click "Load More" button if present (for Experience Sioux Falls and similar sites)
                await self._click_load_more_buttons(page, site_name)
                
                # Get page HTML after JS execution
                content = await page.content()
                
                # Extract events using selectors
                events = await self._extract_events_from_page(page, url, site_name)
                
                logger.info(f"📊 Found {len(events)} events on {site_name}")
                return events
                
            except Exception as e:
                logger.error(f"❌ Error scraping {site_name}: {e}")
                return []
            
            finally:
                await browser.close()
    
    async def _click_load_more_buttons(self, page, site_name):
        """Click 'Load More' buttons until no more are available or dates are too far in future."""
        load_more_selectors = [
            'button:has-text("Load More")',
            'button:has-text("load more")',
            'button:has-text("Show More")',
            'button:has-text("show more")',
            '[class*="load-more"] button',
            '[class*="load_more"] button',
            'button[class*="load"]',
            'a:has-text("Load More")',
        ]
        
        clicks_made = 0
        max_clicks = 20  # Prevent infinite loops
        two_weeks_future = datetime.now().timestamp() + (14 * 24 * 60 * 60)
        
        while clicks_made < max_clicks:
            found_button = False
            
            for selector in load_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        found_button = True
                        logger.info(f"📂 Clicking 'Load More' button (attempt {clicks_made + 1})")
                        await button.click()
                        await page.wait_for_timeout(2000)  # Wait for content to load
                        clicks_made += 1
                        
                        # Check if we've reached dates more than 2 weeks in future
                        if await self._has_future_dates(page, two_weeks_future):
                            logger.info("⏰ Found events more than 2 weeks in future, stopping")
                            return
                        
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not found_button:
                logger.info(f"✓ No more 'Load More' buttons found after {clicks_made} clicks")
                break
        
        if clicks_made > 0:
            logger.info(f"✓ Clicked 'Load More' {clicks_made} times")
    
    async def _has_future_dates(self, page, threshold_timestamp):
        """Check if page contains dates more than 2 weeks in future."""
        try:
            # Look for date elements
            date_selectors = ['time', '.date', '[class*="date"]', '[data-date]', '.event-date']
            
            for selector in date_selectors:
                try:
                    date_elements = await page.query_selector_all(selector)
                    for elem in date_elements:
                        text = await elem.text_content()
                        if text:
                            normalized = self._normalize_date(text.strip())
                            if normalized:
                                try:
                                    event_date = datetime.strptime(normalized, '%Y-%m-%d')
                                    if event_date.timestamp() > threshold_timestamp:
                                        logger.debug(f"Found future date: {normalized}")
                                        return True
                                except:
                                    pass
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error checking future dates: {e}")
        
        return False
    
    async def _extract_events_from_page(self, page, url, site_name):
        """Extract events from rendered page."""
        events = []
        
        # Try multiple event container selectors
        selectors = [
            'div[class*="event"]',
            'div.event-card',
            'article.event',
            'li.event-item',
            '.event-listing',
            '.events-list > *',
            'tr[data-event]',
            '.upcoming-event',
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    logger.info(f"🔍 Found {len(elements)} elements with selector: {selector}")
                    
                    for elem in elements:
                        try:
                            event = await self._extract_single_event(elem, url, site_name)
                            if event and event.get('title') and event.get('date'):
                                events.append(event)
                        except Exception as e:
                            logger.debug(f"Skipped element: {e}")
                    
                    if events:
                        break  # Stop after finding events with first working selector
                        
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return events
    
    async def _extract_single_event(self, element, url, site_name):
        """Extract a single event from an element."""
        event = {}
        
        # Try to extract title
        for title_sel in ['h2', 'h3', '.title', '.name', '[class*="title"]']:
            try:
                el = await element.query_selector(title_sel)
                if el:
                    text = await el.text_content()
                    if text:
                        event['title'] = text.strip()
                        break
            except:
                pass
        
        if not event.get('title'):
            return None
        
        # Try to extract date
        for date_sel in ['time', '.date', '[class*="date"]', '[data-date]', '.event-date']:
            try:
                el = await element.query_selector(date_sel)
                if el:
                    text = await el.text_content()
                    if text and self._looks_like_date(text):
                        event['date'] = text.strip()
                        break
            except:
                pass
        
        if not event.get('date'):
            return None
        
        # Try to extract location
        for loc_sel in ['.location', '.venue', '[class*="location"]', '[class*="venue"]', '.address']:
            try:
                el = await element.query_selector(loc_sel)
                if el:
                    text = await el.text_content()
                    if text:
                        event['location'] = text.strip()
                        break
            except:
                pass
        
        event['location'] = event.get('location', 'TBD')
        event['website'] = site_name
        event['source'] = 'website'  # Set source field for API compatibility
        event['url'] = url
        event['image_url'] = ''
        event['address'] = event['location']
        event['start_time'] = None
        event['end_time'] = None
        event['description'] = f'Event from {site_name}'
        event['organizer'] = event['location']
        event['tags'] = ['event']
        
        return event
    
    def _looks_like_date(self, text):
        """Check if text looks like a date."""
        date_patterns = [
            r'\d{1,2}/\d{1,2}',  # MM/DD
            r'\d{1,2}-\d{1,2}',  # MM-DD
            r'[A-Za-z]+ \d{1,2}',  # Month Day
            r'\d{1,2} [A-Za-z]+',  # Day Month
            r'[A-Za-z]+day',  # Monday, etc.
            r'Today|Tomorrow|TBD|TBA|Now',
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def index_events(self, events):
        """Index events to Elasticsearch with deduplication."""
        indexed_count = 0
        duplicate_count = 0
        
        for event in events:
            try:
                # Normalize date to YYYY-MM-DD
                if event.get('date'):
                    normalized_date = self._normalize_date(event['date'])
                    if normalized_date:
                        event['date'] = normalized_date
                    else:
                        continue  # Skip events without valid dates
                else:
                    continue
                
                # Generate event ID from title + date + location
                event_id = hashlib.md5(
                    f"{event['title']}{event['date']}{event['location']}".encode()
                ).hexdigest()
                
                # Check if event already exists
                if not self.es.exists(index='events', id=event_id):
                    event['timestamp'] = datetime.now().isoformat()
                    self.es.index(index='events', id=event_id, document=event)
                    indexed_count += 1
                    logger.info(f"✓ Indexed: {event['title']}")
                else:
                    duplicate_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to index event: {e}")
        
        logger.info(f"📊 Indexed {indexed_count} events, skipped {duplicate_count} duplicates")
        return indexed_count
    
    def _normalize_date(self, date_str):
        """Convert date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', 
            '%B %d', '%b %d', '%A, %B %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If year not specified, assume current year
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Handle "Mon Day" format (e.g., "Dec 16")
        parts = date_str.split()
        if len(parts) >= 2:
            try:
                dt = datetime.strptime(f"{parts[0]} {parts[1]}", '%b %d')
                dt = dt.replace(year=datetime.now().year)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        return None
    
    async def scrape_and_index(self, urls_file='data/website_urls.txt'):
        """Main function: read URLs and scrape all."""
        try:
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            logger.error(f"URLs file not found: {urls_file}")
            return
        
        logger.info(f"📂 Loaded {len(urls)} URLs")
        
        all_events = []
        for url in urls:
            try:
                events = await self.scrape_events(url, site_name=url.split('/')[2])
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
        
        if all_events:
            indexed = self.index_events(all_events)
            logger.info(f"🎉 Success! Scraped and indexed {indexed} new events")
        else:
            logger.warning("⚠️ No events found on any website")


async def main():
    scraper = PlaywrightScraper()
    await scraper.scrape_and_index()


if __name__ == '__main__':
    asyncio.run(main())
