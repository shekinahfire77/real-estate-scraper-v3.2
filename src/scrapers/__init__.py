"""Scraping engines with retry, pipeline, proxy, and stealth support"""

from .base import BaseScraper
from .beautiful_soup import BeautifulSoupScraper
from .async_scraper import AsyncScraper
from .async_pipeline import AsyncPipelineScraper
from .proxy_async_scraper import ProxyAsyncScraper, create_proxy_scraper_from_config
from .proxy_manager import ProxyManager, Proxy
# Stealth browser imports disabled - using Botasaurus instead
# from .stealth_browser import (
#     StealthBrowserScraper,
#     create_stealth_scraper,
#     needs_stealth_browser,
#     STEALTH_AVAILABLE,
#     STEALTH_LIBRARY
# )
from .async_retry import (
    AsyncRetryHandler,
    AsyncExponentialBackoff,
    async_retry,
    get_domain_retry_handler,
    configure_domain_retry
)
from .retry_handler import (
    retry_with_backoff,
    DomainCircuitBreaker,
    AdaptiveRateLimiter,
    ExponentialBackoff
)

__all__ = [
    # Scrapers
    'BaseScraper',
    'BeautifulSoupScraper', 
    'AsyncScraper',
    'AsyncPipelineScraper',
    'ProxyAsyncScraper',
    'create_proxy_scraper_from_config',
    'StealthBrowserScraper',
    'create_stealth_scraper',
    'needs_stealth_browser',
    'STEALTH_AVAILABLE',
    'STEALTH_LIBRARY',
    
    # Proxy management
    'ProxyManager',
    'Proxy',
    
    # Retry functionality
    'AsyncRetryHandler',
    'AsyncExponentialBackoff',
    'async_retry',
    'get_domain_retry_handler',
    'configure_domain_retry',
    'retry_with_backoff',
    'DomainCircuitBreaker',
    'AdaptiveRateLimiter',
    'ExponentialBackoff'
]
