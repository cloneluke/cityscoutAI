# Facebook Post Event Extraction Guide

## Overview

The CityscoutAI system can extract event information from Facebook posts in multiple ways. This guide explains how the system works, its limitations, and how to work around them.

## How It Works

### 1. **Automatic Post Processing** ✅

When you add a Facebook post URL to `data/facebook_post_urls.txt`, the spider automatically:

1. **Fetches the post** from Facebook
2. **Extracts images** embedded in the post (via multiple methods)
3. **Analyzes images** using Ollama's Llava vision model
4. **Creates events** with extracted information (title, date, location, etc.)
5. **Enriches with venue data** from the venue mapping file

### 2. **Venue-Based Fallback** ✅

If image analysis fails (e.g., Facebook CDN blocking), the system:

1. **Detects the post source venue** (e.g., Bin 201)
2. **Looks up venue information** from `facebook_venues.txt`
3. **Creates a placeholder event** with:
   - Venue name and address
   - Link to the original Facebook post
   - Helpful guidance for manual image extraction

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

### Why Facebook Images Are Tricky

Facebook uses **signed, temporary image URLs** that:
- Expire after a few minutes
- Require specific browser context to access
- Return HTTP 403 "Bad URL hash" when accessed from non-browser clients
- Cannot be reliably scraped programmatically

Example:
```
https://scontent-ord5-2.xx.fbcdn.net/v/t39.30808-6/594074777_...jpg
↓
Status: 403 Forbidden
Response: "Bad URL hash"
```

### Workarounds Implemented

1. **Multiple Image Source Detection** (Lines 618-642)
   - og:image meta tag (most reliable)
   - img tag src attributes
   - picture element sources
   - srcset parsing

2. **Enhanced Image Downloading** (image_service.py)
   - Proper User-Agent headers
   - Session management
   - Retry logic with delays
   - Special handling for CDN URLs

3. **Graceful Degradation** (parse_post method)
   - If images can't be downloaded → use fallback event
   - Fallback includes direct Facebook link
   - User can manually extract and retry

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

### Scenario 1: Automatic Extraction Works ✅

```
1. Add post URL to facebook_post_urls.txt
   https://www.facebook.com/dtsfwine | https://www.facebook.com/dtsfwine/posts/pfbid0T... |
   
2. Run spider
   python3 -m scrapy crawl facebook
   
3. Event with full details automatically created ✅
```

### Scenario 2: Automatic Extraction Fails, Use Fallback

```
1. Add post URL to facebook_post_urls.txt
   
2. Run spider
   python3 -m scrapy crawl facebook
   
3. Spider creates fallback event:
   - Title: "Event at Bin 201"
   - Address: "201 E. 11th Street, Sioux Falls, SD"
   - Description: "Links to post and guides manual extraction"
   
4. Open the Facebook post in your browser
   
5. Manually extract image using:
   python3 extract_post_images.py
   
6. Run spider again to process the extracted image ✅
```

### Scenario 3: Use find_event_photos.py Discovery Tool

```
1. Run the discovery helper
   python3 find_event_photos.py
   
2. Menu guides you to:
   - Browse Facebook page
   - Find event photos
   - Extract image URLs
   - Queue them automatically
   
3. Run spider to process all queued photos
   python3 -m scrapy crawl facebook
```

## Success Indicators

### Event Successfully Created From Post ✅

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

1. **For Posts with Clear Event Posters**
   - Use `extract_post_images.py` to manually extract the image
   - Paste it in `facebook_photo_urls.txt`
   - Re-run spider for full analysis

2. **For Posts with Event Details in Caption**
   - Spider extracts caption text
   - Uses Ollama to parse event info
   - Creates event with extracted details

3. **Keep Venue Mapping Updated**
   - Add new venues to `facebook_venues.txt`
   - Format: `facebook_url | venue_name | address | city | state | country`
   - Improves fallback event quality

4. **Monitor image-pending Events**
   - Search for `image-pending` tag
   - These are good candidates for manual image extraction
   - Re-run spider after adding images

## Limitations & Future Improvements

### Current Limitations
- ❌ Cannot directly download Facebook CDN images (security restriction)
- ❌ Cannot execute JavaScript to render post content
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

### Issue: "Failed to download image: 403"
**Solution**: This is expected for Facebook CDN URLs. Use the fallback event and manually extract the image.

### Issue: "Low confidence event extraction"
**Solution**: The vision model wasn't confident. Check the image quality or add venue information.

### Issue: "No post text found"
**Solution**: Post might use JavaScript rendering. Use manual image extraction instead.

### Issue: Events not appearing in web interface
**Solution**: 
1. Check spider logs for errors
2. Verify Elasticsearch is running: `curl http://localhost:9200`
3. Check events in Elasticsearch: `curl http://localhost:9200/events/_search`

## Testing

### Test Image Extraction
```bash
# Manually test image download
python3 << 'EOF'
from backend.app.services.image_service import ImageService
service = ImageService()
image_data = service.download_image("https://example.com/image.jpg")
print(f"Downloaded: {len(image_data)} bytes" if image_data else "Failed")
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
