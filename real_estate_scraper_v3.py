#!/usr/bin/env python3
"""
Real Estate Web Scraper v3 - Production-Ready Commercial Edition
Enhanced with Pydantic validation, improved selectors, and quality scoring
"""

import csv
import time
import random
import logging
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse
from collections import defaultdict, deque
import requests
from bs4 import BeautifulSoup

# Pydantic for data validation
try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logging.warning("Pydantic not available. Install with: pip install pydantic")

# Playwright (optional dependency)
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# User-Agent rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# Site-specific concurrency settings (from Perplexity research)
SITE_CONCURRENCY_SETTINGS = {
    'zillow.com': {
        'delay_between_requests': (5, 10),
        'requests_per_minute': 6,
        'max_retries': 2
    },
    'realtor.com': {
        'delay_between_requests': (3, 6),
        'requests_per_minute': 12,
        'max_retries': 3
    },
    'apartments.com': {
        'delay_between_requests': (2, 4),
        'requests_per_minute': 20,
        'max_retries': 3
    },
    'rent.com': {
        'delay_between_requests': (1, 3),
        'requests_per_minute': 25,
        'max_retries': 3
    },
    'rentals.com': {
        'delay_between_requests': (1, 2),
        'requests_per_minute': 30,
        'max_retries': 2
    },
    'trulia.com': {
        'delay_between_requests': (4, 8),
        'requests_per_minute': 10,
        'max_retries': 2
    }
}

# Enhanced CSS selectors with fallbacks (from Perplexity research)
ZILLOW_SELECTORS = {
    'price': ['[data-testid="price"]', 'span[data-test="property-card-price"]', '.list-card-price'],
    'address': ['[data-testid="property-card-addr"]', 'address', '.list-card-addr'],
    'beds': ['[data-testid="property-card-bed"]', 'span[data-test="property-card-beds"]'],
    'baths': ['[data-testid="property-card-bath"]', 'span[data-test="property-card-baths"]'],
    'sqft': ['[data-testid="property-card-sqft"]', 'span[data-test="property-card-sqft"]'],
    'listing_id': ['[data-zpid]'],
    'photos': ['picture img[src*="photos.zillowstatic.com"]', '.media-stream img']
}

REALTOR_SELECTORS = {
    'price': ['[data-testid="card-price"]', '.price', '[class*="price"]'],
    'address': ['[data-testid="card-address"]', 'address', '.card-address'],
    'beds': ['[data-testid="meta-beds"]', 'li[data-label="bed"]'],
    'baths': ['[data-testid="meta-baths"]', 'li[data-label="bath"]'],
    'sqft': ['[data-testid="meta-sqft"]', 'li[data-label="sqft"]'],
    'listing_id': ['[data-listingid]', '[data-testid="property-card"]'],
    'photos': ['.photo img', '[data-testid="property-photo"]']
}

# Pydantic validation models
if PYDANTIC_AVAILABLE:
    class RealEstateProperty(BaseModel):
        """Validated real estate property data"""
        url: str = Field(..., min_length=10)
        listing_id: Optional[str] = None
        price: Optional[float] = Field(None, ge=0, le=50000000)
        address: Optional[str] = Field(None, min_length=5)
        bedrooms: Optional[int] = Field(None, ge=0, le=20)
        bathrooms: Optional[float] = Field(None, ge=0, le=20)
        square_footage: Optional[int] = Field(None, ge=100, le=50000)
        page_type: Optional[str] = None
        property_description: Optional[str] = None
        photos: Optional[str] = None
        scrape_method: str = "Unknown"

        @validator('price')
        def validate_price(cls, v):
            if v is not None and (v < 100 or v > 50000000):
                logger.warning(f'Price {v} seems unrealistic')
            return v

        @validator('address')
        def validate_address(cls, v):
            if v and (len(v) < 5 or 'n/a' in v.lower()):
                return None
            return v

        class Config:
            extra = 'allow'


class RealEstateScraperV3:
    """Production-ready scraper with validation and quality scoring"""

    def __init__(self, input_csv: str = 'real_estate_urls.csv',
                 output_csv: str = 'real_estate_data.csv',
                 failures_log: str = 'failures.log',
                 quality_report: str = 'quality_report.json',
                 use_playwright: bool = True):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.failures_log = failures_log
        self.quality_report_file = quality_report
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE

        self.session = requests.Session()
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.scraped_data = []
        self.failed_urls = []
        self.validation_failures = []

        # Site-specific rate limiting
        self.site_stats = defaultdict(lambda: {
            'last_request_time': 0,
            'request_count': 0,
            'request_times': deque(maxlen=100)
        })

        # Playwright browser (lazy initialization)
        self.playwright = None
        self.browser = None

        # CSV headers
        self.csv_headers = [
            'url', 'page_type', 'listing_id', 'price', 'address',
            'bedrooms', 'bathrooms', 'square_footage', 'property_description',
            'photos', 'days_on_market', 'property_history',
            'monthly_rent', 'security_deposit', 'lease_terms', 'amenities',
            'pet_policy', 'contact_info', 'availability_date', 'application_requirements',
            'lease_rate', 'property_size', 'zoning_info', 'parking',
            'building_specs', 'property_management',
            'scrape_method', 'has_api_data', 'quality_score'
        ]

    def __enter__(self):
        """Context manager entry"""
        if self.use_playwright:
            self.init_playwright()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close_playwright()

    def init_playwright(self):
        """Initialize Playwright browser"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available")
            self.use_playwright = False
            return

        try:
            logger.info("Initializing Playwright browser...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            logger.info("Playwright browser initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            self.use_playwright = False

    def close_playwright(self):
        """Close Playwright browser"""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass

    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain

    def get_site_settings(self, url: str) -> dict:
        """Get site-specific settings"""
        domain = self.get_domain(url)
        return SITE_CONCURRENCY_SETTINGS.get(domain, {
            'delay_between_requests': (2, 4),
            'requests_per_minute': 15,
            'max_retries': 3
        })

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

    def random_delay(self, url: str = None):
        """Smart delay based on site settings"""
        if url:
            settings = self.get_site_settings(url)
            delay_range = settings.get('delay_between_requests', (1, 4))
        else:
            delay_range = (1, 4)

        delay = random.uniform(delay_range[0], delay_range[1])
        time.sleep(delay)

    def extract_with_fallback_selectors(self, soup: BeautifulSoup,
                                       selectors: List[str]) -> str:
        """Extract data with multiple fallback selectors"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 0:
                        return text
            except:
                continue
        return ""

    def extract_zillow_data(self, soup: BeautifulSoup) -> dict:
        """Extract data using Zillow selectors"""
        data = {}
        data['price'] = self.extract_with_fallback_selectors(soup, ZILLOW_SELECTORS['price'])
        data['address'] = self.extract_with_fallback_selectors(soup, ZILLOW_SELECTORS['address'])
        data['bedrooms'] = self.extract_with_fallback_selectors(soup, ZILLOW_SELECTORS['beds'])
        data['bathrooms'] = self.extract_with_fallback_selectors(soup, ZILLOW_SELECTORS['baths'])
        data['square_footage'] = self.extract_with_fallback_selectors(soup, ZILLOW_SELECTORS['sqft'])

        # Extract photos
        photos = []
        for selector in ZILLOW_SELECTORS['photos']:
            imgs = soup.select(selector)
            for img in imgs[:10]:  # Limit to 10 photos
                src = img.get('src') or img.get('data-src')
                if src and 'http' in src:
                    photos.append(src)

        if photos:
            data['photos'] = ','.join(photos)

        return data

    def extract_realtor_data(self, soup: BeautifulSoup) -> dict:
        """Extract data using Realtor.com selectors"""
        data = {}
        data['price'] = self.extract_with_fallback_selectors(soup, REALTOR_SELECTORS['price'])
        data['address'] = self.extract_with_fallback_selectors(soup, REALTOR_SELECTORS['address'])
        data['bedrooms'] = self.extract_with_fallback_selectors(soup, REALTOR_SELECTORS['beds'])
        data['bathrooms'] = self.extract_with_fallback_selectors(soup, REALTOR_SELECTORS['baths'])
        data['square_footage'] = self.extract_with_fallback_selectors(soup, REALTOR_SELECTORS['sqft'])

        # Extract photos
        photos = []
        for selector in REALTOR_SELECTORS['photos']:
            imgs = soup.select(selector)
            for img in imgs[:10]:
                src = img.get('src') or img.get('data-src')
                if src and 'http' in src:
                    photos.append(src)

        if photos:
            data['photos'] = ','.join(photos)

        return data

    def scrape_with_playwright(self, url: str) -> Optional[str]:
        """Scrape URL using Playwright"""
        if not self.browser:
            return None

        try:
            logger.info(f"  Using Playwright for: {url}")
            context = self.browser.new_context(
                user_agent=self.get_random_user_agent(),
                viewport={'width': random.choice([1920, 1366, 1536]),
                         'height': random.choice([1080, 768, 864])}
            )
            page = context.new_page()

            # Stealth mode
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page.goto(url, wait_until='networkidle', timeout=30000)

            # Human-like behavior
            page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            page.wait_for_timeout(random.randint(1000, 3000))

            html = page.content()
            context.close()

            return html

        except Exception as e:
            logger.error(f"Playwright error on {url}: {e}")
            return None

    def scrape_url(self, url: str) -> Optional[dict]:
        """Main scraping method with smart fallbacks"""
        # Wait for rate limiting
        while not self.should_make_request(url):
            time.sleep(1)

        domain = self.get_domain(url)
        settings = self.get_site_settings(url)

        # Try static scraping first
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

        html = None
        scrape_method = "Failed"

        # Try BeautifulSoup first
        try:
            self.record_request(url)
            response = self.session.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                html = response.text
                scrape_method = "BeautifulSoup"
                logger.info(f"  BeautifulSoup success")
            elif response.status_code == 403:
                logger.warning(f"  HTTP 403 - trying Playwright")
            elif response.status_code == 429:
                logger.warning(f"  Rate limited - waiting")
                time.sleep(settings.get('delay_between_requests', (2, 4))[1] * 2)

        except Exception as e:
            logger.warning(f"  BeautifulSoup failed: {e}")

        # Fall back to Playwright if needed
        if not html and self.use_playwright:
            html = self.scrape_with_playwright(url)
            if html:
                scrape_method = "Playwright"

        if not html:
            self.failed_scrapes += 1
            self.failed_urls.append(url)
            return None

        # Extract data
        soup = BeautifulSoup(html, 'lxml')
        data = {'url': url, 'scrape_method': scrape_method}

        # Use site-specific selectors
        if 'zillow.com' in domain:
            extracted = self.extract_zillow_data(soup)
            data.update(extracted)
        elif 'realtor.com' in domain:
            extracted = self.extract_realtor_data(soup)
            data.update(extracted)
        else:
            # Generic extraction for other sites
            data['price'] = self.extract_price(soup)
            data['address'] = self.extract_address(soup)
            data['bedrooms'] = self.extract_bedrooms(soup)
            data['bathrooms'] = self.extract_bathrooms(soup)

        # Validate and score data
        if PYDANTIC_AVAILABLE:
            validated = self.validate_and_score(data)
            if validated:
                self.successful_scrapes += 1
                return validated
        else:
            self.successful_scrapes += 1
            return data

        return None

    def validate_and_score(self, raw_data: dict) -> Optional[dict]:
        """Validate data and calculate quality score"""
        try:
            # Clean numeric fields
            if raw_data.get('price'):
                price_match = re.search(r'[\d,]+', raw_data['price'].replace(',', ''))
                raw_data['price'] = float(price_match.group()) if price_match else None

            for field in ['bedrooms', 'bathrooms', 'square_footage']:
                if raw_data.get(field):
                    numbers = re.findall(r'\d+\.?\d*', str(raw_data[field]))
                    raw_data[field] = float(numbers[0]) if numbers else None

            # Validate
            validated = RealEstateProperty(**raw_data)

            # Calculate quality score
            score = self.calculate_quality_score(validated.dict())
            validated_dict = validated.dict()
            validated_dict['quality_score'] = score

            return validated_dict

        except Exception as e:
            logger.warning(f"Validation failed for {raw_data.get('url')}: {e}")
            self.validation_failures.append({
                'url': raw_data.get('url'),
                'error': str(e)
            })
            return None

    def calculate_quality_score(self, data: dict) -> int:
        """Calculate data quality score (0-100)"""
        score = 0

        # Required fields (40 points)
        required_fields = ['price', 'address', 'bedrooms', 'bathrooms']
        filled_required = sum(1 for f in required_fields if data.get(f))
        score += (filled_required / len(required_fields)) * 40

        # Optional fields (20 points)
        optional_fields = ['square_footage', 'property_description', 'photos']
        filled_optional = sum(1 for f in optional_fields if data.get(f))
        score += (filled_optional / len(optional_fields)) * 20

        # Data reasonableness (40 points)
        if data.get('price') and 100 <= data['price'] <= 50000000:
            score += 15

        if data.get('address') and len(str(data['address']).split()) >= 3:
            score += 10

        if data.get('bedrooms') and 0 <= data['bedrooms'] <= 10:
            score += 8

        if data.get('square_footage') and 200 <= data['square_footage'] <= 20000:
            score += 7

        return min(int(score), 100)

    # Generic extraction methods (fallback)
    def extract_price(self, soup: BeautifulSoup) -> str:
        """Generic price extraction"""
        price_selectors = ['.price', '[class*="price"]', '[data-price]']
        price = self.extract_with_fallback_selectors(soup, price_selectors)
        if not price:
            price_match = re.search(r'\$[\d,]+', soup.get_text())
            if price_match:
                price = price_match.group()
        return price

    def extract_address(self, soup: BeautifulSoup) -> str:
        """Generic address extraction"""
        address_selectors = ['address', '.address', '[class*="address"]']
        return self.extract_with_fallback_selectors(soup, address_selectors)

    def extract_bedrooms(self, soup: BeautifulSoup) -> str:
        """Generic bedrooms extraction"""
        bed_patterns = [r'(\d+)\s*bed', r'(\d+)\s*bd']
        text = soup.get_text()
        for pattern in bed_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def extract_bathrooms(self, soup: BeautifulSoup) -> str:
        """Generic bathrooms extraction"""
        bath_patterns = [r'(\d+\.?\d*)\s*bath', r'(\d+\.?\d*)\s*ba']
        text = soup.get_text()
        for pattern in bath_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""

    def read_urls(self) -> List[str]:
        """Read URLs from CSV"""
        urls = []
        try:
            with open(self.input_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Support both 'URL' and 'url' column names
                    url = row.get('URL') or row.get('url', '')
                    url = url.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            logger.info(f"Loaded {len(urls)} URLs from {self.input_csv}")
        except Exception as e:
            logger.error(f"Failed to read URLs: {e}")
        return urls

    def save_to_csv(self):
        """Save scraped data to CSV"""
        if not self.scraped_data:
            logger.warning("No data to save")
            return

        try:
            with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.scraped_data)
            logger.info(f"Saved {len(self.scraped_data)} records to {self.output_csv}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")

    def generate_quality_report(self):
        """Generate and save quality report"""
        if not self.scraped_data:
            return

        quality_scores = [d.get('quality_score', 0) for d in self.scraped_data]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        report = {
            'total_records': len(self.scraped_data),
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'validation_failures': len(self.validation_failures),
            'success_rate': (self.successful_scrapes / (self.successful_scrapes + self.failed_scrapes) * 100) if (self.successful_scrapes + self.failed_scrapes) > 0 else 0,
            'average_quality_score': avg_quality,
            'quality_distribution': {
                'excellent_90+': sum(1 for s in quality_scores if s >= 90),
                'good_70-89': sum(1 for s in quality_scores if 70 <= s < 90),
                'fair_50-69': sum(1 for s in quality_scores if 50 <= s < 70),
                'poor_below_50': sum(1 for s in quality_scores if s < 50)
            }
        }

        try:
            with open(self.quality_report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Quality report saved to {self.quality_report_file}")

            # Print summary
            print(f"\n{'='*70}")
            print("DATA QUALITY REPORT")
            print(f"{'='*70}")
            print(f"Total Records: {report['total_records']}")
            print(f"Success Rate: {report['success_rate']:.1f}%")
            print(f"Average Quality Score: {report['average_quality_score']:.1f}/100")
            print(f"\nQuality Distribution:")
            print(f"  Excellent (90+): {report['quality_distribution']['excellent_90+']}")
            print(f"  Good (70-89): {report['quality_distribution']['good_70-89']}")
            print(f"  Fair (50-69): {report['quality_distribution']['fair_50-69']}")
            print(f"  Poor (<50): {report['quality_distribution']['poor_below_50']}")
            print(f"{'='*70}\n")

        except Exception as e:
            logger.error(f"Failed to save quality report: {e}")

    def run(self, limit: Optional[int] = None):
        """Main execution method"""
        print(f"\n{'='*70}")
        print("REAL ESTATE SCRAPER V3 - Production Edition")
        print(f"{'='*70}")

        # Initialize Playwright if not already initialized
        if self.use_playwright and not self.browser:
            self.init_playwright()

        urls = self.read_urls()
        if not urls:
            logger.error("No URLs to process")
            return

        if limit:
            urls = urls[:limit]
            print(f"Processing first {limit} URLs (test mode)")

        print(f"Total URLs to scrape: {len(urls)}")
        print(f"Playwright enabled: {self.use_playwright}")
        print(f"Pydantic validation: {PYDANTIC_AVAILABLE}")
        print(f"{'='*70}\n")

        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Scraping: {url}")
            data = self.scrape_url(url)

            if data:
                self.scraped_data.append(data)

            # Delay between requests
            if i < len(urls):
                self.random_delay(url)

        # Save results
        self.save_to_csv()
        self.generate_quality_report()


if __name__ == '__main__':
    # Test mode - scrape first 5 URLs
    with RealEstateScraperV3(
        input_csv='test_urls.csv',
        output_csv='real_estate_data_v3.csv',
        quality_report='quality_report_v3.json'
    ) as scraper:
        scraper.run(limit=5)
