import scrapy


class EventItem(scrapy.Item):
    """Event item for Scrapy pipeline"""
    title = scrapy.Field()
    date = scrapy.Field()
    start_time = scrapy.Field()
    end_time = scrapy.Field()
    location = scrapy.Field()
    address = scrapy.Field()
    description = scrapy.Field()
    image_url = scrapy.Field()
    organizer = scrapy.Field()
    attendee_count = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()  # 'facebook', 'eventbrite', 'google'
    scraped_at = scrapy.Field()
    event_id = scrapy.Field()  # For deduplication
    tags = scrapy.Field()  # AI-generated tags
