# Website Scraping Status & Next Steps

## Current Achievement
✅ **Spider Framework Complete** - Built a modular Scrapy-based system with:
- Dynamic spider using CSS pattern matching (20+ selectors)
- Headless spider with Splash JavaScript rendering
- Configurable spider with per-website JSON config
- Multiprocessing orchestrator (2-4 workers)
- Deduplication via fuzzy title matching + Elasticsearch

✅ **Docker Support** - Fixed ENTRYPOINT to pass spider_type parameter
✅ **Facebook Scraper** - Still working with 35 unique events indexed
✅ **Configuration System** - Created `configure_websites.py` interactive menu

## Issue with Target Websites
Both websites (Experience Sioux Falls and Sanford Sports) use:
1. **Highly Dynamic JavaScript** - Events load after page render
2. **No Pre-rendered HTML** - Initial HTML has no event data
3. **Complex React/Vue frameworks** - Not simple static HTML scraping
4. **Connection Issues** - Experience Sioux Falls times out frequently

## Solutions & Recommendations

### Option A: Use Simpler Websites (RECOMMENDED)
Many event websites are static HTML or have API endpoints:
- Local meetup groups
- Chamber of commerce sites  
- Convention bureau listings
- Town/city event calendars
- Sports league websites with simpler structure

**Action**: Update `data/website_urls.txt` with easier-to-scrape websites

### Option B: Use Website-Specific Scrapers
Create custom scrapers for each platform:
```python
# Example for Sanford Sports - use their Ticketmaster integration
ticketmaster_api = "https://www.ticketmaster.com/api/events?venue=50533"

# Example for Experience SF - check for hidden API endpoints
```

### Option C: Browser Automation for These Specific Sites
Use Playwright directly (already created `playwright_scraper.py`):
```bash
# Test with longer timeout and better selectors
python3 scrapy_project/playwright_scraper.py
```

Requires:
- Debugging what selectors actually contain event data
- Longer page load times (30+ seconds)
- More robust error handling

### Option D: Manual Data Entry
For now, manually add known events to Elasticsearch:
```bash
curl -X POST http://localhost:9200/events/_doc \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Event Name",
    "date": "2025-12-20",
    "location": "Venue",
    "website": "Source",
    "url": "https://...",
    "timestamp": "2025-12-17T03:45:00Z"
  }'
```

## What's Working

### Current System Status
- ✅ FastAPI backend serving 35 Facebook events on port 8000
- ✅ Elasticsearch indexed and searchable
- ✅ Dynamic spider framework (works on simpler sites)
- ✅ Docker containerization for easy deployment
- ✅ Deduplication to prevent duplicate events
- ✅ Interactive website management tool

### How to Use Current Setup

**1. Add simpler websites:**
```bash
python3 configure_websites.py
```
Menu options to:
- Add website URLs
- Configure custom CSS selectors per website
- Enable/disable websites
- Run spiders

**2. Run dynamic spider:**
```bash
# From container
docker run --rm --network host -v $(pwd)/data:/data cityscout_scrapy:latest dynamic

# Or directly
python3 scrapy_project/run_multiprocess_spiders.py dynamic
```

**3. Run headless spider (for JavaScript-heavy sites):**
```bash
# Requires Splash running
docker run -d --name splash -p 8050:8050 scrapinghub/splash
docker run --rm --network host -v $(pwd)/data:/data cityscout_scrapy:latest headless
```

**4. View scraped events:**
```bash
curl http://localhost:9200/events/_search?size=100 | python3 -m json.tool
```

## Next Steps (Prioritized)

1. **Replace target URLs with working websites** (5 minutes)
   - Find 3-5 websites with simpler event listings
   - Update `data/website_urls.txt`
   - Test spider on them

2. **Debug Sanford Sports/Experience SF if needed** (30+ minutes)
   - Use browser DevTools to inspect actual HTML structure
   - Identify rendered event selectors
   - Create website-specific config in `data/websites_config.json`

3. **Test and refine** (10 minutes)
   - Run spider on working websites
   - Verify events appear in Elasticsearch
   - Monitor web UI updates

## Code Files Created

- `scrapy_project/dynamic_spider.py` - Generic pattern-matching spider
- `scrapy_project/headless_spider.py` - Splash-based JavaScript rendering
- `scrapy_project/configurable_spider.py` - JSON config-based spider
- `scrapy_project/playwright_scraper.py` - Direct Playwright approach
- `scrapy_project/run_multiprocess_spiders.py` - Multi-worker orchestrator
- `configure_websites.py` - Interactive management tool
- `Dockerfile.scrapy` - Lightweight container

## Testing Success Criteria

```bash
# Should show more than 35 events
curl -s http://localhost:9200/events/_count | jq .count

# Web UI should display total
# Backend /api/events should return all events
```
