"""Async scraper for concurrent requests"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import aiohttp
from aiohttp import ClientTimeout, ClientSession

from .base import BaseScraper
from ..config import ASYNC_TIMEOUT, DEFAULT_CONCURRENT_LIMIT

logger = logging.getLogger(__name__)


class AsyncScraper(BaseScraper):
    """Asynchronous scraper using aiohttp"""
    
    def __init__(self, concurrent_limit: int = DEFAULT_CONCURRENT_LIMIT):
        """Initialize async scraper"""
        super().__init__()
        self.concurrent_limit = concurrent_limit
        self.semaphore = asyncio.Semaphore(concurrent_limit)
        self.session: Optional[ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = ClientTimeout(total=ASYNC_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def scrape(self, url: str) -> Optional[str]:
        """Scrape a single URL asynchronously"""
        
        # Get site-specific settings
        settings = self.get_site_settings(url)
        max_concurrent = settings.get('max_concurrent', self.concurrent_limit)
        
        # Use site-specific semaphore if needed
        domain = self.get_domain(url)
        if not hasattr(self, 'domain_semaphores'):
            self.domain_semaphores = {}
        
        if domain not in self.domain_semaphores:
            self.domain_semaphores[domain] = asyncio.Semaphore(max_concurrent)
        
        semaphore = self.domain_semaphores[domain]
        
        async with semaphore:
            # Wait for rate limiting
            while not self.should_make_request(url):
                await asyncio.sleep(0.5)
            
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
                
                # Make async request
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        logger.info(f"Successfully scraped {url} asynchronously")
                        return await response.text()
                    elif response.status == 403:
                        logger.warning(f"Access forbidden (403) for {url}")
                        return None
                    elif response.status == 429:
                        logger.warning(f"Rate limited (429) for {url}")
                        return None
                    else:
                        logger.warning(f"Unexpected status {response.status} for {url}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout while scraping {url}")
                return None
            except aiohttp.ClientError as e:
                logger.error(f"Client error while scraping {url}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error while scraping {url}: {e}")
                return None
    
    async def scrape_multiple(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs concurrently"""
        tasks = [self.scrape(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Exception for {url}: {result}")
                output.append({'url': url, 'html': None, 'error': str(result)})
            else:
                output.append({'url': url, 'html': result, 'error': None})
        
        return output
