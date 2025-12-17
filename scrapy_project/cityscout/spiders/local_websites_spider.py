"""Local Sioux Falls event website spiders"""

import scrapy
from cityscout.spiders.base_spider import BaseWebsiteSpider
import re


class VisitSiouxFallsSpider(BaseWebsiteSpider):
    """Spider for visitsiouxfalls.com events"""
    
    name = 'visitsiouxfalls'
    allowed_domains = ['visitsiouxfalls.com']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [
            'https://www.visitsiouxfalls.com/events/',
        ]
        self.logger.info(f"🌐 [{self.name}] Initialized")
    
    def parse(self, response):
        """Parse event listings"""
        event_items = response.css('div[class*="event"]')
        self.logger.info(f"🔍 [{self.name}] Found {len(event_items)} events on {response.url}")
        
        for item in event_items:
            title = item.css('h3::text, h4::text, a::text').get()
            date_text = item.css('span[class*="date"]::text, time::attr(datetime)').get()
            location = item.css('span[class*="location"]::text').get()
            event_url = item.css('a::attr(href)').get()
            
            if title:
                title = title.strip()
                date = self.extract_date(date_text) if date_text else None
                location = location.strip() if location else "Sioux Falls, SD"
                
                if event_url and not event_url.startswith('http'):
                    event_url = response.urljoin(event_url)
                
                yield self.create_event_item(
                    title=title,
                    date=date,
                    time=None,
                    location=location,
                    url=event_url or response.url,
                    organizer="Visit Sioux Falls"
                )
        
        # Follow pagination
        next_page = response.css('a[rel="next"], a.next::attr(href)').get()
        if next_page:
            yield scrapy.Request(response.urljoin(next_page), callback=self.parse)


class SiouxFallsChamberSpider(BaseWebsiteSpider):
    """Spider for Sioux Falls Chamber of Commerce events"""
    
    name = 'sfchamber'
    allowed_domains = ['siouxfallschamber.org']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [
            'https://www.siouxfallschamber.org/events/',
        ]
        self.logger.info(f"🌐 [{self.name}] Initialized")
    
    def parse(self, response):
        """Parse event listings"""
        event_items = response.css('div[class*="event"], article[class*="event"]')
        self.logger.info(f"🔍 [{self.name}] Found {len(event_items)} events on {response.url}")
        
        for item in event_items:
            title = item.css('h3::text, h4::text, a::text').get()
            date_text = item.css('span[class*="date"]::text, time::text, .date::text').get()
            location = item.css('span[class*="location"]::text, .location::text').get()
            event_url = item.css('a::attr(href)').get()
            
            if title:
                title = title.strip()
                date = self.extract_date(date_text) if date_text else None
                location = location.strip() if location else "Sioux Falls, SD"
                
                if event_url and not event_url.startswith('http'):
                    event_url = response.urljoin(event_url)
                
                yield self.create_event_item(
                    title=title,
                    date=date,
                    time=None,
                    location=location,
                    url=event_url or response.url,
                    organizer="Sioux Falls Chamber of Commerce"
                )
        
        # Follow pagination
        next_page = response.css('a[rel="next"], a.next::attr(href)').get()
        if next_page:
            yield scrapy.Request(response.urljoin(next_page), callback=self.parse)


class SiouxFallsArtsCenterSpider(BaseWebsiteSpider):
    """Spider for Sioux Falls Arts Center events"""
    
    name = 'sfartscenter'
    allowed_domains = ['sf-artscenter.org']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [
            'https://www.sf-artscenter.org/events/',
        ]
        self.logger.info(f"🌐 [{self.name}] Initialized")
    
    def parse(self, response):
        """Parse event listings"""
        event_items = response.css('div[class*="event"], div[class*="show"]')
        self.logger.info(f"🔍 [{self.name}] Found {len(event_items)} events on {response.url}")
        
        for item in event_items:
            title = item.css('h3::text, h4::text, a::text').get()
            date_text = item.css('span[class*="date"]::text, time::text, .date::text').get()
            location = item.css('span[class*="location"]::text, .location::text').get()
            event_url = item.css('a::attr(href)').get()
            
            if title:
                title = title.strip()
                date = self.extract_date(date_text) if date_text else None
                location = location.strip() if location else "Sioux Falls, SD"
                
                if event_url and not event_url.startswith('http'):
                    event_url = response.urljoin(event_url)
                
                yield self.create_event_item(
                    title=title,
                    date=date,
                    time=None,
                    location=location,
                    url=event_url or response.url,
                    organizer="Sioux Falls Arts Center"
                )
