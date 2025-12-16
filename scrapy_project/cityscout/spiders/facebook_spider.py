import scrapy
from cityscout.items import EventItem
from datetime import datetime, timedelta
import hashlib
import logging
import re
import os
import sys
import json
import requests

# Add backend path to import image service
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from app.services.image_service import ImageService
    HAS_IMAGE_SERVICE = True
except ImportError:
    HAS_IMAGE_SERVICE = False
    logging.warning("ImageService not available - image processing disabled")


class FacebookSpider(scrapy.Spider):
    """Spider for scraping Facebook page/account for events and event-related posts"""
    
    name = 'facebook'
    allowed_domains = ['facebook.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = []
        self.photo_urls = []  # Store photo URLs to process
        self.post_urls = []   # Store post URLs to process
        self.venues = {}  # Store venue information
        self.load_facebook_urls()
        self.load_facebook_photo_urls()
        self.load_facebook_post_urls()
        self.load_venue_info()
        self.image_service = ImageService() if HAS_IMAGE_SERVICE else None
        self.logger.info(f"Initialized Facebook spider for {len(self.start_urls)} pages, {len(self.photo_urls)} photos, and {len(self.post_urls)} posts")
        if self.image_service:
            self.logger.info("Image processing service enabled")
    
    def load_facebook_urls(self):
        """Load Facebook URLs from data/facebook_urls.txt"""
        try:
            # Determine the correct path based on where the spider is being run from
            # The spider directory is cityscout/spiders/, so go up 3 levels to reach data/
            spider_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(spider_dir)))
            
            possible_paths = [
                # Relative to spider file location
                os.path.join(os.path.dirname(__file__), '../../data/facebook_urls.txt'),
                # Relative to project root
                os.path.join(project_root, 'data/facebook_urls.txt'),
                # From common run locations
                '/home/luke/git-repos/cityscoutAI/data/facebook_urls.txt',
                './data/facebook_urls.txt',
                '../data/facebook_urls.txt',
                '../../data/facebook_urls.txt',
                '../../../data/facebook_urls.txt',
            ]
            
            self.logger.info(f"Looking for facebook_urls.txt in: {possible_paths}")
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self.logger.info(f"Found facebook_urls.txt at: {abs_path}")
                    with open(abs_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                # Extract both main page and events section
                                self.start_urls.append(line)
                                if '/events' not in line:
                                    self.start_urls.append(f"{line}/events")
                    
                    self.logger.info(f"Loaded {len(set(self.start_urls))} unique URLs from {abs_path}")
                    self.logger.info(f"URLs to crawl: {self.start_urls}")
                    return
            
            # Fallback to default if no file found
            self.logger.warning("facebook_urls.txt not found, using default page")
            self.logger.warning(f"Checked these paths: {possible_paths}")
            self.start_urls = [
                'https://www.facebook.com/SeveranceBrewing',
                'https://www.facebook.com/SeveranceBrewing/events',
            ]
        except Exception as e:
            self.logger.error(f"Error loading Facebook URLs: {e}")
            self.logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            self.start_urls = [
                'https://www.facebook.com/SeveranceBrewing',
                'https://www.facebook.com/SeveranceBrewing/events',
            ]
    
    def load_facebook_photo_urls(self):
        """Load Facebook photo URLs from data/facebook_photo_urls.txt"""
        try:
            spider_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(spider_dir)))
            
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '../../data/facebook_photo_urls.txt'),
                os.path.join(project_root, 'data/facebook_photo_urls.txt'),
                '/home/luke/git-repos/cityscoutAI/data/facebook_photo_urls.txt',
                './data/facebook_photo_urls.txt',
            ]
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self.logger.info(f"Found facebook_photo_urls.txt at: {abs_path}")
                    with open(abs_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                # Parse format: facebook_page | photo_url | image_url | caption
                                parts = [p.strip() for p in line.split('|')]
                                if len(parts) >= 2:
                                    page_url = parts[0]
                                    photo_url = parts[1]
                                    image_url = parts[2] if len(parts) > 2 else None
                                    caption = parts[3] if len(parts) > 3 else None
                                    
                                    self.photo_urls.append({
                                        'page_url': page_url,
                                        'photo_url': photo_url,
                                        'image_url': image_url,
                                        'caption': caption
                                    })
                    
                    self.logger.info(f"Loaded {len(self.photo_urls)} photo URLs from {abs_path}")
                    return
            
            self.logger.debug("facebook_photo_urls.txt not found - no photo URLs to process")
        except Exception as e:
            self.logger.error(f"Error loading Facebook photo URLs: {e}")
    
    def load_facebook_post_urls(self):
        """Load Facebook post URLs from data/facebook_post_urls.txt"""
        try:
            spider_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(spider_dir)))
            
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '../../data/facebook_post_urls.txt'),
                os.path.join(project_root, 'data/facebook_post_urls.txt'),
                '/home/luke/git-repos/cityscoutAI/data/facebook_post_urls.txt',
                './data/facebook_post_urls.txt',
            ]
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self.logger.info(f"Found facebook_post_urls.txt at: {abs_path}")
                    with open(abs_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                # Parse format: facebook_page | post_url | caption
                                parts = [p.strip() for p in line.split('|')]
                                if len(parts) >= 2:
                                    page_url = parts[0]
                                    post_url = parts[1]
                                    caption = parts[2] if len(parts) > 2 else None
                                    
                                    self.post_urls.append({
                                        'page_url': page_url,
                                        'post_url': post_url,
                                        'caption': caption
                                    })
                    
                    self.logger.info(f"Loaded {len(self.post_urls)} post URLs from {abs_path}")
                    return
            
            self.logger.debug("facebook_post_urls.txt not found - no post URLs to process")
        except Exception as e:
            self.logger.error(f"Error loading Facebook post URLs: {e}")
    
    def load_venue_info(self):
        """Load venue information from data/facebook_venues.txt"""
        try:
            spider_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(spider_dir)))
            
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '../../data/facebook_venues.txt'),
                os.path.join(project_root, 'data/facebook_venues.txt'),
                '/home/luke/git-repos/cityscoutAI/data/facebook_venues.txt',
                './data/facebook_venues.txt',
            ]
            
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self.logger.info(f"Found facebook_venues.txt at: {abs_path}")
                    with open(abs_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                # Parse format: facebook_url | venue_name | address | city | state | country
                                parts = [p.strip() for p in line.split('|')]
                                if len(parts) >= 3:
                                    facebook_url = parts[0]
                                    venue_name = parts[1]
                                    address = parts[2]
                                    city = parts[3] if len(parts) > 3 else ''
                                    state = parts[4] if len(parts) > 4 else ''
                                    country = parts[5] if len(parts) > 5 else ''
                                    
                                    self.venues[facebook_url] = {
                                        'name': venue_name,
                                        'address': address,
                                        'city': city,
                                        'state': state,
                                        'country': country
                                    }
                    
                    self.logger.info(f"Loaded {len(self.venues)} venue definitions from {abs_path}")
                    return
            
            self.logger.debug("facebook_venues.txt not found - will use URL-based names")
        except Exception as e:
            self.logger.error(f"Error loading venue info: {e}")
    
    def get_venue_info(self, facebook_url):
        """Get venue information for a Facebook URL"""
        return self.venues.get(facebook_url, {})
    
    def start_requests(self):
        """Generate requests for page URLs, photo URLs, and post URLs"""
        # Generate requests for regular page URLs
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, meta={'dont_obey_robotstxt': True})
        
        # Generate requests for photo URLs
        for photo_data in self.photo_urls:
            self.logger.info(f"Processing photo from {photo_data['page_url']}")
            yield scrapy.Request(
                photo_data['photo_url'],
                callback=self.parse_photo,
                meta={
                    'dont_obey_robotstxt': True,
                    'photo_data': photo_data
                },
                errback=self.errback_photo
            )
        
        # Generate requests for post URLs
        for post_data in self.post_urls:
            self.logger.info(f"Processing post from {post_data['page_url']}")
            yield scrapy.Request(
                post_data['post_url'],
                callback=self.parse_post,
                meta={
                    'dont_obey_robotstxt': True,
                    'post_data': post_data
                },
                errback=self.errback_post
            )
    
    def errback_photo(self, failure):
        """Handle photo request errors"""
        self.logger.warning(f"Failed to fetch photo: {failure.request.url}")
        self.logger.debug(f"Error: {failure.value}")
        
        # Try to extract event from provided image_url directly
        photo_data = failure.request.meta.get('photo_data')
        if photo_data and photo_data.get('image_url'):
            self.logger.info(f"Attempting direct image processing from provided URL")
            event_item = self.extract_event_from_photo(photo_data)
            if event_item:
                yield event_item
    
    def parse_photo(self, response):
        """Parse a Facebook photo and extract event information"""
        try:
            photo_data = response.meta.get('photo_data', {})
            self.logger.info(f"Parsing photo page")
            
            # Try to find image URL from page
            if not photo_data.get('image_url'):
                og_image = response.xpath('//meta[@property="og:image"]/@content').get()
                if og_image:
                    photo_data['image_url'] = og_image
                    self.logger.info(f"Found image from og:image: {og_image[:50]}...")
            
            # Try to extract caption
            if not photo_data.get('caption'):
                caption_parts = response.xpath('//div[@data-testid="photo_description"]//text()').getall()
                if caption_parts:
                    photo_data['caption'] = ' '.join(caption_parts)
            
            event_item = self.extract_event_from_photo(photo_data)
            if event_item:
                yield event_item
        
        except Exception as e:
            self.logger.error(f"Error parsing photo: {e}")
    
    def extract_event_from_photo(self, photo_data):
        """Extract event information from photo data"""
        try:
            image_url = photo_data.get('image_url')
            caption = photo_data.get('caption', '')
            photo_url = photo_data.get('photo_url', '')
            page_url = photo_data.get('page_url', '')
            
            if not image_url:
                self.logger.warning("No image URL available for event extraction")
                return None
            
            self.logger.info(f"Processing image: {image_url[:50]}...")
            
            # Check if image service available
            if not self.image_service:
                self.logger.warning("Image service not available")
                return None
            
            # Check if likely event image
            if not self.image_service.is_likely_event_image(image_url):
                self.logger.info("Image does not appear to be event-related")
                return None
            
            # Extract event info
            image_info = self.image_service.extract_event_info_from_image(image_url)
            
            if not image_info or image_info.get('confidence') not in ['high', 'medium']:
                self.logger.warning("Low confidence event extraction")
                return None
            
            # Get venue info for this Facebook page
            venue_info = self.get_venue_info(page_url)
            
            item = EventItem()
            item['title'] = image_info.get('title', 'Event from Photo')
            item['date'] = image_info.get('date', 'TBA')
            item['start_time'] = image_info.get('time', '')
            item['end_time'] = None
            
            # Use venue info for location and address
            item['location'] = venue_info.get('name') or image_info.get('location', 'TBA')
            item['address'] = venue_info.get('address') or image_info.get('address', item['location'])
            
            # Combine image description with caption
            descriptions = []
            if image_info.get('description'):
                descriptions.append(image_info['description'])
            if caption:
                descriptions.append(caption)
            item['description'] = ' | '.join(descriptions)
            
            item['image_url'] = image_url
            item['organizer'] = venue_info.get('name') or page_url.split('/')[-1] or 'Unknown'
            item['attendee_count'] = 0
            item['url'] = photo_url
            item['source'] = 'facebook_photo'
            item['scraped_at'] = datetime.now().isoformat()
            
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            item['tags'] = ['event', 'facebook-photo', 'image-extracted']
            
            self.logger.info(f"✅ Created event from photo: {item['title']}")
            return item
        
        except Exception as e:
            self.logger.error(f"Error extracting event from photo: {e}")
            return None
    
    def parse(self, response):
        """Parse Facebook page and extract events"""
        
        try:
            # Look for event links on the page
            event_links = response.css('a[href*="/events/"]::attr(href)').getall()
            event_links += response.xpath('//a[contains(@href, "/events/")]/@href').getall()
            
            if event_links:
                self.logger.info(f"Found {len(event_links)} potential event links at {response.url}")
                for link in event_links:
                    # Ensure absolute URL
                    if link.startswith('http'):
                        yield scrapy.Request(link, callback=self.parse_event, meta={'dont_obey_robotstxt': True})
                    elif link.startswith('/'):
                        yield scrapy.Request(f"https://www.facebook.com{link}", callback=self.parse_event, meta={'dont_obey_robotstxt': True})
            
            # Also look for posts that mention events
            posts = response.css('[data-testid="post"]')
            self.logger.info(f"Found {len(posts)} posts to analyze at {response.url}")
            
            for post in posts:
                # Extract post text
                post_text = ' '.join(post.css('::text').getall())
                
                # Check if post contains event-related keywords
                event_keywords = ['event', 'show', 'concert', 'gig', 'performance', 'live', 'ticket', 'date', 'time']
                if any(keyword in post_text.lower() for keyword in event_keywords):
                    self.logger.info(f"Found event-related post: {post_text[:100]}")
                    # Yield item from post data
                    yield self.parse_post_as_event(post, post_text)
        
        except Exception as e:
            self.logger.error(f"Error parsing page {response.url}: {e}")
    
    def parse_event(self, response):
        """Parse individual Facebook event page"""
        
        try:
            item = EventItem()
            
            # Extract event title
            title = response.css('h1::text').get()
            if not title:
                title = response.css('[role="heading"]::text').get()
            if not title:
                title = response.xpath('//meta[@property="og:title"]/@content').get()
            
            item['title'] = (title or 'Unknown Event').strip()
            
            # Extract event description
            description_selectors = [
                response.css('[data-testid="event_description"]::text').get(),
                response.xpath('//meta[@property="og:description"]/@content').get(),
                ' '.join(response.css('span::text').getall())[:500]
            ]
            item['description'] = next((d for d in description_selectors if d), '')
            
            # Extract location/address
            location_selectors = [
                response.css('[data-testid="event_location"]::text').get(),
                response.xpath('//span[contains(text(), "Location")]//following-sibling::span//text()').get(),
                response.xpath('//meta[@property="og:location"]/@content').get()
            ]
            location = next((l for l in location_selectors if l), 'TBA')
            item['location'] = location.strip() if location else 'TBA'
            item['address'] = item['location']
            
            # Extract event date and time
            date_text = response.css('[data-testid="event_date"]::text').get()
            if not date_text:
                date_text = response.xpath('//span[contains(text(), "Date")]//following-sibling::span//text()').get()
            if not date_text:
                # Try to extract from og:updated_time
                date_text = response.xpath('//meta[@property="article:published_time"]/@content').get()
            
            item['date'] = date_text.strip() if date_text else 'TBA'
            
            # Extract time if separate from date
            time_selectors = [
                response.css('[data-testid="event_time"]::text').get(),
                response.xpath('//span[contains(text(), "Time")]//following-sibling::span//text()').get()
            ]
            item['start_time'] = next((t for t in time_selectors if t), '').strip()
            item['end_time'] = ''
            
            # Extract image
            image_selectors = [
                response.css('img[alt*="event"]::attr(src)').get(),
                response.xpath('//meta[@property="og:image"]/@content').get(),
                response.css('img[role="presentation"]::attr(src)').get()
            ]
            item['image_url'] = next((img for img in image_selectors if img), '')
            
            # Extract organizer
            organizer_selectors = [
                response.css('[data-testid="event_organizer"]::text').get(),
                response.xpath('//span[contains(text(), "Hosted by")]//following-sibling::span//text()').get(),
                self.facebook_page
            ]
            item['organizer'] = next((org for org in organizer_selectors if org), 'Unknown').strip()
            
            # Extract attendee count
            attendee_text = ' '.join(response.css('::text').getall())
            attendee_match = re.search(r'(\d+(?:,\d+)?)\s*(?:people|attendees?|interested)', attendee_text, re.IGNORECASE)
            item['attendee_count'] = attendee_match.group(1) if attendee_match else '0'
            
            # Set source and URL
            item['url'] = response.url
            item['source'] = 'facebook'
            item['scraped_at'] = datetime.now().isoformat()
            
            # Generate unique event ID for deduplication
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            
            # Initialize tags (will be filled by AI service)
            item['tags'] = []
            
            # Only yield if we have meaningful data
            if item['title'] and item['title'] != 'Unknown Event':
                self.logger.info(f"Scraped event: {item['title']} on {item['date']}")
                yield item
            else:
                self.logger.warning(f"Skipped event with no title from {response.url}")
        
        except Exception as e:
            self.logger.error(f"Error parsing event page {response.url}: {e}")
    
    def parse_post_as_event(self, post, post_text):
        """Extract event data from a social media post"""
        
        try:
            item = EventItem()
            
            # Try to extract title from post text
            item['title'] = post_text[:100].strip()
            item['description'] = post_text[:500].strip()
            
            # Try to find date mentions in post
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?\b'
            date_matches = re.findall(date_pattern, post_text, re.IGNORECASE)
            item['date'] = date_matches[0] if date_matches else 'TBA'
            
            # Try to find time mentions
            time_pattern = r'\b(?:\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}\s*(?:AM|PM|am|pm))\b'
            time_matches = re.findall(time_pattern, post_text)
            item['start_time'] = time_matches[0] if time_matches else ''
            item['end_time'] = ''
            
            # Location from post
            item['location'] = self.facebook_page
            item['address'] = self.facebook_page
            
            # Organizer
            item['organizer'] = self.facebook_page
            
            # Other fields
            image_url = post.css('img::attr(src)').get() or ''
            item['image_url'] = image_url
            item['attendee_count'] = '0'
            item['url'] = f"https://www.facebook.com/{self.facebook_page}"
            item['source'] = 'facebook'
            item['scraped_at'] = datetime.now().isoformat()
            
            # Extract event info from images if available
            if image_url and self.image_service:
                self.logger.info(f"Processing image from post: {image_url[:50]}...")
                image_info = self.image_service.extract_event_info_from_image(image_url)
                
                if image_info and image_info.get('confidence') in ['high', 'medium']:
                    self.logger.info(f"Extracted from image: {image_info}")
                    
                    # Update item with image-extracted data (prefer image data if available)
                    if image_info.get('title') and image_info['title'] != 'null':
                        item['title'] = image_info['title']
                    if image_info.get('date') and image_info['date'] != 'null':
                        item['date'] = image_info['date']
                    if image_info.get('time') and image_info['time'] != 'null':
                        item['start_time'] = image_info['time']
                    if image_info.get('location') and image_info['location'] != 'null':
                        item['location'] = image_info['location']
                    if image_info.get('address') and image_info['address'] != 'null':
                        item['address'] = image_info['address']
                    if image_info.get('description'):
                        item['description'] = f"{post_text[:200]} | Image: {image_info.get('description', '')}"
            
            # Generate unique event ID
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            item['tags'] = []
            
            return item
        
        except Exception as e:
            self.logger.error(f"Error parsing post as event: {e}")
            return None
    
    def process_image_for_events(self, image_url: str) -> dict:
        """
        Process a single image and extract event information.
        Can be called independently to scan image-heavy pages.
        """
        if not self.image_service:
            return {}
        
        try:
            self.logger.info(f"Analyzing image for event info: {image_url}")
            
            # First check if it's likely an event image
            if not self.image_service.is_likely_event_image(image_url):
                self.logger.info(f"Image does not appear to be event-related")
                return {}
            
            # Extract event information
            event_info = self.image_service.extract_event_info_from_image(image_url)
            
            if event_info and event_info.get('confidence') in ['high', 'medium']:
                self.logger.info(f"Successfully extracted event info from image")
                return event_info
            
            return {}
        
        except Exception as e:
            self.logger.error(f"Error processing image: {e}")
            return {}
    
    def errback_post(self, failure):
        """Handle post request errors"""
        self.logger.warning(f"Failed to fetch post: {failure.request.url}")
        self.logger.debug(f"Error: {failure.value}")
    
    def parse_post(self, response):
        """Parse a Facebook post and extract embedded images and event information"""
        try:
            post_data = response.meta.get('post_data', {})
            post_url = post_data.get('post_url', '')
            page_url = post_data.get('page_url', '')
            post_caption = post_data.get('caption', '')
            
            self.logger.info(f"Parsing post: {post_url}")
            
            # Extract og:description meta tag (often contains event details)
            og_description = response.xpath('//meta[@property="og:description"]/@content').get()
            if og_description:
                self.logger.info(f"Found og:description: {og_description[:100]}...")
            
            # Try to extract event info from og:description if present
            event_created = False
            if og_description and self.image_service:
                self.logger.info(f"Attempting to extract event from og:description")
                event_item = self.extract_event_from_post_text(og_description, post_url, page_url)
                if event_item:
                    self.logger.info(f"✅ Extracted event from post description: {event_item.get('title')}")
                    yield event_item
                    event_created = True
            
            # Try multiple selectors to find images in the post
            # Facebook embeds images in various ways
            image_urls = []
            
            # Try og:image meta tag first (most reliable)
            og_image = response.xpath('//meta[@property="og:image"]/@content').get()
            if og_image:
                image_urls.append(og_image)
                self.logger.info(f"Found og:image: {og_image[:60]}...")
            
            # Try img tags with data attributes (Facebook's newer format)
            data_img_urls = response.xpath('//img[@src and contains(@src, "http")]/@src').getall()
            if data_img_urls:
                image_urls.extend([u for u in data_img_urls if u.startswith('http') and 'fbcdn' in u])
            
            # Try picture element sources
            picture_urls = response.xpath('//picture//img/@src').getall()
            if picture_urls:
                image_urls.extend([u for u in picture_urls if u.startswith('http')])
            
            # Try srcset parsing
            srcset_data = response.xpath('//img/@srcset').getall()
            for srcset in srcset_data:
                # srcset format: "url1 1x, url2 2x"
                urls = [u.strip().split()[0] for u in srcset.split(',')]
                image_urls.extend([u for u in urls if u.startswith('http')])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for url in image_urls:
                if url not in seen:
                    seen.add(url)
                    unique_images.append(url)
            image_urls = unique_images
            
            self.logger.info(f"Found {len(image_urls)} unique images in post")
            
            # Extract post text
            post_text_parts = response.xpath('//div[@data-testid="post_message"]//text()').getall()
            if not post_text_parts:
                post_text_parts = response.xpath('//div[contains(@class, "msg")]//text()').getall()
            if not post_text_parts:
                post_text_parts = response.css('span::text').getall()
            
            post_text = ' '.join([p.strip() for p in post_text_parts if p.strip()])
            if not post_text:
                post_text = post_caption
            
            self.logger.info(f"Extracted post text ({len(post_text)} chars): {post_text[:100]}...")
            
            # Try to extract event info from the POST TEXT itself (only if substantial text available)
            if not event_created and post_text and self.image_service and len(post_text.strip()) > 50:
                self.logger.info(f"Attempting to extract event info from post text")
                event_item = self.extract_event_from_post_text(post_text, post_url, page_url)
                if event_item:
                    self.logger.info(f"✅ Extracted event from post text: {event_item.get('title')}")
                    yield event_item
                    event_created = True
            
            # Also process images if available (even if text extraction worked)
            if not image_urls:
                self.logger.info(f"No images found in post {post_url}")
                # If no images and no event yet created, try fallback
                if not event_created:
                    fallback_event = self.create_fallback_post_event(post_url, page_url)
                    if fallback_event:
                        yield fallback_event
                return
            
            # NOTE: Image processing from posts is DISABLED
            # Reason: Facebook CDN URLs are signed, time-limited, and return HTTP 403
            # when accessed programmatically. Ollama cannot access them directly either.
            # 
            # Instead, we rely on og:description and text extraction via extract_event_from_post_text()
            # 
            # For manual image extraction when needed:
            # - Use: python3 extract_post_images.py
            # - Or: Add URLs to data/facebook_photo_urls.txt manually
            
            # Image processing loop DISABLED - skip to fallback
            # for idx, image_url in enumerate(image_urls, 1):
            #     ...image processing code...
            
            # If no events were created, try fallback
            if not event_created:
                fallback_event = self.create_fallback_post_event(post_url, page_url)
                if fallback_event:
                    yield fallback_event
        
        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
    
    def create_fallback_post_event(self, post_url, page_url):
        """Create a basic event item from post URL and venue information (fallback when content unavailable)"""
        try:
            venue_info = self.get_venue_info(page_url)
            
            # Only create fallback event if we have venue information
            if not venue_info.get('name'):
                self.logger.debug(f"No venue info found for {page_url}, cannot create fallback event")
                return None
            
            item = EventItem()
            item['title'] = f"Event at {venue_info.get('name')}"
            item['date'] = 'Check Facebook post'
            item['start_time'] = ''
            item['end_time'] = None
            item['location'] = venue_info.get('name')
            item['address'] = venue_info.get('address', '')
            
            # Create a helpful description with specific instructions
            venue_name = venue_info.get('name', 'venue')
            item['description'] = (
                f"Event posted at {venue_name}. "
                f"The image on the post contains event details but couldn't be analyzed programmatically. "
                f"To extract the full event info, copy the image from "
                f"[{post_url}] and either: "
                f"1) Use 'python3 extract_post_images.py' (interactive tool), or "
                f"2) Add directly to data/facebook_photo_urls.txt, then re-run the spider."
            )
            
            item['image_url'] = ''
            item['organizer'] = venue_info.get('name')
            item['attendee_count'] = 0
            item['url'] = post_url
            item['source'] = 'facebook_post'
            item['scraped_at'] = datetime.now().isoformat()
            
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            item['tags'] = ['event', 'facebook-post', 'needs-review', 'image-pending']
            
            self.logger.info(f"✅ Created fallback event from post: {item['title']}")
            return item
        
        except Exception as e:
            self.logger.error(f"Error creating fallback post event: {e}")
            return None
    
    def extract_event_from_post_text(self, post_text, post_url, page_url):
        """Extract event information from post text (without requiring image download)"""
        try:
            if not self.image_service:
                return None
            
            # Check if we actually have meaningful post text
            if not post_text or len(post_text.strip()) < 10:
                self.logger.debug(f"Post text too short or empty, cannot extract event")
                return None
            
            self.logger.info(f"Analyzing post text for event information: {post_text[:100]}...")
            
            # Use the image service's Ollama connection
            prompt = f"""Extract event details from this text. Return ONLY valid JSON with extracted info.

Text:
{post_text}

Required JSON response format (include all fields, use null for missing data):
{{
  "has_event": true/false,
  "title": "event name or null",
  "date": "date like 'Dec 10' or 'December 10th' or null",
  "time": "time like '7pm' or '7:00 PM' or null",
  "location": "venue name or null",
  "address": "street address or null",
  "ticket_price": "price or '$35' or null",
  "description": "1-2 sentence summary or null",
  "confidence": "high/medium/low - how confident you are there's an event here"
}}

Examples of has_event=true: "Join us for Holiday tasting Dec 10 7pm", "Concert Friday 8pm $20", "Event at Main St Saturday"
Examples of has_event=false: "Check out our menu", "See you around", "New photo albums"

IMPORTANT: Respond with ONLY the JSON object, no additional text."""

            response = requests.post(
                self.image_service.api_url,
                json={
                    'model': self.image_service.model,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.1  # Lower temp for more structured output
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '').strip()
                
                self.logger.debug(f"Ollama response for text extraction: {response_text[:200]}")
                
                # Try to parse JSON
                try:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        event_info = json.loads(json_match.group())
                        has_event = event_info.get('has_event', False)
                        confidence = event_info.get('confidence', 'low')
                        title = event_info.get('title')
                        
                        # Accept medium/high confidence, or low confidence if has_event=True and has title
                        should_create = (confidence in ['high', 'medium'] and title) or (has_event and title)
                        
                        if should_create:
                            # Create event item from extracted info
                            venue_info = self.get_venue_info(page_url)
                            
                            item = EventItem()
                            item['title'] = title or 'Event from Post'
                            item['date'] = event_info.get('date') or 'TBA'
                            item['start_time'] = event_info.get('time') or ''
                            item['end_time'] = None
                            item['location'] = venue_info.get('name') or event_info.get('location') or 'TBA'
                            item['address'] = venue_info.get('address') or event_info.get('address') or ''
                            item['description'] = event_info.get('description') or post_text[:200]
                            item['image_url'] = ''
                            item['organizer'] = venue_info.get('name') or page_url.split('/')[-1] or 'Unknown'
                            item['attendee_count'] = 0
                            item['url'] = post_url
                            item['source'] = 'facebook_post'
                            item['scraped_at'] = datetime.now().isoformat()
                            
                            event_hash = f"{item['title']}{item['date']}{item['location']}"
                            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
                            item['tags'] = ['event', 'facebook-post', 'text-extracted']
                            
                            self.logger.info(f"✅ Created event from post text: {item['title']} ({confidence} confidence)")
                            return item
                        else:
                            self.logger.info(f"No event detected in text (has_event={has_event}, confidence={confidence})")
                except Exception as parse_error:
                    self.logger.debug(f"Failed to parse JSON from post text analysis: {parse_error}")
            else:
                self.logger.warning(f"Ollama response status: {response.status_code}")
        
        except Exception as e:
            self.logger.error(f"Error extracting event from post text: {e}")
        
        return None
    