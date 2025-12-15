#!/usr/bin/env python3
"""
Helper script to find and extract event photos from Facebook pages

Since Facebook blocks web scrapers, this script provides a semi-manual workflow:
1. Open the Facebook page in your browser
2. Scroll through posts to find event photos
3. For each event photo, right-click and "Copy image link"
4. Use this script to add photos to the event extraction queue

Usage:
    python3 find_event_photos.py
    # Then interactively add photos
"""

import os
import sys

def get_facebook_venues():
    """Load venue information"""
    venues = {}
    venue_file = '/home/luke/git-repos/cityscoutAI/data/facebook_venues.txt'
    
    if os.path.exists(venue_file):
        with open(venue_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        facebook_url = parts[0]
                        venue_name = parts[1]
                        address = parts[2]
                        venues[facebook_url] = {
                            'name': venue_name,
                            'address': address
                        }
    return venues


def display_venues():
    """Display available venues"""
    venues = get_facebook_venues()
    print("\n📍 Available Venues:")
    for url, info in venues.items():
        print(f"   {url}")
        print(f"      → {info['name']} ({info['address']})")
    return venues


def add_photo_to_queue():
    """Interactively add a photo to the queue"""
    venues = display_venues()
    
    print("\n" + "="*70)
    print("📸 ADD EVENT PHOTO")
    print("="*70)
    
    # Select venue
    print("\nSelect a venue (paste the Facebook URL):")
    page_url = input("Facebook page URL: ").strip()
    
    if page_url not in venues:
        print(f"❌ Venue not found. Please add it to data/facebook_venues.txt first")
        return False
    
    venue = venues[page_url]
    print(f"✅ Selected: {venue['name']} ({venue['address']})")
    
    # Get photo URL
    print("\nTo find the photo URL:")
    print("  1. Open the Facebook page in your browser")
    print("  2. Find the post with the event photo")
    print("  3. Right-click the image")
    print("  4. Select 'Copy image link'")
    print("  5. Paste it below")
    
    photo_url = input("\nFacebook photo URL (https://www.facebook.com/photo.php?...): ").strip()
    if not photo_url.startswith('https://'):
        print("❌ Invalid URL")
        return False
    
    # Get image URL
    print("\nTo get the direct image URL:")
    print("  1. Right-click the image")
    print("  2. Select 'Copy image link'")
    print("  3. Paste it below")
    
    image_url = input("\nDirect image URL (https://...): ").strip()
    if not image_url.startswith('https://'):
        print("⚠️  No image URL provided - will try to extract from photo page")
        image_url = ""
    
    # Get caption
    caption = input("\nPhoto caption/description (optional): ").strip()
    
    # Confirm
    print("\n" + "="*70)
    print("📋 REVIEW")
    print("="*70)
    print(f"Venue:    {venue['name']}")
    print(f"Photo:    {photo_url}")
    if image_url:
        print(f"Image:    {image_url}")
    if caption:
        print(f"Caption:  {caption}")
    
    confirm = input("\nAdd to queue? (y/n): ").strip().lower()
    if confirm != 'y':
        return False
    
    # Append to file
    photo_file = '/home/luke/git-repos/cityscoutAI/data/facebook_photo_urls.txt'
    
    entry = f"{page_url} | {photo_url}"
    if image_url or caption:
        entry += f" | {image_url}"
    if caption:
        entry += f" | {caption}"
    
    try:
        with open(photo_file, 'a') as f:
            f.write(entry + '\n')
        print(f"\n✅ Added to {photo_file}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def list_queued_photos():
    """List photos already in queue"""
    photo_file = '/home/luke/git-repos/cityscoutAI/data/facebook_photo_urls.txt'
    
    if not os.path.exists(photo_file):
        print("No queued photos yet")
        return
    
    print("\n" + "="*70)
    print("📸 QUEUED PHOTOS FOR PROCESSING")
    print("="*70)
    
    count = 0
    with open(photo_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = [p.strip() for p in line.split('|')]
                count += 1
                page_url = parts[0]
                photo_url = parts[1] if len(parts) > 1 else "N/A"
                
                venues = get_facebook_venues()
                venue = venues.get(page_url, {})
                venue_name = venue.get('name', 'Unknown')
                
                print(f"\n{count}. {venue_name}")
                print(f"   Photo: {photo_url[:60]}...")
                if len(parts) > 3 and parts[3]:
                    print(f"   Caption: {parts[3][:50]}...")
    
    if count == 0:
        print("No queued photos yet")
    else:
        print(f"\n✅ {count} photos queued for processing")
        print("\nTo process these photos:")
        print("  cd /home/luke/git-repos/cityscoutAI/scrapy_project")
        print("  python3 -m scrapy crawl facebook")


def main():
    """Main menu"""
    while True:
        print("\n" + "="*70)
        print("🎯 FACEBOOK EVENT PHOTO EXTRACTOR")
        print("="*70)
        print("\n1. Add event photo from Facebook post")
        print("2. View queued photos")
        print("3. Exit")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            if add_photo_to_queue():
                print("\n✨ Photo added successfully!")
        elif choice == '2':
            list_queued_photos()
        elif choice == '3':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled")
        sys.exit(0)
