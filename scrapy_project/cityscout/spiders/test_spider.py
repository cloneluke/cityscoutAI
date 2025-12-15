import scrapy
from cityscout.items import EventItem
from datetime import datetime, timedelta
import hashlib
import random


class TestSpider(scrapy.Spider):
    """Test spider that generates sample events for demonstration"""
    
    name = 'test'
    allowed_domains = ['example.com']
    start_urls = ['http://example.com']
    
    # Sample events to generate
    sample_events = [
        {
            'title': 'Severance Brewing Tap Takeover Night',
            'date': 'December 20, 2024',
            'time': '6:00 PM',
            'location': 'Severance Brewing',
            'address': 'Sioux Falls, SD',
            'description': 'Join us for a special tap takeover featuring craft breweries from around the region. Free tastings and live music!',
            'organizer': 'Severance Brewing',
        },
        {
            'title': 'Winter Beer Festival',
            'date': 'December 28, 2024',
            'time': '4:00 PM',
            'location': 'Falls Park',
            'address': 'Sioux Falls, SD',
            'description': 'Annual winter beer festival featuring 30+ breweries. Food trucks, live bands, and winter activities.',
            'organizer': 'Sioux Falls Events',
        },
        {
            'title': 'New Year Eve Celebration',
            'date': 'December 31, 2024',
            'time': '9:00 PM',
            'location': 'Downtown Sioux Falls',
            'address': 'Main Street, Sioux Falls, SD',
            'description': 'Ring in 2025 with fireworks, live music, and celebrations across downtown.',
            'organizer': 'City of Sioux Falls',
        },
        {
            'title': 'Winter Concert Series - Local Rock Band',
            'date': 'January 10, 2025',
            'time': '7:30 PM',
            'location': 'Orpheum Theatre',
            'address': 'Sioux Falls, SD',
            'description': 'Local favorite rock band performs original songs and covers.',
            'organizer': 'Orpheum Theatre',
        },
        {
            'title': 'Craft Brewery Showcase',
            'date': 'January 17, 2025',
            'time': '5:00 PM',
            'location': 'Convention Center',
            'address': 'Sioux Falls, SD',
            'description': 'Meet local brewers, sample new beers, and learn about craft brewing.',
            'organizer': 'SD Brewers Guild',
        },
    ]
    
    def parse(self, response):
        """Generate sample events"""
        
        self.logger.info("Test spider: Generating sample events")
        
        for idx, event_data in enumerate(self.sample_events):
            item = EventItem()
            
            item['title'] = event_data['title']
            item['date'] = event_data['date']
            item['start_time'] = event_data['time']
            item['end_time'] = None
            item['location'] = event_data['location']
            item['address'] = event_data['address']
            item['description'] = event_data['description']
            item['image_url'] = None
            item['organizer'] = event_data['organizer']
            item['attendee_count'] = random.randint(50, 500)
            item['url'] = f"https://example.com/event/{idx}"
            item['source'] = 'facebook'
            item['scraped_at'] = datetime.now().isoformat()
            item['event_id'] = hashlib.md5(f"{item['title']}{item['date']}{item['location']}".encode()).hexdigest()
            item['tags'] = ['event', 'sioux-falls', 'community']
            
            self.logger.info(f"Generated event: {item['title']}")
            yield item
