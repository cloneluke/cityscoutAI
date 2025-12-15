# Facebook Event Photo Extraction Workflow

## Overview

Since Facebook heavily blocks web scrapers, cityscoutAI uses a **semi-automated workflow** to extract events from Facebook photos:

1. **Manual Discovery**: You find event photos on Facebook pages (posts, stories, etc.)
2. **URL Extraction**: Copy the image link from your browser
3. **Automated Processing**: Spider analyzes images and creates events
4. **Data Enrichment**: Venue information auto-fills location, address, organizer

## Quick Start

### Step 1: Use the Photo Finder Helper

```bash
python3 find_event_photos.py
```

This interactive script helps you:
- ✅ Select a venue (Bin 201, Severance Brewing, etc.)
- ✅ Paste the Facebook photo URL
- ✅ Get the direct image URL
- ✅ Add optional caption/description
- ✅ Queue photos for processing

### Step 2: Run the Spider

```bash
cd /home/luke/git-repos/cityscoutAI/scrapy_project
python3 -m scrapy crawl facebook
```

The spider will:
- Load all queued photos from `data/facebook_photo_urls.txt`
- Download and analyze each image
- Extract event details (title, date, time, location, performers, prices)
- Use venue mapping to add proper addresses
- Create searchable events in Elasticsearch
- Mark as `facebook-photo` source for tracking

## How to Find Event Photos on Facebook

### On Desktop

1. Go to the venue's Facebook page
   - Example: https://www.facebook.com/dtsfwine (Bin 201)

2. Scroll through the **Posts** timeline
   - Look for posts with photos of event posters, flyers, etc.
   - Events often get promoted with visual graphics

3. Click on the post to open it
   - Hover over or click the photo
   - Right-click → **"Copy image link"**
   - Paste this into the photo finder

### On Mobile

1. Open the venue's Facebook page
2. Find the event photo post
3. Tap the photo to open full view
4. Tap the three dots (...) → Share → Copy Link
5. Or use your browser's "Inspect" to find image URL

## Example Workflow

```bash
# Step 1: Open photo finder
python3 find_event_photos.py

# Step 2: Add a photo
# - Select venue: https://www.facebook.com/dtsfwine
# - Photo URL: https://www.facebook.com/photo.php?fbid=1449282227200521...
# - Image URL: https://example.com/image.jpg
# - Caption: Wine tasting event

# Step 3: Verify queue
# Option 2 to see queued photos

# Step 4: Process
cd scrapy_project
python3 -m scrapy crawl facebook -L INFO

# Step 5: Check results
curl http://localhost:8000/api/events/?source=facebook_photo
```

## Supported Venues

Currently configured venues (add more in `data/facebook_venues.txt`):

- **Bin 201** (https://www.facebook.com/dtsfwine)
  - 201 E. 11th Street, Sioux Falls, SD
  
- **Severance Brewing** (https://www.facebook.com/SeveranceBrewing)
  - Sioux Falls, SD
  
- **Woodgrain Brewing** (https://www.facebook.com/woodgrainbrew)
  - Sioux Falls, SD
  
- **WGO Sioux Falls** (https://www.facebook.com/wgosf)
  - Sioux Falls, SD
  
- **Washington Pavilion** (https://www.facebook.com/washpav)
  - Sioux Falls, SD

## Adding New Venues

Edit `data/facebook_venues.txt`:

```
https://www.facebook.com/page_name | Venue Name | Full Address | City | State | Country
```

Example:
```
https://www.facebook.com/mybrewery | My Brewery | 123 Main St, Sioux Falls, SD | Sioux Falls | SD | United States
```

Then use `find_event_photos.py` and it will show up as an option.

## Extracted Event Fields

When photos are processed, the system extracts:

- ✅ **Title**: Event name/heading
- ✅ **Date**: Event date (if visible)
- ✅ **Time**: Start time (if visible)
- ✅ **Location**: Venue name
- ✅ **Address**: Full venue address
- ✅ **Organizer**: Venue that posted it
- ✅ **Performers**: Artists/bands (if visible)
- ✅ **Ticket Price**: Cost (if visible)
- ✅ **Description**: Caption + image description
- ✅ **Image URL**: Direct link to poster image

## Limitations & Workarounds

### Facebook Blocking

**Issue**: Spider cannot directly visit Facebook pages
**Solution**: Use manual URL collection via photo finder

### Dynamic Content

**Issue**: Facebook loads content dynamically with JavaScript
**Solution**: We extract from image content instead, which works for posters

### Bot Detection

**Issue**: Facebook detects and blocks scrapers
**Solution**: We don't try to scrape Facebook directly; we process images you provide

## API Integration

Once photos are processed, query them:

```bash
# Get all events from Facebook photos
curl http://localhost:8000/api/events/?source=facebook_photo

# Search for specific event
curl "http://localhost:8000/api/search/?q=wine+tasting"

# Get by venue
curl "http://localhost:8000/api/events/?location=Bin+201"
```

## Future Improvements

To make this fully automatic, we could:

1. **Use Facebook Graph API** (requires app approval)
   - Official access to page posts
   - Automatic photo extraction
   - No anti-bot issues

2. **Add Headless Browser** (Playwright/Puppeteer)
   - JavaScript rendering for dynamic content
   - Automatic post crawling
   - Requires more resources

3. **Combine with Manual + Automated**
   - Facebook API for official events
   - Photo spider for community posts
   - Hybrid approach

## Troubleshooting

### Photo not processing

1. Check if image URL is correct
   - Visit URL in browser, should show the image
   
2. Check if it's a valid event image
   - Make sure it's actually an event poster/flyer
   - Vision AI might skip non-event images

3. Check spider logs
   ```bash
   python3 -m scrapy crawl facebook -L DEBUG
   ```

### Venue not found

1. Add to `data/facebook_venues.txt`
2. Make sure Facebook URL is exact
3. Restart photo finder to reload

### Image extracted wrong data

1. Check if vision model has good image quality
2. Try adding a caption to help the model
3. Review spider logs for confidence scores

## Files

- `find_event_photos.py` - Interactive helper script
- `data/facebook_photo_urls.txt` - Queue of photos to process
- `data/facebook_venues.txt` - Venue information mapping
- `scrapy_project/cityscout/spiders/facebook_spider.py` - Main spider with photo support
