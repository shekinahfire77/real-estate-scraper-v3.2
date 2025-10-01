"""Base scraper class"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from collections import defaultdict, deque

from ..config import SITE_CONCURRENCY_SETTINGS, USER_AGENTS

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for scrapers"""
    
    def __init__(self):
        """Initialize base scraper"""
        self.site_stats = defaultdict(lambda: {
            'last_request_time': 0,
            'request_count': 0,
            'request_times': deque(maxlen=100)
        })
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    
    def get_site_settings(self, url: str) -> Dict[str, Any]:
        """Get site-specific settings"""
        domain = self.get_domain(url)
        return SITE_CONCURRENCY_SETTINGS.get(
            domain, 
            SITE_CONCURRENCY_SETTINGS['default']
        )
    
    def should_make_request(self, url: str) -> bool:
        """Check if we can make a request based on rate limits"""
        domain = self.get_domain(url)
        stats = self.site_stats[domain]
        settings = self.get_site_settings(url)
        
        now = time.time()
        
        # Check requests per minute limit
        recent_requests = [t for t in stats['request_times'] if now - t < 60]
        if len(recent_requests) >= settings.get('requests_per_minute', 15):
            return False
        
        # Check minimum delay
        min_delay = settings.get('delay_between_requests', (2, 4))[0]
        if now - stats['last_request_time'] < min_delay:
            return False
        
        return True
    
    def record_request(self, url: str):
        """Record that a request was made"""
        domain = self.get_domain(url)
        stats = self.site_stats[domain]
        now = time.time()
        
        stats['last_request_time'] = now
        stats['request_times'].append(now)
        stats['request_count'] += 1
    
    def get_random_user_agent(self) -> str:
        """Get random user agent"""
        return random.choice(USER_AGENTS)
    
    def random_delay(self, url: Optional[str] = None):
        """Smart delay based on site settings"""
        if url:
            settings = self.get_site_settings(url)
            delay_range = settings.get('delay_between_requests', (1, 4))
        else:
            delay_range = (1, 4)
        
        delay = random.uniform(delay_range[0], delay_range[1])
        time.sleep(delay)
    
    @abstractmethod
    def scrape(self, url: str) -> Optional[str]:
        """Scrape a URL and return HTML content"""
        pass
