import scrapy
from cityscout.items import EventItem
from datetime import datetime, timedelta
import hashlib
import logging
import re


class FacebookSpider(scrapy.Spider):
    """Spider for scraping Facebook page/account for events and event-related posts"""
    
    name = 'facebook'
    allowed_domains = ['facebook.com']
    
    # Facebook page/account to scan
    facebook_page = 'SeveranceBrewing'
    
    # Different endpoints to check for events
    start_urls = [
        'https://www.facebook.com/SeveranceBrewing',
        'https://www.facebook.com/SeveranceBrewing/events',
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.info(f"Initialized Facebook spider for page: {self.facebook_page}")
    
    def parse(self, response):
        """Parse Facebook page and extract events"""
        
        try:
            # Look for event links on the page
            event_links = response.css('a[href*="/events/"]::attr(href)').getall()
            event_links += response.xpath('//a[contains(@href, "/events/")]/@href').getall()
            
            if event_links:
                self.logger.info(f"Found {len(event_links)} potential event links")
                for link in event_links:
                    # Ensure absolute URL
                    if link.startswith('http'):
                        yield scrapy.Request(link, callback=self.parse_event, dont_obey_robotstxt=True)
                    elif link.startswith('/'):
                        yield scrapy.Request(f"https://www.facebook.com{link}", callback=self.parse_event, dont_obey_robotstxt=True)
            
            # Also look for posts that mention events
            posts = response.css('[data-testid="post"]')
            self.logger.info(f"Found {len(posts)} posts to analyze")
            
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
            item['image_url'] = post.css('img::attr(src)').get() or ''
            item['attendee_count'] = '0'
            item['url'] = f"https://www.facebook.com/{self.facebook_page}"
            item['source'] = 'facebook'
            item['scraped_at'] = datetime.now().isoformat()
            
            # Generate unique event ID
            event_hash = f"{item['title']}{item['date']}{item['location']}"
            item['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            item['tags'] = []
            
            return item
        
        except Exception as e:
            self.logger.error(f"Error parsing post as event: {e}")
            return None
