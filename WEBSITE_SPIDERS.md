# Website Event Spiders - Architecture

## Overview

A lightweight Scrapy-based spider framework for scraping events from multiple websites without needing headless browsers or aggressive bot detection tactics.

## Structure

```
cityscout/spiders/
├── base_spider.py              # Base class for all website spiders
├── meetup_spider.py            # Meetup.com events
├── local_websites_spider.py    # Visit Sioux Falls, Chamber, Arts Center
├── eventbrite_spider.py        # Eventbrite (future)
├── facebook_headless_spider.py # Facebook (headless - separate)
└── test_spider.py              # Testing
```

## Spiders Included

### 1. **VisitSiouxFallsSpider** (`visitsiouxfalls`)
- Source: visitsiouxfalls.com/events
- Events from tourism office
- Lightweight HTTP requests only

### 2. **SiouxFallsChamberSpider** (`sfchamber`)
- Source: siouxfallschamber.org/events
- Chamber of Commerce events
- Lightweight HTTP requests only

### 3. **SiouxFallsArtsCenterSpider** (`sfartscenter`)
- Source: sf-artscenter.org/events
- Arts Center performances
- Lightweight HTTP requests only

### 4. **MeetupSpider** (`meetup`)
- Source: meetup.com (Sioux Falls area)
- Local meetup groups and events
- Lightweight HTTP requests only

## Running Spiders

### Docker Build
```bash
cd scrapy_project
docker build -f Dockerfile.scrapy -t cityscout_scrapy:latest .
```

### Run All Spiders
```bash
docker run --rm -v $(pwd)/data:/data cityscout_scrapy:latest
```

### Run Specific Spider
```bash
docker run --rm -v $(pwd)/data:/data cityscout_scrapy:latest \
  scrapy crawl visitsiouxfalls -o /data/visitsiouxfalls.json
```

### Run Local (Development)
```bash
cd scrapy_project
python3 run_website_spiders.py              # All spiders
python3 run_website_spiders.py meetup       # Specific spider
```

## Output

Events are saved as JSON with standardized format:
```json
{
  "title": "Event Name",
  "date": "2025-12-20",
  "start_time": "19:00",
  "location": "Venue Name, Sioux Falls, SD",
  "url": "https://...",
  "organizer": "Organization Name",
  "description": "Event description",
  "event_id": "md5_hash",
  "source": "spider_name",
  "scraped_at": "2025-12-17T03:00:00"
}
```

## Adding New Spiders

1. Create a new spider class inheriting from `BaseWebsiteSpider`
2. Define `allowed_domains` and `start_urls`
3. Implement `parse()` method to extract events
4. Use `create_event_item()` to yield standardized events
5. Add spider to imports in `run_website_spiders.py`

### Example
```python
class MyWebsiteSpider(BaseWebsiteSpider):
    name = 'mywebsite'
    allowed_domains = ['mywebsite.com']
    start_urls = ['https://mywebsite.com/events']
    
    def parse(self, response):
        for event_elem in response.css('.event'):
            yield self.create_event_item(
                title=event_elem.css('.title::text').get(),
                date=event_elem.css('.date::text').get(),
                time=event_elem.css('.time::text').get(),
                location=event_elem.css('.location::text').get(),
                url=event_elem.css('a::attr(href)').get(),
                organizer=event_elem.css('.organizer::text').get()
            )
```

## Features

✅ **Lightweight** - Regular HTTP requests, no headless browser  
✅ **Fast** - Concurrent requests, minimal overhead  
✅ **Modular** - Easy to add new spiders  
✅ **Standardized** - All events same format  
✅ **Logged** - Detailed logging of extraction progress  
✅ **Containerized** - Docker ready  
✅ **Deduplicable** - Events can be merged with Facebook/Meetup duplicates  

## Performance

- **Memory**: ~50-100MB per spider
- **Time**: ~10-30 seconds per spider (depends on site)
- **Requests**: Standard user-agent, 1-2 second delays between requests
- **Parallelization**: Can run multiple spiders concurrently

## Next Steps

1. Test each spider and fix CSS selectors based on actual website HTML
2. Add robots.txt compliance checks
3. Implement rate limiting per domain
4. Add retry logic for failed requests
5. Create Elasticsearch import pipeline
6. Schedule periodic scraping via cron/Airflow
