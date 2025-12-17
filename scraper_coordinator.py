#!/usr/bin/env python3
"""
Multithreaded scraper coordinator that runs all scrapers in parallel.
"""

import concurrent.futures
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s')
logger = logging.getLogger(__name__)

class ScraperCoordinator:
    def __init__(self):
        self.scrapers = {
            'facebook': 'docker run --rm --network cityscout -e ELASTICSEARCH_HOST=http://elasticsearch:9200 cityscout_headless python run_multiprocess_spiders.py facebook',
            'website': 'docker run --rm --network cityscout -e ELASTICSEARCH_HOST=http://elasticsearch:9200 -v website_urls:/data cityscout_playwright',
            'dynamic': 'docker run --rm --network cityscout -e ELASTICSEARCH_HOST=http://elasticsearch:9200 cityscout_scrapy dynamic',
        }
    
    def run_scraper(self, name, command):
        """Run a single scraper in a subprocess."""
        logger.info(f"Starting {name} scraper: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✓ {name} scraper completed successfully")
                if result.stdout:
                    logger.info(f"Output: {result.stdout}")
            else:
                logger.error(f"✗ {name} scraper failed with code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error: {result.stderr}")
            
            return name, result.returncode
        
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {name} scraper timed out after 10 minutes")
            return name, 1
        except Exception as e:
            logger.error(f"✗ {name} scraper error: {e}")
            return name, 1
    
    def run_all(self):
        """Run all scrapers in parallel."""
        logger.info("🚀 Starting multithreaded scraper coordinator")
        logger.info(f"📊 Running {len(self.scrapers)} scrapers in parallel")
        
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
            futures = {
                executor.submit(self.run_scraper, name, cmd): name 
                for name, cmd in self.scrapers.items()
            }
            
            for future in concurrent.futures.as_completed(futures):
                name, code = future.result()
                results[name] = code
        
        # Summary
        logger.info("=" * 60)
        logger.info("🎉 Scraper Coordinator Summary:")
        for name, code in results.items():
            status = "✓ Success" if code == 0 else "✗ Failed"
            logger.info(f"  {name}: {status}")
        
        all_success = all(code == 0 for code in results.values())
        if all_success:
            logger.info("✓ All scrapers completed successfully!")
            return 0
        else:
            logger.warning("⚠️ Some scrapers failed. Check logs above.")
            return 1


if __name__ == '__main__':
    coordinator = ScraperCoordinator()
    sys.exit(coordinator.run_all())
