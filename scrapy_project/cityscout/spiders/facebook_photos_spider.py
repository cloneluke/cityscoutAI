import scrapy
from cityscout.items import EventItem
from datetime import datetime
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


class FacebookPhotoSpider(scrapy.Spider):
    """Spider for extracting event information from Facebook photo posts
    
    Handles direct Facebook photo URLs like:
    https://www.facebook.com/photo.php?fbid=1449282227200521&set=...
    
    Uses image processing to extract event details from photos
    """
    
    name = 'facebook_photos'
    allowed_domains = ['facebook.com']
    
    # Photo URLs can be passed as argument: -a photo_urls=url1,url2
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 5,
    }
    
    def __init__(self, photo_urls=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_service = ImageService() if HAS_IMAGE_SERVICE else None
        
        # Parse photo URLs from argument
        if photo_urls:
            self.photo_urls = [url.strip() for url in photo_urls.split(',')]
        else:
            self.photo_urls = []
        
        self.start_urls = []
        self.logger.info(f"Initialized Facebook Photo spider for {len(self.photo_urls)} photos")
        if self.image_service:
            self.logger.info("Image processing service enabled")
    
    def start_requests(self):
        """Generate requests for photo URLs"""
        for photo_url in self.photo_urls:
            self.logger.info(f"Requesting photo: {photo_url}")
            yield scrapy.Request(
                photo_url,
                callback=self.parse_photo,
                meta={'dont_obey_robotstxt': True},
                errback=self.errback_photo
            )
    
    def errback_photo(self, failure):
        """Handle request errors"""
        self.logger.warning(f"Failed to fetch photo: {failure.request.url}")
        self.logger.warning(f"Error: {failure.value}")
    
    def parse_photo(self, response):
        """Parse Facebook photo page and extract event information"""
        
        try:
            photo_url = response.url
            self.logger.info(f"Parsing photo from: {photo_url}")
            
            # Try to extract the actual image URL from the page
            # Facebook stores images in various ways
            image_urls = []
            
            # Method 1: Look for og:image meta tag (highest quality)
            og_image = response.xpath('//meta[@property="og:image"]/@content').get()
            if og_image:
                image_urls.append(og_image)
                self.logger.info(f"Found og:image: {og_image}")
            
            # Method 2: Look for img tags with facebook/photo in src
            img_sources = response.xpath('//img[contains(@src, "photo")]/@src').getall()
            image_urls.extend(img_sources)
            
            # Method 3: Look for large image tags
            large_imgs = response.xpath('//img[contains(@class, "img")]/@src').getall()
            for img in large_imgs:
                if 'facebook' in img and 'photo' in img:
                    image_urls.append(img)
            
            # Extract caption/description which might contain event info
            caption = response.xpath('//div[@data-testid="photo_description"]//text()').getall()
            if not caption:
                caption = response.xpath('//div[@data-testid="post_message"]//text()').getall()
            if not caption:
                # Fallback: get all text near images
                caption = response.css('div._4-u2, div._3058 ::text').getall()
            
            caption_text = ' '.join(caption).strip() if caption else ''
            
            self.logger.info(f"Found {len(image_urls)} images and caption: {caption_text[:100]}")
            
            # Process each image found
            for image_url in image_urls:
                if not image_url:
                    continue
                
                event_item = self.extract_event_from_photo(
                    image_url, 
                    caption_text, 
                    photo_url
                )
                
                if event_item:
                    yield event_item
            
            # If no images found but there's caption text, try to create event from text
            if not image_urls and caption_text:
                self.logger.info(f"No images found, extracting from caption text")
                event_item = self.create_event_from_text(caption_text, photo_url)
                if event_item:
                    yield event_item
        
        except Exception as e:
            self.logger.error(f"Error parsing photo {response.url}: {e}")
    
    def extract_event_from_photo(self, image_url: str, caption: str, photo_url: str):
        """Extract event information from a photo and its caption"""
        
        try:
            if not self.image_service:
                self.logger.warning("Image service not available, using text-only extraction")
                return self.create_event_from_text(caption, photo_url)
            
            self.logger.info(f"Processing image for event info: {image_url[:50]}...")
            
            # Check if likely an event image
            if not self.image_service.is_likely_event_image(image_url):
                self.logger.info(f"Image does not appear to be event-related")
                # Still try text if available
                if caption:
                    return self.create_event_from_text(caption, photo_url)
                return None
            
            # Extract event info from image
            image_info = self.image_service.extract_event_info_from_image(image_url)
            
            if not image_info or not image_info.get('confidence') in ['high', 'medium']:
                self.logger.warning(f"Low confidence event extraction from image")
                # Fallback to text
                if caption:
                    return self.create_event_from_text(caption, photo_url)
                return None
            
            # Create event item from image data
            item = EventItem()
            
            # Use image data with caption as fallback
            item['title'] = image_info.get('title') or 'Event from Photo'
            item['date'] = image_info.get('date') or 'TBA'
            item['start_time'] = image_info.get('time') or ''
            item['end_time'] = None
            item['location'] = image_info.get('location') or 'TBA'
            item['address'] = image_info.get('address') or image_info.get('location') or 'TBA'
            
            # Combine image description with caption
            description_parts = []
            if image_info.get('description'):
                description_parts.append(image_info['description'])
            if caption:
                description_parts.append(caption[:200])
            item['description'] = ' | '.join(description_parts)
            
            item['image_url'] = image_url
            item['organizer'] = image_info.get('performers', ['Unknown'])[0] if image_info.get('performers') else 'Unknown'
            item['attendee_count'] = 0
            item['url'] = photo_url
            item['source'] = 'facebook_photo'
            item['scraped_at'] = datetime.now().isoformat()
            
            # Generate unique event ID
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            
            # Create tags
            item['tags'] = ['event', 'facebook-photo', 'image-extracted']
            if image_info.get('performers'):
                item['tags'].extend([p.lower().replace(' ', '-') for p in image_info['performers']])
            
            self.logger.info(f"Created event from photo: {item['title']}")
            return item
        
        except Exception as e:
            self.logger.error(f"Error extracting event from photo: {e}")
            return None
    
    def create_event_from_text(self, text: str, photo_url: str):
        """Create event from caption text if image processing fails"""
        
        try:
            if not text or len(text.strip()) < 10:
                return None
            
            item = EventItem()
            
            # Extract title (first line or first 100 chars)
            lines = text.split('\n')
            item['title'] = lines[0][:100].strip() or 'Event from Photo'
            
            item['description'] = text[:500].strip()
            
            # Try to find dates
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?\b'
            date_matches = re.findall(date_pattern, text, re.IGNORECASE)
            item['date'] = date_matches[0] if date_matches else 'TBA'
            
            # Try to find times
            time_pattern = r'\b(?:\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}\s*(?:AM|PM|am|pm))\b'
            time_matches = re.findall(time_pattern, text)
            item['start_time'] = time_matches[0] if time_matches else ''
            item['end_time'] = None
            
            item['location'] = 'TBA'
            item['address'] = 'TBA'
            item['image_url'] = None
            item['organizer'] = 'Unknown'
            item['attendee_count'] = 0
            item['url'] = photo_url
            item['source'] = 'facebook_photo'
            item['scraped_at'] = datetime.now().isoformat()
            
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            
            item['tags'] = ['event', 'facebook-photo', 'text-extracted']
            
            self.logger.info(f"Created event from photo caption: {item['title']}")
            return item
        
        except Exception as e:
            self.logger.error(f"Error creating event from text: {e}")
            return None
