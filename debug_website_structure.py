#!/usr/bin/env python3
"""
Debug script to inspect actual HTML structure after JavaScript rendering.
Saves rendered HTML and identifies event containers.
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def debug_website(url, output_file):
    """Load website and save rendered HTML for inspection."""
    print(f"🔍 Debugging: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Get full rendered HTML
            content = await page.content()
            
            with open(output_file, 'w') as f:
                f.write(content)
            
            print(f"✓ Saved {len(content)} bytes to {output_file}")
            
            # Try to find event-like elements
            print("\n🔎 Searching for event containers...")
            
            selectors_to_try = [
                'div[class*="event"]',
                'div.event',
                'article',
                'li[class*="event"]',
                '[data-event]',
                'div[class*="card"]',
                'div[class*="item"]',
                'section[class*="event"]',
                '.event-item',
                '.listing',
                'div.col',
                'div.row',
                '[role="article"]',
                '[role="listitem"]',
            ]
            
            for selector in selectors_to_try:
                count = len(await page.query_selector_all(selector))
                if count > 0:
                    print(f"  ✓ {selector}: {count} elements")
                    
                    # Get text from first few
                    for i in range(min(2, count)):
                        elem = (await page.query_selector_all(selector))[i]
                        text = await elem.text_content()
                        if text:
                            preview = text[:100].replace('\n', ' ')
                            print(f"    [{i}] {preview}...")
            
            # Look for date-like patterns
            print("\n📅 Looking for date patterns...")
            all_text = await page.text_content()
            
            import re
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}/\d{1,2}\b'
            dates_found = re.findall(date_pattern, all_text, re.IGNORECASE)
            if dates_found:
                print(f"  Found {len(dates_found)} date-like patterns:")
                for date in dates_found[:5]:
                    print(f"    - {date}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            await browser.close()

async def main():
    sites = [
        ("https://www.experiencesiouxfalls.com/events", "experience_sioux_falls.html"),
        ("https://www.sanfordsports.com/events?eventCategory=Spectator+Events&location=Sanford+Sports+Complex&facilityType=Sanford+Pentagon", "sanford_sports.html"),
    ]
    
    for url, output in sites:
        print(f"\n{'='*60}")
        await debug_website(url, output)
        print(f"{'='*60}\n")

if __name__ == '__main__':
    asyncio.run(main())
