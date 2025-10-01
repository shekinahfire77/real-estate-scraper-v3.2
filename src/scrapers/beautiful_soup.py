"""BeautifulSoup-based synchronous scraper"""

import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import BaseScraper
from ..config import DEFAULT_TIMEOUT, MAX_RETRIES, BACKOFF_FACTOR

logger = logging.getLogger(__name__)


class BeautifulSoupScraper(BaseScraper):
    """Synchronous scraper using requests and BeautifulSoup"""
    
    def __init__(self):
        """Initialize BeautifulSoup scraper"""
        super().__init__()
        
        # Set up session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def scrape(self, url: str) -> Optional[str]:
        """Scrape URL and return HTML content"""
        
        # Wait for rate limiting
        while not self.should_make_request(url):
            logger.debug(f"Rate limiting for {url}, waiting...")
            self.random_delay()
        
        # Prepare headers
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            # Record request
            self.record_request(url)
            
            # Make request
            response = self.session.get(
                url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True
            )
            
            # Check response status
            if response.status_code == 200:
                logger.info(f"Successfully scraped {url} with BeautifulSoup")
                return response.text
            elif response.status_code == 403:
                logger.warning(f"Access forbidden (403) for {url}")
                return None
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429) for {url}")
                return None
            else:
                logger.warning(f"Unexpected status code {response.status_code} for {url}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while scraping {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while scraping {url}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while scraping {url}: {e}")
            return None
    
    def close(self):
        """Close the session"""
        self.session.close()
