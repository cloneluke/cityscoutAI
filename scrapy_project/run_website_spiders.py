"""Multi-spider runner for website event scraping"""

import sys
import os
import json
import logging
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Import all spiders
from cityscout.spiders.meetup_spider import MeetupSpider
from cityscout.spiders.local_websites_spider import (
    VisitSiouxFallsSpider,
    SiouxFallsChamberSpider,
    SiouxFallsArtsCenterSpider,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiSpiderRunner:
    """Runner for executing multiple spiders and combining results"""
    
    def __init__(self, output_dir='/data'):
        self.output_dir = output_dir
        self.settings = get_project_settings()
        self.settings.set('LOG_LEVEL', 'INFO')
        self.all_events = []
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def run_all_spiders(self):
        """Run all available spiders"""
        spiders = [
            VisitSiouxFallsSpider,
            SiouxFallsChamberSpider,
            SiouxFallsArtsCenterSpider,
            MeetupSpider,
        ]
        
        process = CrawlerProcess(self.settings)
        
        logger.info(f"🚀 Starting {len(spiders)} website spiders...")
        
        for spider_class in spiders:
            process.crawl(spider_class)
        
        process.start()
        
        logger.info(f"✅ All spiders completed")
    
    def run_specific_spider(self, spider_name):
        """Run a specific spider by name"""
        spiders_map = {
            'visitsiouxfalls': VisitSiouxFallsSpider,
            'sfchamber': SiouxFallsChamberSpider,
            'sfartscenter': SiouxFallsArtsCenterSpider,
            'meetup': MeetupSpider,
        }
        
        spider_class = spiders_map.get(spider_name)
        if not spider_class:
            logger.error(f"Unknown spider: {spider_name}")
            logger.info(f"Available spiders: {list(spiders_map.keys())}")
            return
        
        process = CrawlerProcess(self.settings)
        logger.info(f"🚀 Starting {spider_name} spider...")
        process.crawl(spider_class)
        process.start()
        logger.info(f"✅ Spider {spider_name} completed")


def main():
    """Main entry point"""
    runner = MultiSpiderRunner()
    
    # Check if specific spider requested via command line
    if len(sys.argv) > 1:
        spider_name = sys.argv[1]
        runner.run_specific_spider(spider_name)
    else:
        runner.run_all_spiders()


if __name__ == '__main__':
    main()
