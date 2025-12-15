import random
import logging


class RandomUserAgentMiddleware:
    """Middleware to rotate user agents"""
    
    def __init__(self, crawler):
        self.user_agent_list = crawler.settings.get('USER_AGENT_LIST', [])
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
    
    def process_request(self, request, spider):
        if self.user_agent_list:
            user_agent = random.choice(self.user_agent_list)
            request.headers['User-Agent'] = user_agent
