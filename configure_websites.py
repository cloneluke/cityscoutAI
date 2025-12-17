#!/usr/bin/env python3
"""
Interactive website scraper configurator
Allows users to add websites and define custom CSS selectors per website
"""

import json
import os
from pathlib import Path
from urllib.parse import urlparse


CONFIG_FILE = 'data/websites_config.json'


def load_config():
    """Load website configuration"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save website configuration"""
    os.makedirs('data', exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Configuration saved to {CONFIG_FILE}")


def add_website():
    """Add a new website to scrape"""
    print("\n📝 Add Website Configuration")
    print("=" * 50)
    
    url = input("Website URL: ").strip()
    domain = urlparse(url).netloc
    
    print("\nCSS Selectors (leave blank for auto-detection):")
    selectors = {
        'event_container': input("Event container selector (e.g., 'div.event-item'): ").strip() or 'div[class*="event"]',
        'title': input("Event title selector (e.g., 'h3.title'): ").strip() or 'h3, h2, [class*="title"]',
        'date': input("Event date selector (e.g., 'span.date'): ").strip() or '[class*="date"], time',
        'location': input("Event location selector (e.g., 'span.venue'): ").strip() or '[class*="location"], [class*="venue"]',
    }
    
    config = load_config()
    config[domain] = {
        'url': url,
        'selectors': selectors,
        'enabled': True,
        'spider_type': 'dynamic'  # Can be 'dynamic' or 'headless'
    }
    
    save_config(config)
    print(f"\n✅ Added website: {domain}")


def list_websites():
    """List all configured websites"""
    config = load_config()
    
    if not config:
        print("❌ No websites configured yet")
        return
    
    print("\n📋 Configured Websites")
    print("=" * 50)
    
    for domain, data in config.items():
        status = "✅" if data.get('enabled') else "❌"
        spider = data.get('spider_type', 'dynamic')
        print(f"\n{status} {domain} ({spider})")
        print(f"   URL: {data.get('url')}")
        print(f"   Selectors: {list(data.get('selectors', {}).keys())}")


def edit_website():
    """Edit an existing website configuration"""
    config = load_config()
    
    if not config:
        print("❌ No websites configured yet")
        return
    
    print("\n🔧 Edit Website Configuration")
    print("=" * 50)
    
    print("\nAvailable websites:")
    for i, domain in enumerate(config.keys(), 1):
        print(f"{i}. {domain}")
    
    choice = input("\nSelect website number: ").strip()
    
    try:
        idx = int(choice) - 1
        website_domains = list(config.keys())
        domain = website_domains[idx]
    except (ValueError, IndexError):
        print("❌ Invalid selection")
        return
    
    data = config[domain]
    
    print(f"\nEditing {domain}:")
    
    new_url = input(f"URL [{data.get('url')}]: ").strip()
    if new_url:
        data['url'] = new_url
    
    print("\nSelectors (press Enter to keep current):")
    for selector_key, selector_val in data.get('selectors', {}).items():
        new_val = input(f"{selector_key} [{selector_val}]: ").strip()
        if new_val:
            data['selectors'][selector_key] = new_val
    
    spider = input(f"Spider type [{data.get('spider_type', 'dynamic')}] (dynamic/headless): ").strip().lower()
    if spider in ['dynamic', 'headless']:
        data['spider_type'] = spider
    
    save_config(config)
    print(f"\n✅ Updated website: {domain}")


def toggle_website():
    """Enable/disable a website"""
    config = load_config()
    
    if not config:
        print("❌ No websites configured yet")
        return
    
    print("\nAvailable websites:")
    for i, (domain, data) in enumerate(config.items(), 1):
        status = "✅" if data.get('enabled') else "❌"
        print(f"{i}. {status} {domain}")
    
    choice = input("\nSelect website number: ").strip()
    
    try:
        idx = int(choice) - 1
        website_domains = list(config.keys())
        domain = website_domains[idx]
    except (ValueError, IndexError):
        print("❌ Invalid selection")
        return
    
    data = config[domain]
    data['enabled'] = not data.get('enabled', True)
    status = "enabled" if data['enabled'] else "disabled"
    
    save_config(config)
    print(f"✅ {domain} is now {status}")


def export_urls():
    """Export enabled websites to website_urls.txt"""
    config = load_config()
    
    enabled_urls = [
        data.get('url') 
        for data in config.values() 
        if data.get('enabled', True)
    ]
    
    if not enabled_urls:
        print("❌ No enabled websites found")
        return
    
    os.makedirs('data', exist_ok=True)
    with open('data/website_urls.txt', 'w') as f:
        f.write('\n'.join(enabled_urls))
    
    print(f"✅ Exported {len(enabled_urls)} URLs to data/website_urls.txt")
    print("   URLs:")
    for url in enabled_urls:
        print(f"   - {url}")


def main():
    """Main menu"""
    while True:
        print("\n🌐 Website Scraper Configuration")
        print("=" * 50)
        print("1. Add website")
        print("2. List websites")
        print("3. Edit website")
        print("4. Enable/disable website")
        print("5. Export URLs to website_urls.txt")
        print("6. Run Docker scraper (dynamic)")
        print("7. Run Docker scraper (headless)")
        print("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            add_website()
        elif choice == '2':
            list_websites()
        elif choice == '3':
            edit_website()
        elif choice == '4':
            toggle_website()
        elif choice == '5':
            export_urls()
        elif choice == '6':
            export_urls()
            print("\n🐳 Running Docker scraper (dynamic mode)...")
            os.system('cd /home/luke/git-repos/cityscoutAI && docker run --rm --network host -v $(pwd)/data:/data cityscout_scrapy:latest dynamic')
        elif choice == '7':
            export_urls()
            print("\n🐳 Running Docker scraper (headless mode)...")
            os.system('cd /home/luke/git-repos/cityscoutAI && docker run --rm --network host -v $(pwd)/data:/data cityscout_scrapy:latest headless')
        elif choice == '0':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == '__main__':
    main()
