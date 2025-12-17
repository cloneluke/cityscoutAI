"""Meetup.com event spider"""

import scrapy
from cityscout.spiders.base_spider import BaseWebsiteSpider
import re


class MeetupSpider(BaseWebsiteSpider):
    """Spider for scraping Meetup.com events for Sioux Falls area"""
    
    name = 'meetup'
    allowed_domains = ['meetup.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Start URLs for Sioux Falls area meetup groups
        self.start_urls = [
            'https://www.meetup.com/find/?keywords=sioux%20falls&location=Sioux%20Falls%2C%20SD',
            'https://www.meetup.com/find/?keywords=technology&location=Sioux%20Falls%2C%20SD',
            'https://www.meetup.com/find/?keywords=business&location=Sioux%20Falls%2C%20SD',
            'https://www.meetup.com/find/?keywords=social&location=Sioux%20Falls%2C%20SD',
        ]
        self.logger.info(f"🌐 [{self.name}] Initialized with {len(self.start_urls)} search URLs")
    
    def parse(self, response):
        """Parse Meetup search results"""
        # Find event cards on the page
        event_cards = response.css('div[class*="eventCard"]')
        self.logger.info(f"🔍 [{self.name}] Found {len(event_cards)} event cards on {response.url}")
        
        for card in event_cards:
            # Extract event details
            title = card.css('h3::text').get()
            date_text = card.css('div[class*="eventDate"]::text').get()
            location = card.css('div[class*="eventLocation"]::text').get()
            event_url = card.css('a::attr(href)').get()
            organizer = card.css('div[class*="groupName"]::text').get()
            
            if title and date_text:
                # Clean and normalize
                title = title.strip()
                date = self.extract_date(date_text)
                location = location.strip() if location else "Sioux Falls, SD"
                
                # Build full URL if relative
                if event_url and not event_url.startswith('http'):
                    event_url = response.urljoin(event_url)
                
                # Yield event item
                yield self.create_event_item(
                    title=title,
                    date=date,
                    time=None,
                    location=location,
                    url=event_url or response.url,
                    organizer=organizer
                )
        
        # Follow pagination if present
        next_page = response.css('a[rel="next"]::attr(href)').get()
        if next_page:
            self.logger.debug(f"📄 [{self.name}] Following next page: {next_page}")
            yield scrapy.Request(response.urljoin(next_page), callback=self.parse)
