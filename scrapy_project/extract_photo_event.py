"""
Helper script to extract events from Facebook photo URLs

Usage:
    python3 extract_photo_event.py "https://www.facebook.com/photo.php?fbid=..."
"""

import sys
import requests
import json
from datetime import datetime
import hashlib

# Add backend to path
sys.path.insert(0, '/home/luke/git-repos/cityscoutAI/backend')

from app.services.image_service import ImageService
from elasticsearch import Elasticsearch

def extract_event_from_facebook_photo(photo_url, image_url=None, caption=None):
    """
    Extract event information from a Facebook photo.
    
    Args:
        photo_url: The Facebook photo URL
        image_url: Direct URL to the image (if known)
        caption: Photo caption text (if extracted)
    
    Returns:
        Event dict or None
    """
    
    image_service = ImageService()
    
    # If we have an image URL, try to extract event info from it
    if image_url:
        # Image processing is DISABLED
        # Reason: Facebook CDN URLs are signed, time-limited, and return HTTP 403
        # print(f"Processing image: {image_url[:60]}...")
        
        # Check if likely event image
        if not image_service.is_likely_event_image(image_url):
            print("Image does not appear to be event-related")
            return None
        
        # Extract event info
        event_info = image_service.extract_event_info_from_image(image_url)
        
        if event_info and event_info.get('confidence') in ['high', 'medium']:
            print(f"✅ Extracted event from image: {event_info}")
            
            event = {
                'title': event_info.get('title', 'Event from Photo'),
                'date': event_info.get('date', 'TBA'),
                'start_time': event_info.get('time', ''),
                'end_time': None,
                'location': event_info.get('location', 'TBA'),
                'address': event_info.get('address', event_info.get('location', 'TBA')),
                'description': event_info.get('description', ''),
                'image_url': image_url,
                'organizer': (event_info.get('performers', ['Unknown'])[0] 
                             if event_info.get('performers') else 'Unknown'),
                'attendee_count': 0,
                'url': photo_url,
                'source': 'facebook_photo',
                'scraped_at': datetime.now().isoformat(),
                'tags': ['event', 'facebook-photo', 'image-extracted']
            }
            
            # Generate event ID
            event_hash = f"{event['title']}{event['date']}{event['location']}"
            event['event_id'] = hashlib.md5(event_hash.encode()).hexdigest()
            
            return event
    
    print("Could not extract event from photo")
    return None


def index_event(event):
    """Index an event in Elasticsearch"""
    
    try:
        es = Elasticsearch(['http://localhost:9200'])
        
        # Ensure index exists
        if not es.indices.exists(index='events'):
            es.indices.create(index='events')
        
        # Index the event
        result = es.index(index='events', document=event)
        print(f"✅ Indexed event: {event['title']}")
        print(f"   ID: {result['_id']}")
        return True
    
    except Exception as e:
        print(f"❌ Error indexing event: {e}")
        return False


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 extract_photo_event.py <photo_url> [image_url] [caption]")
        print("\nExample:")
        print('  python3 extract_photo_event.py "https://www.facebook.com/photo.php?fbid=..." ')
        print('    "https://example.com/image.jpg" "Event caption text"')
        sys.exit(1)
    
    photo_url = sys.argv[1]
    image_url = sys.argv[2] if len(sys.argv) > 2 else None
    caption = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"\nExtracting event from Facebook photo:")
    print(f"  Photo URL: {photo_url}")
    if image_url:
        print(f"  Image URL: {image_url}")
    if caption:
        print(f"  Caption: {caption[:50]}...")
    print()
    
    event = extract_event_from_facebook_photo(photo_url, image_url, caption)
    
    if event:
        print(f"\n📸 Extracted Event:")
        print(json.dumps(event, indent=2))
        
        # Ask to index
        if sys.stdin.isatty():
            response = input("\nIndex this event in Elasticsearch? (y/n): ")
            if response.lower() == 'y':
                index_event(event)
        else:
            index_event(event)
    else:
        print("❌ Could not extract event information")
        sys.exit(1)


if __name__ == '__main__':
    main()
