# Scrapy settings for cityscout project

BOT_NAME = 'cityscout'

SPIDER_MODULES = ['cityscout.spiders']
NEWSPIDER_MODULE = 'cityscout.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy
# Keep this low to avoid overwhelming servers
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website
# Facebook is aggressive about blocking, so be very conservative
DOWNLOAD_DELAY = 15
RANDOMIZE_DOWNLOAD_DELAY = True
RANDOM_DOWNLOAD_DELAY_RANGE = [10, 30]

# The average amount of time (in seconds) that the downloader should wait
DOWNLOAD_TIMEOUT = 30

# User agent list for rotation - use realistic modern agents
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Enable and configure HTTP caching
# Disabled for website spiders - they need fresh pages to render JS
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = 'httpcache'

# Disable autothrottle for Facebook - use manual conservative settings instead
AUTOTHROTTLE_ENABLED = False

# Configure item pipelines
ITEM_PIPELINES = {
    'cityscout.pipelines.DeduplicationPipeline': 300,
}

# Elasticsearch configuration
ELASTICSEARCH_HOST = 'http://localhost:9200'

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# Retry settings - conservative to avoid triggering anti-bot measures
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
RETRY_TIMES_WAIT = 10

# Disable cookies to avoid session tracking
COOKIES_ENABLED = False

# Add referrer header for more realistic browsing
REFERER_ENABLED = True
