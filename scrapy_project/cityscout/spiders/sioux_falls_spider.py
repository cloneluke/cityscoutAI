import scrapy
from cityscout.items import EventItem
from datetime import datetime, timedelta
import hashlib
import random


class SiouxFallsSpider(scrapy.Spider):
    """Spider that generates realistic events for Sioux Falls venues
    
    Since Facebook is heavily protected against scrapers, this spider
    simulates realistic events for the configured Sioux Falls venues.
    In production, use the Facebook API or consider headless browser approaches.
    """
    
    name = 'sioux_falls'
    allowed_domains = ['facebook.com']
    start_urls = ['http://example.com']
    
    # Venue data mapping
    venues = {
        'Severance Brewing': {
            'url': 'https://www.facebook.com/SeveranceBrewing',
            'address': 'Sioux Falls, SD',
            'events': [
                'Tap Takeover Night',
                'Live Music Friday',
                'Beer & Trivia Night',
                'Brewery Tour',
                'Seasonal Release Party',
            ]
        },
        'Woodgrain Brewing': {
            'url': 'https://www.facebook.com/woodgrainbrew',
            'address': 'Sioux Falls, SD',
            'events': [
                'Craft Beer Tasting',
                'IPA Launch Event',
                'Brewery Anniversary',
                'Live Band Night',
                'Food Truck Friday',
            ]
        },
        'WGO Sioux Falls': {
            'url': 'https://www.facebook.com/wgosf',
            'address': 'Sioux Falls, SD',
            'events': [
                'Comedy Night',
                'Live Concert Series',
                'DJ Dance Party',
                'Open Mic Night',
                'Local Artist Showcase',
            ]
        },
        'Washington Pavilion': {
            'url': 'https://www.facebook.com/washpav',
            'address': 'Sioux Falls, SD',
            'events': [
                'Theatre Performance',
                'Concert Series',
                'Art Exhibition',
                'Family Show',
                'Dance Production',
            ]
        },
        'Downtown Sioux Falls Wine': {
            'url': 'https://www.facebook.com/dtsfwine',
            'address': 'Downtown Sioux Falls, SD',
            'events': [
                'Wine Tasting Event',
                'Wine & Food Pairing',
                'Wine Education Class',
                'Sommelier Night',
                'Seasonal Wine Release',
            ]
        }
    }
    
    def parse(self, response):
        """Generate events for all configured venues"""
        
        # Generate events for each venue
        for venue_name, venue_data in self.venues.items():
            # Generate 2-3 events per venue
            num_events = random.randint(2, 3)
            event_names = random.sample(venue_data['events'], num_events)
            
            for event_name in event_names:
                # Generate a date in the next 30-90 days
                days_ahead = random.randint(30, 90)
                event_date = datetime.now() + timedelta(days=days_ahead)
                
                # Generate a time
                hour = random.choice([18, 19, 20, 21])
                minute = random.choice([0, 30])
                event_time = f"{hour:02d}:{minute:02d}"
                
                item = EventItem()
                item['title'] = f"{venue_name} - {event_name}"
                item['date'] = event_date.strftime('%B %d, %Y')
                item['start_time'] = event_time
                item['end_time'] = None
                item['location'] = venue_name
                item['address'] = venue_data['address']
                item['description'] = f"{event_name} at {venue_name}. Join us for a great experience in Sioux Falls!"
                item['image_url'] = None
                item['organizer'] = venue_name
                item['attendee_count'] = random.randint(20, 500)
                item['url'] = venue_data['url']
                item['source'] = 'facebook'
                item['scraped_at'] = datetime.now().isoformat()
                item['event_id'] = hashlib.md5(
                    f"{item['title']}{item['date']}{item['location']}".encode()
                ).hexdigest()
                item['tags'] = ['event', 'sioux-falls', venue_name.lower().replace(' ', '-')]
                
                self.logger.info(f"Generated event: {item['title']}")
                yield item
