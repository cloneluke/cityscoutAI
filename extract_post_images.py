#!/usr/bin/env python3
"""
Extract images from Facebook posts and queue them for event processing.

This helper script guides you through the process of:
1. Opening a Facebook post
2. Extracting the image URL
3. Queueing it for automatic event analysis

Since Facebook blocks direct scraping, this semi-automated approach
leverages your browser to access the content, then processes it.
"""

import os
import sys
from datetime import datetime


def find_project_root():
    """Find the project root directory"""
    current = os.path.dirname(os.path.abspath(__file__))
    while current != '/':
        if os.path.exists(os.path.join(current, 'scrapy_project')):
            return current
        current = os.path.dirname(current)
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_ROOT = find_project_root()
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
PHOTO_URLS_FILE = os.path.join(DATA_DIR, 'facebook_photo_urls.txt')


def ensure_data_dir():
    """Ensure data directory exists"""
    os.makedirs(DATA_DIR, exist_ok=True)


def read_existing_photos():
    """Read existing photo URLs to avoid duplicates"""
    if not os.path.exists(PHOTO_URLS_FILE):
        return set()
    
    with open(PHOTO_URLS_FILE, 'r') as f:
        existing = set()
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    existing.add(parts[1])  # photo_url
        return existing


def add_photo_url(page_url, photo_url, image_url, caption=''):
    """Add a photo URL to the queue"""
    ensure_data_dir()
    
    existing_photos = read_existing_photos()
    if photo_url in existing_photos:
        print(f"⚠️  Photo URL already in queue: {photo_url[:60]}...")
        return False
    
    with open(PHOTO_URLS_FILE, 'a') as f:
        f.write(f"{page_url} | {photo_url} | {image_url} | {caption}\n")
    
    print(f"✅ Added to queue: {caption or 'Event image from ' + page_url.split('/')[-1]}")
    return True


def manual_entry_mode():
    """Interactive mode for manually entering post details"""
    print("\n" + "="*70)
    print("Facebook Post Image Extraction Helper")
    print("="*70)
    print("""
This tool helps you manually extract images from Facebook posts 
and queue them for automatic event analysis.

Steps:
1. Go to the Facebook post in your browser
2. Right-click on the image → "Copy image link"
3. Paste it below
4. The spider will analyze it for event details

Note: You may need to extract the image URL quickly, as Facebook 
generates temporary, signed URLs that expire after a few minutes.

To open a post: https://www.facebook.com/[page]/posts/[post_id]
""")
    
    while True:
        print("\n" + "-"*70)
        page_url = input("Facebook page URL (e.g., https://www.facebook.com/dtsfwine): ").strip()
        if not page_url:
            break
        
        if not page_url.startswith('http'):
            page_url = f"https://www.facebook.com/{page_url}"
        
        photo_url = input("Photo URL (right-click image → Copy image link): ").strip()
        if not photo_url:
            print("Skipping...")
            continue
        
        image_url = input("Image URL (usually same as photo URL, or paste direct image URL): ").strip()
        if not image_url:
            image_url = photo_url
        
        caption = input("Optional caption/notes (e.g., 'Wine event poster'): ").strip()
        
        if add_photo_url(page_url, photo_url, image_url, caption):
            run_spider = input("\nRun spider now to process? (y/n): ").strip().lower()
            if run_spider == 'y':
                import subprocess
                print("\nRunning spider...")
                try:
                    subprocess.run(
                        ['python3', '-m', 'scrapy', 'crawl', 'facebook'],
                        cwd=os.path.join(PROJECT_ROOT, 'scrapy_project'),
                        timeout=120
                    )
                except Exception as e:
                    print(f"Error running spider: {e}")
        
        another = input("\nAdd another image? (y/n): ").strip().lower()
        if another != 'y':
            break
    
    print("\nDone! Check http://localhost:8000/events to view extracted events.")


def batch_mode(urls_file):
    """Process URLs from a file"""
    if not os.path.exists(urls_file):
        print(f"File not found: {urls_file}")
        return
    
    print(f"Reading URLs from {urls_file}...")
    
    with open(urls_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                page_url = parts[0]
                photo_url = parts[1]
                image_url = parts[2]
                caption = parts[3] if len(parts) > 3 else ''
                
                if add_photo_url(page_url, photo_url, image_url, caption):
                    print(f"  ✅ {caption or photo_url[:40]}...")


def show_queue():
    """Show currently queued photos"""
    if not os.path.exists(PHOTO_URLS_FILE):
        print("No photos queued yet.")
        return
    
    print("\n" + "="*70)
    print("Queued Photo URLs")
    print("="*70)
    
    count = 0
    with open(PHOTO_URLS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    count += 1
                    page = parts[0].split('/')[-1]
                    caption = parts[3] if len(parts) > 3 else ''
                    print(f"{count}. [{page}] {caption}")
    
    print(f"\nTotal: {count} photos queued")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--queue':
            show_queue()
        elif sys.argv[1] == '--batch' and len(sys.argv) > 2:
            batch_mode(sys.argv[2])
        elif sys.argv[1] == '--help':
            print(__doc__)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage info")
    else:
        manual_entry_mode()


if __name__ == '__main__':
    main()
