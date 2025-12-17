# Website Scraping - Successfully Working!

## Achievement ✅

Successfully scraped and indexed **5 new events** from Experience Sioux Falls website using Playwright-based browser automation.

### Events Found & Indexed

1. **Rosemaling Demonstration at the Old Courthouse Museum** - Dec 16, 2025
2. **Temptations & Tempranillo** - Dec 16, 2025 (Harvester Kitchen by Bryan)
3. **Italian Christmas Wine Dinner** - Dec 16, 2025 (Parker's Bistro)
4. **Santa Photo Experience** - Dec 16, 2025 (The Empire Mall)
5. **Parades, Picnics, & Pageants: South Dakota Celebrates Exhibit** - Dec 16, 2025 (Old Courthouse Museum)

### System Status

- **Total Events in Elasticsearch**: 40
  - Facebook events: 35 (via headless_scraper.py)
  - Website events: 5 (via playwright_scraper.py)
  
- **Backend API**: Running on port 8000
  - `/api/events/` - Returns paginated event list
  - Full Elasticsearch integration working

### How It Works

#### Script: `playwright_scraper.py`

Uses Playwright (real browser automation) instead of Scrapy for JavaScript-heavy websites:

```bash
python3 scrapy_project/playwright_scraper.py
```

**Process**:
1. Launches Chromium browser
2. Navigates to configured URLs with `wait_until='load'`
3. Waits 3 seconds for JavaScript rendering
4. Extracts events using flexible selectors
5. Normalizes dates to `YYYY-MM-DD` format
6. Indexes to Elasticsearch with deduplication

**Advantages over Scrapy**:
- ✅ Handles complex JavaScript-rendered content
- ✅ Simpler date/location extraction
- ✅ Better error handling for timeouts
- ✅ Built-in deduplication

### Website Configuration

Events configured in `/data/website_urls.txt`:
```
https://www.experiencesiouxfalls.com/events
https://www.sanfordsports.com/events?eventCategory=Spectator+Events&location=Sanford+Sports+Complex&facilityType=Sanford+Pentagon
```

**Note on Sanford Sports**: Found 0 events (likely minimal event data on page or different HTML structure)

### Next Steps for Sanford Sports

1. **Inspect with browser DevTools**:
   - Check actual rendered HTML structure
   - Find event container selectors
   - Create site-specific configuration

2. **Or try different approach**:
   - Check if they have event API endpoints
   - Use Ticketmaster API (they redirect there for event booking)
   - Manual configuration in `data/websites_config.json`

### Running Scripts

**Scrape with Playwright (recommended for complex sites)**:
```bash
python3 scrapy_project/playwright_scraper.py
```

**Scrape with Scrapy (faster, for simpler HTML)**:
```bash
docker run --rm --network host -v $(pwd)/data:/data cityscout_scrapy:latest dynamic
```

**Manual website management**:
```bash
python3 configure_websites.py
```

### Key Files

- **playwright_scraper.py** - Browser-based scraper (WORKING ✓)
- **dynamic_spider.py** - Scrapy spider with CSS pattern matching (for simpler sites)
- **headless_spider.py** - Splash-based rendering (requires Splash container)
- **configurable_spider.py** - JSON config-based per-website selectors
- **run_multiprocess_spiders.py** - Multi-worker orchestrator
- **configure_websites.py** - Interactive website management menu

### Elasticsearch Status

```bash
# Check count
curl http://localhost:9200/events/_count

# Search events
curl http://localhost:9200/events/_search?size=50

# Check mapping
curl http://localhost:9200/events/_mapping
```

### Date Format Requirements

All dates must be `YYYY-MM-DD` format in Elasticsearch. The playwright_scraper automatically converts:
- "Dec 16" → "2025-12-16"
- "December 16, 2025" → "2025-12-16"
- "Mon, Dec 16" → "2025-12-16"

### Troubleshooting

**Events extracted but not indexed**:
- Check date format (must be YYYY-MM-DD)
- Verify title is not empty
- Check Elasticsearch is running on port 9200

**No events found on website**:
- Check if site requires JavaScript rendering
- Try with `wait_until='load'` instead of `'domcontentloaded'`
- Increase wait time: `page.wait_for_timeout(5000)` for 5 seconds
- Inspect HTML with saved playwright_scraper debug output

**Scraper hangs or times out**:
- Increase timeout: `timeout 300 python3 playwright_scraper.py`
- Check network connectivity to target website
- Verify website is responding to requests

