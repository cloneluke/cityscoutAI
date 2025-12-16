# Facebook Post Event Extraction Guide

## Overview

The CityscoutAI system can extract event information from Facebook posts in multiple ways. This guide explains how the system works, its limitations, and how to work around them.

## How It Works

### 1. **Text Extraction from Post Metadata** ✅ (WORKING)

When you add a Facebook post URL to `data/facebook_post_urls.txt`, the spider automatically:

1. **Fetches the post** from Facebook
2. **Extracts og:description meta tag** from the post (structured text)
3. **Analyzes text** using Ollama's Mistral model to identify event details
4. **Creates full events** with: title, date, time, location, price, description
5. **Enriches with venue data** from the venue mapping file

**Success Example:** "Join us for a Holiday tasting at Stogeez December 10th 7pm. 5 tap beers or 5 cocktails and a cigar for $35!"
- ✅ Extracted: Holiday tasting at Stogeez, Dec 10th, 7pm, $35
- ✅ Stored in Elasticsearch with all details
- ✅ Source tagged as "facebook_post"

### 2. **Image Analysis (Disabled)** ⚠️ 

Image-based event extraction is **currently disabled** because:
- Facebook CDN returns HTTP 403 "Bad URL hash" for signed image URLs
- URLs are time-limited and require browser context
- Direct image downloads fail reliably across all methods

Code remains available for future use if this limitation is resolved.

### 3. **Venue-Based Fallback** ✅

If text extraction finds no event (no og:description), the system:

1. **Detects the post source venue** (e.g., Bin 201)
2. **Looks up venue information** from `facebook_venues.txt`
3. **Creates a minimal event** with:
   - Venue name and address
   - Link to the original Facebook post
   - Encourages checking post content directly

### 3. **Semi-Automated Image Extraction** (For You) 📋

For posts where automatic extraction doesn't work:

```bash
# Option A: Interactive helper
python3 extract_post_images.py

# Option B: Check current queue
python3 extract_post_images.py --queue

# Option C: Batch add from file
python3 extract_post_images.py --batch my_urls.txt
```

## Technical Details

### How Text Extraction Works ✅

The system uses **Facebook's open graph metadata**:

1. **og:description meta tag** - Contains event summary posted by the venue
2. **Mistral model analysis** - Ollama parses the text for event details
3. **Confidence scoring** - High/medium confidence extractions create full events
4. **Venue enrichment** - Adds address/details from venue database

Example Facebook post text:
```
"Join us for a Holiday tasting at Stogeez December 10th 7pm. 
5 tap beers or 5 cocktails and a cigar for $35!"
```

Extracted to:
```json
{
  "title": "Holiday tasting with 5 tap beers or 5 cocktails and a cigar at Stogeez",
  "date": "Dec 10th",
  "time": "7pm",
  "location": "Stogeez",
  "ticket_price": "$35",
  "description": "Holiday tasting featuring 5 tap beers or cocktails and a cigar",
  "confidence": "high"
}
```

### Why Image Extraction Is Not Used ⚠️

Facebook CDN images use **signed, temporary URLs** that:
- Expire after a few minutes
- Require specific browser context to access  
- Return HTTP 403 "Bad URL hash" when accessed from bots/scripts
- Cannot be reliably downloaded programmatically

The text extraction approach is:
- ✅ More reliable (no CDN signing issues)
- ✅ Faster (no image downloads)
- ✅ Works for most event posts (venues post text descriptions)
- ✅ No image processing overhead (no Ollama vision model needed)

### Code Details

**Text Extraction Method:** `extract_event_from_post_text()` (facebook_spider.py line 777)
- Calls Ollama's Mistral model for text analysis
- Works independently (no image_service required)
- Falls back to venue-based events if no og:description found
- Logs all extractions with confidence levels

**Image Processing:** Disabled in `parse_post()` method (lines 713-728)
- Code remains commented with detailed explanation
- Available for future use if Facebook CDN access is solved
- Helper scripts (`extract_post_images.py`) remain for manual extraction

## File Structure

```
data/
├── facebook_post_urls.txt      # Posts to process (format: page | url | caption)
├── facebook_photo_urls.txt     # Pre-extracted photo URLs
└── facebook_venues.txt         # Venue info (name, address, city, state)

extract_post_images.py          # Interactive image extraction helper
find_event_photos.py            # Photo discovery helper
```

## Example Workflows

### Scenario 1: Text Extraction Works ✅ (MOST COMMON)

```
1. Add post URL to facebook_post_urls.txt
   https://www.facebook.com/dtsfwine | https://www.facebook.com/dtsfwine/posts/pfbid0T... |
   
2. Run spider
   cd scrapy_project && python3 -m scrapy crawl facebook
   
3. Spider extracts og:description metadata
   "Holiday tasting at Stogeez December 10th 7pm. $35..."
   
4. Ollama analyzes text and extracts:
   - Title: "Holiday tasting with 5 tap beers... at Stogeez"
   - Date: "Dec 10th"
   - Time: "7pm"
   - Location: "Stogeez" (or venue from database)
   - Price: "$35"
   
5. Event stored in Elasticsearch with all details ✅
   Source: "facebook_post"
   Tags: ["event", "facebook-post", "text-extracted"]
```

### Scenario 2: No og:description, Use Venue Fallback

```
1. Add post URL to facebook_post_urls.txt
   
2. Run spider
   python3 -m scrapy crawl facebook
   
3. No og:description found → uses fallback:
   - Creates event with venue name and address
   - Includes link to original Facebook post
   - Tags as ["event", "facebook-post"]
   - User can manually check post for details
   - Example:
     Title: "Event at Bin 201"
     Address: "201 E. 11th Street, Sioux Falls, SD"
     URL: links to the Facebook post
   
4. User can manually add details to Elasticsearch if needed
```

## Adding Posts

### Adding a Single Post

Edit `data/facebook_post_urls.txt` and add a line:

```
https://www.facebook.com/page_name | https://www.facebook.com/page_name/posts/post_id | optional_notes
```

Example:
```
https://www.facebook.com/dtsfwine | https://www.facebook.com/dtsfwine/posts/pfbid02823zoqpRszif... | Holiday tasting event
```

Then run the spider:
```bash
cd scrapy_project
python3 -m scrapy crawl facebook
```

## Success Indicators

### Event Successfully Created From Post Text ✅

```json
{
  "title": "Event Title",
  "date": "2025-12-20",
  "location": "Bin 201",
  "address": "201 E. 11th Street, Sioux Falls, SD, United States",
  "source": "facebook_post",
  "tags": ["event", "facebook-post"]
}
```

### Fallback Event (Needs Manual Review) 📋

```json
{
  "title": "Event at Bin 201",
  "date": "Check Facebook post",
  "location": "Bin 201",
  "source": "facebook_post",
  "tags": ["event", "facebook-post", "needs-review", "image-pending"],
  "description": "To extract details: Open [post URL] in your browser, save the event image..."
}
```

## Best Practices

1. **Text Extraction is Primary Method** ✅
   - Most event posts have og:description metadata
   - Ollama text analysis is reliable and fast
   - No image processing overhead
   - Recommended for all posts

2. **Venue Mapping for Location Enrichment**
   - System automatically enriches with venue info from `facebook_venues.txt`
   - Format: `facebook_url | venue_name | address | city | state`
   - Improves location accuracy when venue can be inferred from post page

3. **Monitor Extraction Quality**
   - Log entries show confidence levels (high/medium/low)
   - Low confidence extractions are still created but tagged appropriately
   - Fallback events are created when no og:description found

4. **Multiple Attempts Safe**
   - Posts are de-duplicated by event_id
   - Re-running spider on same posts won't create duplicates
   - Can safely re-add posts to queue

## Limitations & Architecture

### Current Design Choices
- ✅ **Text extraction from og:description** - Most reliable, no CDN issues
- ✅ **Mistral model for text analysis** - Faster than vision models
- ✅ **Venue-based enrichment** - Improves location data quality
- ❌ **Image processing** - Disabled due to Facebook CDN security restrictions

### Why Not Image Processing?
- Facebook CDN uses signed, time-limited URLs
- HTTP 403 "Bad URL hash" errors for non-browser clients
- No way to refresh signatures programmatically
- Text extraction avoids this entirely
- ⚠️ Post text extraction limited to visible HTML

### Potential Solutions (Not Implemented)
1. **Selenium/Playwright Integration**
   - Would allow full JavaScript rendering
   - Could capture dynamic content
   - More resource-intensive

2. **Facebook API Access**
   - Official API for event extraction
   - Requires app approval
   - Better reliability

3. **OCR Enhancement**
   - Combine vision model with traditional OCR
   - Better extraction from event posters
   - Could extract handwritten text

## Troubleshooting

### Potential Future Enhancements
1. **Selenium/Playwright Integration** - Would allow JavaScript rendering and dynamic content
2. **Facebook API Access** - Official API provides structured event data (requires approval)
3. **Multi-language Support** - Currently works best with English text
4. **Confidence Tuning** - Fine-tune Mistral prompts for specific venue types

## Troubleshooting

### Issue: "No event detected in text (has_event=False)"
**Solution**: Post text doesn't contain event details. Check that:
1. Post has og:description metadata
2. Description mentions dates/times/locations
3. Fallback event was created instead - user can manually check post

### Issue: "Low confidence event extraction"
**Solution**: Ollama wasn't confident in the extraction. Examples:
- Text is ambiguous or poorly formatted
- No clear dates/times mentioned
- Multiple conflicting event details
Check the extracted data - it may still be useful

### Issue: "Analyzing post text... No event detected"
**Diagnosis**: Either:
1. Post has no og:description (social media share, not event post)
2. og:description doesn't contain event-like information
3. Ollama determined it's not an event

**Solution**: Fallback event created with venue info. User can manually verify post content.

### Issue: Events not appearing in web interface
**Solution**: 
1. Check spider logs: `grep -i error facebook_spider.log`
2. Verify Elasticsearch is running: `curl http://localhost:9200`
3. Check events in Elasticsearch: `curl http://localhost:9200/events/_search`
4. Verify spider pipeline: `scrapy_project/cityscout/pipelines.py`

## Testing

### Test Text Extraction Directly
```bash
# Test Ollama text analysis
python3 << 'EOF'
import requests
import json

prompt = """Extract event details from: "Holiday tasting at Stogeez Dec 10 7pm. $35"
Return JSON with title, date, time, location, price."""

response = requests.post(
    "http://localhost:11434/api/generate",
    json={'model': 'mistral', 'prompt': prompt, 'stream': False},
    timeout=30
)

if response.status_code == 200:
    result = response.json()
    print("Ollama Response:", result['response'])
else:
    print(f"Error: {response.status_code}")
EOF
```

### Test Spider
```bash
cd scrapy_project
python3 -m scrapy crawl facebook -a log_level=DEBUG
```

### View Events
```bash
# Via API
curl http://localhost:8000/api/events/?limit=10

# Via Elasticsearch
curl http://localhost:9200/events/_search?pretty

# Via Web Interface
open http://localhost:8000/events
```

## See Also

- `FACEBOOK_PHOTOS.md` - Photo discovery workflow
- `IMAGE_PROCESSING.md` - Vision model details
- `API.md` - REST API documentation
- `docs/SETUP.md` - Initial setup guide
