# Facebook Spider Changes

## Overview
The Facebook spider has been updated to scan Facebook pages/accounts for events instead of requiring individual event URLs.

## What Changed

### Before
- Required individual event URLs (e.g., `https://www.facebook.com/events/12345/`)
- Users had to manually find and add each event URL
- Limited to already-published events

### Now
- Scans entire Facebook pages/accounts (e.g., `https://www.facebook.com/SeveranceBrewing`)
- Automatically extracts:
  - Events from the page's events section
  - Event-related posts from the timeline
- Intelligently identifies events using keyword matching

## How It Works

### 1. Page Scanning
The spider visits Facebook page URLs provided in `data/facebook_urls.txt`:
```
https://www.facebook.com/SeveranceBrewing
https://www.facebook.com/YourOtherPage
```

### 2. Event Discovery
The spider looks for two types of events:

**Type 1: Explicit Events**
- Searches for links to Facebook events pages
- Follows the links and extracts full event details

**Type 2: Event Posts**
- Scans timeline posts for event-related keywords
- Keywords: event, show, concert, gig, performance, live, ticket, date, time
- Extracts post content as event information

### 3. Data Extraction
For each event found, the spider extracts:
- **Title**: Post text (first 100 chars) or event title
- **Date**: Uses regex to find dates like "Jan 15, 2024" or "1/15/2024"
- **Time**: Uses regex to find times like "7:00 PM" or "19:00"
- **Location**: Uses the page name as default
- **Organizer**: Uses the page name as organizer
- **Description**: Full post text or event description
- **Image**: Post/event image if available
- **URL**: Link to the page or event
- **Source**: Always "facebook"

### 4. Regex Patterns Used

**Date Pattern:**
```
\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?\b
```

Matches:
- "Jan 15"
- "January 15, 2024"
- "Feb 28"
- "December 31, 2024"

**Time Pattern:**
```
\b(?:\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)|\d{1,2}\s*(?:AM|PM|am|pm))\b
```

Matches:
- "7:00 PM"
- "19:00"
- "3 PM"
- "8:30 am"

### 5. Deduplication
- Events are deduplicated using an MD5 hash of title + date + location
- If an event already exists, it gets updated with new information
- Prevents duplicates from multiple posts about the same event

## Usage

### Step 1: Add Your Pages
Edit `data/facebook_urls.txt`:
```
https://www.facebook.com/SeveranceBrewing
https://www.facebook.com/Page2
https://www.facebook.com/Page3
```

### Step 2: Run the Spider
```bash
cd scrapy_project
scrapy crawl facebook
```

### Step 3: Check Results
```bash
# View indexed events
curl http://localhost:9200/events/_count

# Search via API
curl "http://localhost:8000/api/search?q=concert"
```

## Customization

### Change Keywords
Edit the `event_keywords` list in `facebook_spider.py` around line 50:
```python
event_keywords = ['event', 'show', 'concert', 'gig', 'performance', 'live', 'ticket', 'date', 'time']
```

### Adjust Date Format
Modify the `date_pattern` regex in `parse_post_as_event()`:
```python
date_pattern = r'\b(?:Jan|Feb|...[your pattern]\b'
```

### Update CSS Selectors
If Facebook changes its HTML structure, update selectors:
```python
posts = response.css('[data-testid="post"]')  # Update this selector
```

## Advantages

✅ **Automatic Discovery** - No need to manually find each event URL
✅ **Post Analysis** - Captures upcoming events mentioned in posts
✅ **Flexible** - Works with any Facebook page/account
✅ **Scalable** - Can scan multiple pages in one spider run
✅ **Intelligent** - Uses regex patterns to extract structured data from unstructured posts

## Limitations

❌ **HTML Structure** - Facebook changes their HTML frequently, CSS selectors may break
❌ **Private Posts** - Cannot access posts from private accounts without login
❌ **Dynamic Content** - Some content loaded via JavaScript may be missed
❌ **Rate Limiting** - Facebook aggressively rate limits scrapers
❌ **Date Parsing** - Ambiguous dates (like "3/4/24") may be misinterpreted

## Rate Limiting

The spider includes:
- 5-second delays between requests
- User-agent rotation
- Respects robots.txt
- Configured autothrottle for adaptive delays

## Future Improvements

- [ ] Handle private/admin posts if authenticated
- [ ] Support more date formats internationally
- [ ] Extract event attendance/RSVP information
- [ ] Extract ticket information/links
- [ ] Support for event galleries and multiple images
- [ ] Venue information extraction

## Troubleshooting

### Spider finds no events
- Check that page is public
- Check that pages have event posts or events section
- Verify CSS selectors are still valid (Facebook changes frequently)

### Events missing dates
- Post dates must match regex patterns
- Try adding more date formats to the pattern
- Check post content for date mentions

### Spider timing out
- Facebook rate limiting is active
- Increase delays in `settings.py`
- Try running at different times

### No posts being parsed
- Check event keywords list
- Posts may not contain event-related keywords
- Check browser console for actual post HTML structure

## Questions?

See:
- `docs/ARCHITECTURE.md` - System design
- `docs/API.md` - How to query results
- `GETTING_STARTED.md` - Setup instructions
