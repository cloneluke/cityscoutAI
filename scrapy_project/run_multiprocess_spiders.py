"""Multiprocessing spider runner for website event scraping"""

import sys
import os
import json
import logging
from multiprocessing import Pool, cpu_count
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from cityscout.spiders.dynamic_spider import DynamicWebsiteSpider
from cityscout.spiders.headless_spider import HeadlessWebsiteSpider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_urls_from_file(filepath):
    """Read URLs from a text file (one per line)"""
    urls = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
        logger.info(f"📂 Loaded {len(urls)} URLs from {filepath}")
        return urls
    except FileNotFoundError:
        logger.error(f"❌ File not found: {filepath}")
        return []


def scrape_url_batch(url_batch, spider_type='dynamic'):
    """Scrape a batch of URLs in a single worker process"""
    worker_id = os.getpid()
    batch_size = len(url_batch)
    logger.info(f"🔄 [Worker {worker_id}] Processing {batch_size} URLs with {spider_type} spider")
    
    settings = get_project_settings()
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('CONCURRENT_REQUESTS', 4)
    settings.set('DOWNLOAD_DELAY', 2)  # 2 second delay between requests
    
    # For headless spider, use Splash
    if spider_type == 'headless':
        settings.set('SPLASH_URL', 'http://localhost:8050')
        spider_class = HeadlessWebsiteSpider
    else:
        spider_class = DynamicWebsiteSpider
    
    all_events = []
    
    process = CrawlerProcess(settings)
    process.crawl(spider_class, urls=url_batch)
    process.start()
    
    logger.info(f"✅ [Worker {worker_id}] Completed batch of {batch_size} URLs")
    
    return all_events


class MultiProcessSpiderRunner:
    """Runner that uses multiprocessing for parallel website scraping"""
    
    def __init__(self, urls_file='data/website_urls.txt', spider_type='dynamic'):
        self.urls_file = urls_file
        self.spider_type = spider_type
        self.settings = get_project_settings()
        self.settings.set('LOG_LEVEL', 'INFO')
    
    def run_with_multiprocessing(self, num_workers=None):
        """Run spiders using multiprocessing"""
        
        # Read URLs from file
        urls = read_urls_from_file(self.urls_file)
        
        if not urls:
            logger.error("❌ No URLs found to scrape")
            return
        
        # Calculate workers
        if num_workers is None:
            num_workers = max(1, min(cpu_count() - 1, 4))  # Use up to 4 workers
        
        logger.info(f"🚀 Starting multiprocessing spider with {num_workers} workers ({self.spider_type} mode)")
        logger.info(f"📊 Total URLs to scrape: {len(urls)}")
        
        # Split URLs into batches for workers
        batch_size = max(1, len(urls) // num_workers)
        batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
        
        logger.info(f"📦 Split into {len(batches)} batches of ~{batch_size} URLs each")
        
        # Run spiders in parallel using multiprocessing
        with Pool(processes=num_workers) as pool:
            results = pool.starmap(scrape_url_batch, [(batch, self.spider_type) for batch in batches])
        
        logger.info(f"✅ All workers completed")
        
        # Combine results
        all_events = []
        for result in results:
            all_events.extend(result)
        
        logger.info(f"📈 Total events scraped: {len(all_events)}")
        
        return all_events
    
    def run_single_process(self):
        """Run all spiders in a single process (simpler, slower)"""
        
        urls = read_urls_from_file(self.urls_file)
        
        if not urls:
            logger.error("❌ No URLs found to scrape")
            return
        
        logger.info(f"🚀 Starting website spider (single process)")
        logger.info(f"📊 Total URLs to scrape: {len(urls)}")
        
        process = CrawlerProcess(self.settings)
        process.crawl(DynamicWebsiteSpider, urls=urls)
        process.start()
        
        logger.info(f"✅ Spider completed")


def main():
    """Main entry point"""
    
    # Check if custom URLs file provided
    # Try both relative and absolute paths
    urls_file = 'data/website_urls.txt'
    if not os.path.exists(urls_file):
        urls_file = '/data/website_urls.txt'
    
    num_workers = None
    spider_type = 'dynamic'  # Default to dynamic spider
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['dynamic', 'headless']:
            spider_type = sys.argv[1]
        elif sys.argv[1].endswith('.txt'):
            urls_file = sys.argv[1]
        else:
            try:
                num_workers = int(sys.argv[1])
            except ValueError:
                urls_file = sys.argv[1]
    
    if len(sys.argv) > 2:
        if sys.argv[2] in ['dynamic', 'headless']:
            spider_type = sys.argv[2]
        else:
            try:
                num_workers = int(sys.argv[2])
            except ValueError:
                pass
    
    if len(sys.argv) > 3:
        try:
            num_workers = int(sys.argv[3])
        except ValueError:
            pass
    
    runner = MultiProcessSpiderRunner(urls_file, spider_type)
    
    # Use multiprocessing by default
    runner.run_with_multiprocessing(num_workers)


if __name__ == '__main__':
    main()
