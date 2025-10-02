"""Stealth browser scraper using Botasaurus for bypassing bot protection

Botasaurus is a stealth browser automation framework that bypasses advanced bot detection.
It uses Selenium-based stealth with anti-detection features.
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

try:
    from botasaurus import browser
    from botasaurus.browser import Driver
except ImportError:
    browser = None

from .base import BaseScraper
from ..config import USER_AGENTS, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


class BotasaurusScraper(BaseScraper):
    """Stealth browser scraper using Botasaurus to bypass bot protection

    Uses Botasaurus's anti-detection features:
    - Advanced browser fingerprinting evasion
    - Human-like behavior simulation
    - Canvas/WebGL fingerprint randomization
    - WebRTC leak prevention
    - Automatic ChromeDriver management
    """

    def __init__(self, max_concurrent: int = 2, headless: bool = True):
        """Initialize Botasaurus scraper

        Args:
            max_concurrent: Maximum concurrent browser contexts
            headless: Run in headless mode (False for debugging)
        """
        super().__init__()
        self.headless = headless
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        if browser is None:
            raise ImportError(
                "Botasaurus is not installed. Install with: pip install botasaurus"
            )

        logger.info(f"Botasaurus stealth scraper initialized (headless={headless}, concurrent={max_concurrent})")

    async def scrape(self, url: str, wait_for_selector: Optional[str] = None,
                    timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
        """Scrape a URL using stealth browser with retry logic

        Args:
            url: URL to scrape
            wait_for_selector: Optional CSS selector to wait for
            timeout: Request timeout in seconds

        Returns:
            HTML content or None on failure
        """
        async with self.semaphore:
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # Run browser operation in thread pool to avoid blocking
                    html = await asyncio.to_thread(
                        self._scrape_sync,
                        url,
                        wait_for_selector,
                        timeout
                    )

                    # Retry if no HTML content received
                    if html and len(html) > 100:
                        return html
                    else:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries}: No valid HTML from {url}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue

                except asyncio.TimeoutError:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries}: Timeout scraping {url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1}/{max_retries}: Error scraping {url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue

            logger.error(f"Failed to scrape {url} after {max_retries} attempts")
            return None

    def _scrape_sync(self, url: str, wait_for_selector: Optional[str], timeout: int) -> Optional[str]:
        """Synchronous scraping operation using Botasaurus

        Args:
            url: URL to scrape
            wait_for_selector: Optional CSS selector to wait for
            timeout: Request timeout in seconds

        Returns:
            HTML content or None on failure
        """
        try:
            from botasaurus.browser import Driver
            from botasaurus_driver import Driver as BotasaurusDriver

            # Create driver instance
            driver = BotasaurusDriver(
                headless=self.headless,
                user_agent=self.get_random_user_agent(),
                block_images=True
            )

            try:
                # Navigate to URL
                logger.debug(f"Botasaurus navigating to: {url}")
                driver.get(url, timeout=timeout)

                # Wait for selector if provided
                if wait_for_selector:
                    try:
                        driver.wait_for_element(wait_for_selector, timeout=10)
                    except Exception as e:
                        logger.debug(f"Selector '{wait_for_selector}' not found: {e}")

                # Additional wait for JavaScript execution (increased for heavy JS sites)
                import time
                import random
                wait_time = random.uniform(5, 8)
                logger.debug(f"Waiting {wait_time:.1f}s for JavaScript execution")
                time.sleep(wait_time)

                # Extract HTML
                html = driver.page_html

                # Log HTML length and first 500 chars for debugging
                if html:
                    logger.debug(f"Successfully scraped {url} ({len(html)} bytes)")
                    logger.debug(f"HTML preview: {html[:500]}")
                else:
                    logger.warning(f"No HTML content retrieved from {url}")

                return html

            finally:
                # Close driver
                try:
                    driver.close()
                except:
                    pass

        except Exception as e:
            logger.error(f"Botasaurus scrape failed for {url}: {e}")
            return None

    def get_random_user_agent(self) -> str:
        """Get random user agent"""
        import random
        return random.choice(USER_AGENTS)
