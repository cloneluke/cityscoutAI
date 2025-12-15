import scrapy
from cityscout.items import EventItem
from datetime import datetime, timedelta
import hashlib
import logging
import re
import os
import sys
import json

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
            
            # Extract all images from the post
            image_urls = response.xpath('//img[@class="scaledImageFitWidth"]/@src').getall()
            
            # Also try other image selectors
            if not image_urls:
                image_urls = response.xpath('//img[contains(@class, "img")]/@src').getall()
            
            if not image_urls:
                og_image = response.xpath('//meta[@property="og:image"]/@content').get()
                if og_image:
                    image_urls = [og_image]
            
            self.logger.info(f"Found {len(image_urls)} images in post")
            
            # Extract post text
            post_text_parts = response.xpath('//div[@data-testid="post_message"]//text()').getall()
            post_text = ' '.join(post_text_parts) if post_text_parts else post_caption
            
            if not image_urls:
                self.logger.warning(f"No images found in post {post_url}")
                return
            
            # Process each image from the post
            for idx, image_url in enumerate(image_urls, 1):
                # Clean up image URL
                image_url = image_url.split('?')[0] if '?' in image_url else image_url
                
                if not image_url.startswith('http'):
                    continue
                
                self.logger.info(f"Processing post image {idx}/{len(image_urls)}: {image_url[:50]}...")
                
                # Create photo data for image processing
                photo_data = {
                    'page_url': page_url,
                    'post_url': post_url,
                    'photo_url': image_url,
                    'image_url': image_url,
                    'caption': post_text
                }
                
                # Extract event from this image
                event_item = self.extract_event_from_photo(photo_data)
                if event_item:
                    yield event_item
        
        except Exception as e:
            self.logger.error(f"Error parsing post: {e}")
