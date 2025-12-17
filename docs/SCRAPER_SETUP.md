# Running Scrapers

All scrapers now run exclusively in Docker containers with multithreading support.

## Quick Start

### Run all scrapers in parallel:

```bash
./run_all_scrapers.sh
```

This will:
1. Build Docker images for all three scrapers
2. Run them in parallel in separate containers
3. Each scraper indexes results to Elasticsearch automatically

### Run individual scrapers:

```bash
# Website scraper (Playwright)
docker-compose -f config/docker-compose.yml --profile scrapers up scraper_playwright

# Facebook scraper (Headless)
docker-compose -f config/docker-compose.yml --profile scrapers up scraper_facebook

# Dynamic website scraper (Scrapy)
docker-compose -f config/docker-compose.yml --profile scrapers up scraper_dynamic
```

## Scraper Details

### Playwright Scraper (Website Events)
- **Container**: `cityscout_playwright`
- **Source**: `scrapy_project/playwright_scraper.py`
- **Features**:
  - Real browser automation for JavaScript-heavy sites
  - Clicks "Load More" buttons automatically
  - Stops clicking when dates are >2 weeks in future
  - Supports: `data/website_urls.txt`

### Facebook Scraper (Headless)
- **Container**: `cityscout_facebook`
- **Source**: `scrapy_project/facebook_headless_spider.py`
- **Features**:
  - Headless browser for Facebook event pages
  - Handles pagination automatically
  - Extracts event details and images

### Dynamic Scraper (Scrapy)
- **Container**: `cityscout_dynamic`
- **Source**: `scrapy_project/dynamic_spider.py`
- **Features**:
  - Pattern-matching CSS selectors
  - Multithreaded spider execution
  - Best for static HTML sites

## Configuration

URLs for website scraping are read from `data/website_urls.txt`:

```
https://www.experiencesiouxfalls.com/events
https://www.sanfordsports.com/events?eventCategory=Spectator+Events
```

## Output

All scrapers automatically:
1. Extract event data
2. Normalize dates to YYYY-MM-DD format
3. Index to Elasticsearch
4. Deduplicate using MD5 hash of title+date+location
5. Log results to console

## Environment Variables

All scraper containers accept:
- `ELASTICSEARCH_HOST`: Elasticsearch connection (default: `elasticsearch:9200`)
- `MAX_WORKERS`: Thread pool size for multithreading (if applicable)

## Troubleshooting

### Check scraper logs:
```bash
docker logs cityscout_playwright
docker logs cityscout_facebook
docker logs cityscout_dynamic
```

### View indexed events:
```bash
curl http://localhost:9200/events/_search?size=100
```

### Rebuild images:
```bash
docker-compose -f config/docker-compose.yml build --no-cache scraper_playwright scraper_facebook scraper_dynamic
```

## Next Steps

To retrieve indexed events:
```bash
# Via API
curl http://localhost:8000/api/events/?limit=50

# Via web UI
http://localhost:8000/events
```
