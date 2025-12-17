#!/usr/bin/env python3
"""
Headless browser scraper for Facebook events using multiprocessing
Runs events extraction in parallel using Python multiprocessing
Filters events to 1 week in the past and 2 weeks in the future
"""

import os
import sys
import logging
import hashlib
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def load_facebook_urls():
    """Load Facebook URLs from data/facebook_urls.txt
    
    Returns main page URLs, /events URLs, and /past_hosted_events URLs
    """
    possible_paths = [
        '/home/luke/git-repos/cityscoutAI/data/facebook_urls.txt',
        './data/facebook_urls.txt',
        '../data/facebook_urls.txt',
        '../../data/facebook_urls.txt',
    ]
    
    urls = []
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Found facebook_urls.txt at: {path}")
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Add main page URL (for post extraction from feed)
                        base_url = line.replace('/events', '').replace('/past_hosted_events', '')
                        if base_url not in urls:
                            urls.append(base_url)
                        # Add /events URL (for official event listing)
                        events_url = base_url + '/events'
                        if events_url not in urls:
                            urls.append(events_url)
                        # Add /past_hosted_events URL (for past events)
                        past_url = base_url + '/past_hosted_events'
                        if past_url not in urls:
                            urls.append(past_url)
            logger.info(f"Loaded {len(urls)} URLs ({len(urls)//3} pages with main + /events + /past_hosted_events)")
            return urls
    
    logger.warning("facebook_urls.txt not found")
    return []


def load_venue_info():
    """Load venue information from data/facebook_urls.txt
    
    Extracts venue names directly from the URLs being scraped.
    """
    urls = load_facebook_urls()
    venues = {}
    
    for url in urls:
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
            venues[url] = {
                'name': name,
                'address': 'Sioux Falls, SD'  # Default for Sioux Falls
            }
    
    if venues:
        logger.info(f"Loaded {len(venues)} venues from facebook_urls.txt")
    return venues


def get_venue_name(url, venues):
    """Extract venue name from URL or venue mapping"""
    for venue_url, venue_data in venues.items():
        if venue_url in url:
            return venue_data['name']
    
    parts = url.rstrip('/').split('/')
    return parts[-1].replace('-', ' ').title() if parts[-1] else 'Unknown Venue'


def get_venue_address(url, venues):
    """Get venue address from mapping"""
    for venue_url, venue_data in venues.items():
        if venue_url in url:
            return venue_data.get('address', 'Sioux Falls, SD')
    return 'Sioux Falls, SD'


def normalize_date(date_str):
    """Normalize date to YYYY-MM-DD format
    
    Handles various input formats:
    - "Monday December 15th"
    - "December 15"
    - "December 15, 2025"
    
    Returns: "2025-12-15" or None if invalid
    """
    if not date_str or date_str == 'Date TBA':
        return None
    
    try:
        original = date_str
        
        # Remove day names (Monday, Tuesday, etc.)
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_name in day_names:
            date_str = date_str.replace(day_name, '').strip()
        
        # Clean up spacing and dashes
        date_str = re.sub(r'\s*-\s*', ' ', date_str).strip()
        
        # Remove ordinal indicators (st, nd, rd, th)
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        
        # Parse the date string
        parsed_date = None
        
        # Try various date formats
        date_formats = [
            "%B %d, %Y",      # December 12, 2025
            "%B %d",           # December 12 (assume current/next year)
            "%m/%d/%Y",       # 12/12/2025
            "%m/%d",          # 12/12 (assume current/next year)
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue
        
        if not parsed_date:
            logger.warning(f"Could not parse date: {original}")
            return None
        
        # If year not specified, assume current or next year
        if parsed_date.year < 2000:
            current_year = datetime.now().year
            # If month is in the past this year, assume next year
            if parsed_date.month < datetime.now().month:
                parsed_date = parsed_date.replace(year=current_year + 1)
            else:
                parsed_date = parsed_date.replace(year=current_year)
        
        return parsed_date.strftime("%Y-%m-%d")
    
    except Exception as e:
        logger.warning(f"Error normalizing date '{date_str}': {e}")
        return None


def is_event_in_date_range(date_str):
    """Check if event is within acceptable date range
    
    - For past events (/past_hosted_events): accept up to 3 months in the past
    - For upcoming events (/events): accept 1 week past to 2 weeks future
    - If no date specified, exclude
    """
    if not date_str or date_str == 'Date TBA':
        return False  # Exclude events with no date
    
    try:
        # Remove day names (Monday, Tuesday, etc.) from the date string
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day_name in day_names:
            date_str = date_str.replace(day_name, '').strip()
        
        # Clean up spacing and dashes
        date_str = re.sub(r'\s*-\s*', ' ', date_str).strip()
        
        # Remove ordinal indicators (st, nd, rd, th)
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        
        # Parse the date string
        parsed_date = None
        
        # Try various date formats
        date_formats = [
            "%B %d, %Y",      # December 12, 2025
            "%B %d",           # December 12 (assume current/next year)
            "%m/%d/%Y",       # 12/12/2025
            "%m/%d",          # 12/12 (assume current/next year)
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt)
                break
            except ValueError:
                continue
        
        if not parsed_date:
            logger.warning(f"Could not parse date: {date_str}")
            return False
        
        # If year not specified, assume current or next year
        if parsed_date.year < 2000:
            current_year = datetime.now().year
            # If month is in the past this year, assume next year
            if parsed_date.month < datetime.now().month:
                parsed_date = parsed_date.replace(year=current_year + 1)
            else:
                parsed_date = parsed_date.replace(year=current_year)
        
        # Check if date is within range: 3 months in past to 2 weeks in future
        # (This allows us to catch past events from /past_hosted_events)
        now = datetime.now()
        min_date = now - timedelta(days=90)  # 3 months past
        max_date = now + timedelta(days=14)  # 2 weeks future
        
        in_range = min_date <= parsed_date <= max_date
        
        if not in_range:
            logger.debug(f"Event date {parsed_date.date()} outside range ({min_date.date()} to {max_date.date()})")
        
        return in_range
    
    except Exception as e:
        logger.warning(f"Error checking date range for '{date_str}': {e}")
        return False

def scrape_url(args):
    """Scrape a single Facebook URL using headless browser
    
    Args:
        args: tuple of (url, venues_dict)
    
    Returns:
        list of event dicts
    """
    url, venues = args
    events = []
    
    logger.info(f"🌐 [Worker] Opening browser for {url}")
    
    try:
        with sync_playwright() as p:
            # Anti-detection: Use realistic browser arguments
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',  # Prevent memory issues
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-sync',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-default-apps',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-background-networking',
                    '--disable-preconnect',
                ]
            )
            
            # Anti-detection: Use realistic viewport and user agent
            page = browser.new_page(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Anti-detection: Inject stealth script to hide headless indicators
            stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
              get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
              get: () => ['en-US', 'en'],
            });
            window.chrome = {
              runtime: {}
            };
            """
            page.add_init_script(stealth_js)
            
            # Anti-detection: Set realistic headers
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            logger.info(f"🌐 [Worker] Navigating to {url}")
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
            except Exception as e:
                logger.warning(f"🌐 [Worker] Navigation timeout for {url}: {e}")
            
            # Anti-detection: Random delay to mimic human behavior (2-4 seconds)
            import time
            import random
            delay = random.uniform(2, 4)
            logger.debug(f"🌐 [Worker] Waiting {delay:.1f}s to mimic human behavior")
            time.sleep(delay)
            
            # Get content
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract events from /events pages
            logger.info(f"🌐 [Worker] Extracting events from {url}")
            events.extend(extract_events_from_page(url, soup, venues, browser, page))
            
            # Also extract events from posts if not already on /events page
            if '/events' not in url:
                logger.info(f"📝 [Worker] Extracting event posts from feed at {url}")
                
                # Try to expand "See more" links to show full post content
                try:
                    import time as time_module
                    # Use JavaScript to find and click all "See more" buttons
                    # This avoids element interception issues
                    expand_count = page.evaluate('''() => {
                        let count = 0;
                        const buttons = document.querySelectorAll('[role="button"], button, a');
                        for (let btn of buttons) {
                            if (btn.textContent && btn.textContent.includes('See more') && 
                                btn.textContent.length < 50 &&  // Avoid "See more from..." links
                                btn.offsetHeight > 0) {
                                try {
                                    btn.click();
                                    count++;
                                    if (count >= 5) break;  // Limit clicks
                                } catch (e) {}
                            }
                        }
                        return count;
                    }''')
                    
                    if expand_count > 0:
                        logger.debug(f"📝 [Worker] Clicked {expand_count} 'See more' button(s)")
                        time_module.sleep(1)  # Wait for content to load
                    
                    # Get updated content after expanding posts
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                except Exception as e:
                    logger.debug(f"Could not expand posts: {e}")
                
                events.extend(extract_events_from_posts(url, soup, venues, browser, page))
            
            browser.close()
            logger.info(f"✅ [Worker] Extracted {len(events)} events from {url}")
    
    except Exception as e:
        logger.error(f"❌ [Worker] Error scraping {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return events


def extract_events_from_page(url, soup, venues, browser, page):
    """Extract events from Facebook /events page"""
    events = []
    
    # Find event links
    event_links = soup.find_all('a', href=True)
    seen_links = set()
    
    for link in event_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Look for event links
        if '/events/' in href and len(text) > 2 and href not in seen_links:
            seen_links.add(href)
            logger.info(f"🌐 [Worker] Found event: {text[:50]}")
            
            # Try to get date and location from the event page itself
            event_date = 'Date TBA'
            event_location = get_venue_name(url, venues)  # Fallback to page venue
            event_organizer = get_venue_name(url, venues)  # Fallback to page venue
            
            try:
                full_event_url = href if href.startswith('http') else f"https://facebook.com{href}"
                event_page = browser.new_page()
                event_page.goto(full_event_url, wait_until='domcontentloaded', timeout=10000)
                
                # Anti-detection: Random delay between event page requests (0.5-1.5 seconds)
                import time
                import random
                event_delay = random.uniform(0.5, 1.5)
                time.sleep(event_delay)
                
                # Extract date and location from event page
                event_html = event_page.content()
                event_soup = BeautifulSoup(event_html, 'html.parser')
                event_text = event_soup.get_text(separator='\n', strip=True)
                
                # Look for date in og:description meta tag first (most reliable)
                import re
                og_desc = event_soup.find('meta', property='og:description')
                if og_desc and og_desc.get('content'):
                    og_content = og_desc.get('content', '')
                    # Normalize whitespace (replace newlines with spaces)
                    og_content_normalized = ' '.join(og_content.split())
                    
                    # Extract date from og:description like "Event in Sioux Falls, SD by Bin 201 on Friday, December 12 2025"
                    # Look for day name pattern followed by month and date
                    day_date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s+\d{4})?'
                    date_match = re.search(day_date_pattern, og_content_normalized)
                    if date_match:
                        event_date = date_match.group(0)
                        # Remove leading day name for cleaner date format
                        event_date = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+', '', event_date)
                    
                    # Extract organizer/venue from "by [organizer] on" pattern
                    organizer_match = re.search(r'by\s+(.+?)\s+on', og_content_normalized)
                    if organizer_match:
                        extracted_organizer = organizer_match.group(1).strip()
                        # Truncate if it's very long (sometimes contains extra text)
                        if len(extracted_organizer) < 150:
                            event_organizer = extracted_organizer
                            event_location = extracted_organizer
                            logger.debug(f"  Extracted organizer from og:description: {event_organizer}")
                
                # Fallback: look for date pattern in body text
                if event_date == 'Date TBA':
                    date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s+\d{4})?'
                    date_match = re.search(date_pattern, event_text)
                    if date_match:
                        event_date = date_match.group(0)
                
                # Extract location from event page text ONLY if we didn't already extract it from og:description
                # Look for venue name (usually appears before address with street info)
                if event_location == get_venue_name(url, venues):  # Still has default value
                    # Strategy: Find lines followed by an address, pick the one that looks like a venue
                    lines = event_text.split('\n')
                    venue_candidates = []
                    
                    for i, line in enumerate(lines):
                        line_clean = line.strip()
                        
                        # Skip common UI elements and the event title
                        if not line_clean or len(line_clean) < 2:
                            continue
                        if line_clean in ['Like', 'Comment', 'Share', 'Follow', '·', 'Sioux Falls, South Dakota', 'Sioux Falls']:
                            continue
                        if line_clean == text[:100]:  # Skip if it matches event title
                            continue
                        
                        # Skip UI labels and common non-venue text
                        if line_clean in ['Host', 'Online', 'TBA', 'TBD', 'See all', 'Event by', 'See more']:
                            continue
                        
                        # Check if next line looks like an address
                        if i < len(lines) - 1:
                            next_line = lines[i+1].strip()
                            if any(marker in next_line for marker in ['Street', 'St,', 'Ave', 'Road', 'Rd,', 'Boulevard', 'Drive', 'Lane', 'Way', 'Court', 'Plaza', 'Circle']):
                                # This looks like a venue-address pair
                                venue_candidates.append((line_clean, next_line))
                    
                    # Pick the best candidate (prefer shorter venue names that look like business names)
                    if venue_candidates:
                        # Sort by length (shorter names usually better) and pick first
                        venue_candidates.sort(key=lambda x: len(x[0]))
                        event_location = venue_candidates[0][0][:100]
                        event_organizer = venue_candidates[0][0][:100]
                        logger.debug(f"  Extracted location: {event_location}")
                
                event_page.close()
            except Exception as e:
                logger.debug(f"Could not fetch event details from {href}: {e}")
            
            event = {
                'title': text[:100],
                'location': event_location,
                'address': get_venue_address(url, venues),
                'date': normalize_date(event_date) or event_date,  # Normalize date
                'start_time': '19:00',
                'end_time': None,
                'description': 'Event from Facebook',
                'image_url': None,
                'organizer': event_organizer,
                'url': url,
                'link': href if href.startswith('http') else f"https://facebook.com{href}",
                'source': 'facebook',
                'scraped_at': datetime.now().isoformat(),
                'tags': ['event', 'sioux-falls', 'facebook']
            }
            
            # Generate event_id - use link (most reliable unique identifier)
            if event.get('link'):
                event['event_id'] = hashlib.md5(event['link'].encode()).hexdigest()
            else:
                event['event_id'] = hashlib.md5(
                    f"{event['title']}{event['location']}{event['organizer']}".encode()
                ).hexdigest()
            
            # Filter by date range: 1 week past, 2 weeks future
            if is_event_in_date_range(event_date):
                events.append(event)
            else:
                logger.debug(f"⏭️  Skipping event outside date range: {text[:50]} ({event_date})")
    
    return events


def extract_events_from_posts(url, soup, venues, browser=None, page=None):
    """Extract events from Facebook posts in page feed
    
    Extracts event information directly from the feed page where events are visible.
    Handles posts with multiple events on the same date.
    
    Structure: Date heading, then repeating: Title, Time+Venue
    """
    events = []
    
    try:
        # Get full text from feed with line separation to preserve structure
        text = soup.get_text(separator='\n', strip=True)
        lines = text.split('\n')
        
        logger.debug(f"📝 [Feed] Parsing {len(lines)} lines from {url}")
        
        # Patterns
        date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*-?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s+\d{4})?'
        time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?(?:\s*-\s*\d{1,2}:\d{2}\s*(am|pm|AM|PM)?)?'
        
        # Stop words that indicate end of event block
        stop_patterns = ['Like', 'Comment', 'Share', 'Log In', 'Password', 'Email or phone', 
                        'Create new account', 'Forgot', 'All reactions', 'View more comments',
                        'Follow', '©', 'Privacy', 'Terms', 'Cookies', 'Meta']
        
        extracted_events = {}
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1
            
            if not line or len(line) < 2:
                continue
            
            # Look for date lines
            date_match = re.search(date_pattern, line)
            if not date_match:
                continue
                
            event_date = re.sub(r'\s*-\s*', ' ', date_match.group(0).strip())
            logger.debug(f"📝 [Feed] Found date: '{event_date}'")
            
            # Process events under this date
            while i < len(lines):
                title_line = lines[i].strip()
                i += 1
                
                # Stop conditions
                if not title_line or len(title_line) < 2:
                    continue
                if title_line in ['Like', 'Comment', 'Share', '·']:
                    break
                if any(pattern in title_line for pattern in stop_patterns):
                    break
                if re.search(date_pattern, title_line):  # Next date
                    i -= 1
                    break
                if 'See more' in title_line and 'From' in title_line:  # "See more from..." footer
                    break
                if 'https://www.facebook.com' in title_line:
                    break
                if 'Bottoms Up' in title_line:  # Other page name
                    break
                
                # Handle multi-line titles (e.g., "Men's Basketball:", "Jackrabbit...", "vs Wyoming")
                # Combine lines that don't have time/venue info until we find the time line
                full_title = title_line
                while i < len(lines):
                    next_line = lines[i].strip()
                    
                    # Stop if we hit a stop pattern or empty line
                    if not next_line or any(p in next_line for p in stop_patterns):
                        break
                    
                    # If the next line has a time pattern, we found the time+venue line
                    if re.search(time_pattern, next_line):
                        break
                    
                    # If next line has a date pattern, it's the next date
                    if re.search(date_pattern, next_line):
                        break
                    
                    # Check if this line looks like venue text (no time pattern, reasonable length)
                    if len(next_line) < 200 and not re.search(time_pattern, next_line):
                        # This is likely part of the title or a standalone venue
                        # Look ahead to see if there's a time line coming
                        found_time_ahead = False
                        for j in range(i + 1, min(i + 3, len(lines))):
                            if re.search(time_pattern, lines[j].strip()):
                                found_time_ahead = True
                                break
                        
                        if found_time_ahead:
                            # Combine this line with the title
                            full_title += " " + next_line
                            i += 1
                        else:
                            break
                    else:
                        break
                
                # Now get the time+venue line
                if i < len(lines):
                    time_venue_line = lines[i].strip()
                    
                    # Check if next line has time
                    if time_venue_line and re.search(time_pattern, time_venue_line):
                        start_time = re.search(time_pattern, time_venue_line).group(0)
                        
                        # Extract venue (everything after time)
                        venue = re.sub(time_pattern, '', time_venue_line).strip()
                        
                        # If no venue on this line, it might be on the next line
                        if not venue and i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            # Check if next line is NOT a time and NOT a title (no colon)
                            if (next_line and len(next_line) > 2 and
                                not re.search(time_pattern, next_line) and
                                not re.search(date_pattern, next_line) and
                                next_line not in ['Like', 'Comment', 'Share']):
                                venue = next_line
                                i += 1  # Consume the venue line
                        
                        if not venue:
                            venue = get_venue_name(url, venues)
                        
                        # Create event
                        event_key = (event_date, full_title, venue)
                        if event_key not in extracted_events and is_event_in_date_range(event_date):
                            event = {
                                'title': full_title[:100],
                                'location': venue[:100],
                                'address': get_venue_address(url, venues),
                                'date': normalize_date(event_date) or event_date,  # Normalize date
                                'start_time': start_time,
                                'end_time': None,
                                'description': f"{full_title} at {venue}",
                                'image_url': None,
                                'organizer': venue[:100],
                                'url': url,
                                'link': url,
                                'source': 'facebook_posts',
                                'scraped_at': datetime.now().isoformat(),
                                'tags': ['event', 'facebook-post']
                            }
                            event['event_id'] = hashlib.md5(f"{venue}{event_date}{full_title}".encode()).hexdigest()
                            extracted_events[event_key] = event
                            logger.debug(f"  Extracted: {full_title[:40]} at {start_time} @ {venue[:30]}")
                        
                        i += 1  # Consume the time_venue_line
        
        events = list(extracted_events.values())
        if events:
            logger.info(f"📰 [Worker] Extracted {len(events)} events from feed posts at {url}")
        else:
            logger.debug(f"📰 [Worker] No events found in feed posts from {url}")
    
    except Exception as e:
        logger.error(f"❌ [Feed] Error extracting events: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return events


def save_to_elasticsearch(events):
    """Save events to Elasticsearch, skipping existing events
    
    Events should be pre-deduplicated before calling this function.
    """
    if not events:
        logger.warning("No events to save")
        return
    
    try:
        from elasticsearch import Elasticsearch
        
        # Use localhost for direct connection, container hostname for Docker
        es = Elasticsearch(['http://localhost:9200'])
        
        saved = 0
        skipped = 0
        
        for event in events:
            # Check if event already exists
            try:
                existing = es.get(index='events', id=event['event_id'])
                logger.debug(f"⏭️  Skipped existing event: {event['title']}")
                skipped += 1
            except:
                # Event doesn't exist, index it
                result = es.index(
                    index='events',
                    id=event['event_id'],
                    document=event
                )
                logger.info(f"✅ Indexed event: {event['title']}")
                saved += 1
        
        logger.info(f"✅ Saved {saved} new events, skipped {skipped} existing events to Elasticsearch")
    
    except Exception as e:
        logger.error(f"❌ Error saving to Elasticsearch: {e}")

def deduplicate_events(events):
    """Deduplicate events by exact date + fuzzy title matching before saving
    
    This ensures that when the same event appears from multiple sources/locations,
    they get merged into a single record with multiple sources listed.
    Uses fuzzy string matching to catch similar titles (e.g., truncated text).
    Requires EXACT date match - events on different dates are treated as separate events.
    """
    deduplicated = {}
    merged_count = 0
    fuzzy_matches_found = []
    
    def normalize_date(date_str):
        """Convert various date formats to YYYY-MM-DD for comparison"""
        if not date_str:
            return None
        
        try:
            # Try parsing if it's already in YYYY-MM-DD format
            from datetime import datetime
            if isinstance(date_str, str):
                # Already normalized format
                if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                    return date_str
                
                # Try common formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y', '%Y/%m/%d']:
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
        except:
            pass
        
        # Return original if can't parse
        return date_str.strip() if isinstance(date_str, str) else str(date_str)
    
    def fuzzy_match(str1, str2, threshold=0.85):
        """Check if two strings are similar enough to be the same"""
        ratio = SequenceMatcher(None, str(str1).lower().strip(), str(str2).lower().strip()).ratio()
        return ratio >= threshold
    
    logger.info(f"🔍 Starting deduplication on {len(events)} events...")
    
    for event in events:
        # Normalize the date
        event_date = normalize_date(event.get('date', ''))
        event_title = event.get('title', '').lower().strip()
        
        # Try to find a matching event in deduplicated dict
        found_match = False
        for existing_key, existing_event in deduplicated.items():
            existing_date, existing_title = existing_key
            
            # EXACT date match required - different dates = different events
            # Titles must be fuzzy similar (catches truncated text, minor variations)
            if existing_date == event_date and fuzzy_match(event_title, existing_title, threshold=0.85):
                # Found a match - merge sources
                ratio = SequenceMatcher(None, event_title, existing_title).ratio()
                fuzzy_matches_found.append({
                    'ratio': ratio,
                    'title1': event_title[:50],
                    'title2': existing_title[:50],
                    'date': event_date
                })
                
                # Initialize sources array if not present
                if 'sources' not in existing_event:
                    existing_event['sources'] = [existing_event.get('url', 'unknown')]
                
                # Add new source if not already there
                if event.get('url') not in existing_event.get('sources', []):
                    existing_event['sources'].append(event['url'])
                
                # Also track the location if different
                if 'locations' not in existing_event:
                    existing_event['locations'] = [existing_event.get('location', 'unknown')]
                if event.get('location') not in existing_event.get('locations', []):
                    existing_event['locations'].append(event['location'])
                
                logger.info(f"🎯 Fuzzy match found ({ratio:.0%}): {existing_event['title'][:50]} ({event_date})")
                logger.debug(f"   Title 1: {event_title[:60]}")
                logger.debug(f"   Title 2: {existing_title[:60]}")
                logger.debug(f"   Merged from: {event.get('url', 'unknown')}")
                logger.debug(f"   Sources: {existing_event['sources']}")
                merged_count += 1
                found_match = True
                break
        
        if not found_match:
            # New event - normalize date in the event object
            event['date'] = event_date
            key = (event_date, event_title)
            event['sources'] = [event.get('url', 'unknown')]
            event['locations'] = [event.get('location', 'unknown')]
            deduplicated[key] = event
    
    result = list(deduplicated.values())
    if merged_count > 0:
        logger.info(f"🔀 Deduplication complete: merged {merged_count} duplicates → {len(result)} unique events")
        if fuzzy_matches_found:
            logger.info(f"   Found {len(fuzzy_matches_found)} fuzzy title matches")
            for match in fuzzy_matches_found[:5]:  # Log first 5
                logger.debug(f"   - {match['ratio']:.0%} similar: '{match['title1']}' ↔ '{match['title2']}'")
    
    return result


def main():
    """Main function"""
    logger.info("🚀 Starting Facebook Headless Scraper with Multiprocessing")
    
    # Load data
    urls = load_facebook_urls()
    venues = load_venue_info()
    
    if not urls:
        logger.error("No Facebook URLs to scrape")
        return
    
    # Use more workers for faster scraping (anti-detection built into scrape_url with random delays)
    num_workers = max(2, min(cpu_count() - 1, 6))  # Use 2-6 workers depending on CPU cores
    logger.info(f"🚀 Scraping {len(urls)} URLs using {num_workers} workers")
    
    # Create worker args
    worker_args = [(url, venues) for url in urls]
    
    # Run multiprocessing pool
    all_events = []
    
    with Pool(processes=num_workers) as pool:
        for result in pool.imap_unordered(scrape_url, worker_args):
            all_events.extend(result)
    
    logger.info(f"🌐 Total events extracted: {len(all_events)}")
    
    # Deduplicate events before saving
    if all_events:
        all_events = deduplicate_events(all_events)
        save_to_elasticsearch(all_events)
    else:
        logger.warning("No events were extracted")


if __name__ == '__main__':
    main()
