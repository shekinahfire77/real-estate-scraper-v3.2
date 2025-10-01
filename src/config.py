"""Configuration settings for the real estate scraper"""

import os
from typing import Dict, Tuple
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# User-Agent rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# Site-specific concurrency settings
SITE_CONCURRENCY_SETTINGS: Dict[str, Dict] = {
    'zillow.com': {
        'delay_between_requests': (5, 10),
        'requests_per_minute': 6,
        'max_retries': 2,
        'max_concurrent': 1  # No concurrent requests for Zillow
    },
    'realtor.com': {
        'delay_between_requests': (3, 6),
        'requests_per_minute': 12,
        'max_retries': 3,
        'max_concurrent': 2
    },
    'redfin.com': {
        'delay_between_requests': (1, 2),
        'requests_per_minute': 30,
        'max_retries': 3,
        'max_concurrent': 5  # Redfin allows more concurrent requests
    },
    'apartments.com': {
        'delay_between_requests': (2, 4),
        'requests_per_minute': 20,
        'max_retries': 3,
        'max_concurrent': 3
    },
    'rent.com': {
        'delay_between_requests': (1, 3),
        'requests_per_minute': 25,
        'max_retries': 3,
        'max_concurrent': 4
    },
    'rentals.com': {
        'delay_between_requests': (1, 2),
        'requests_per_minute': 30,
        'max_retries': 2,
        'max_concurrent': 5
    },
    'trulia.com': {
        'delay_between_requests': (4, 8),
        'requests_per_minute': 10,
        'max_retries': 2,
        'max_concurrent': 1
    },
    'default': {
        'delay_between_requests': (2, 4),
        'requests_per_minute': 15,
        'max_retries': 3,
        'max_concurrent': 2
    }
}

# CSV headers for output
CSV_HEADERS = [
    'url', 'page_type', 'listing_id', 'price', 'address',
    'bedrooms', 'bathrooms', 'square_footage', 'property_description',
    'photos', 'days_on_market', 'property_history',
    'monthly_rent', 'security_deposit', 'lease_terms', 'amenities',
    'pet_policy', 'contact_info', 'availability_date', 'application_requirements',
    'lease_rate', 'property_size', 'zoning_info', 'parking',
    'building_specs', 'property_management',
    'scrape_method', 'has_api_data', 'quality_score'
]

# Scraping settings
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.3

# Quality score thresholds
QUALITY_THRESHOLDS = {
    'excellent': 90,
    'good': 70,
    'fair': 50,
    'poor': 0
}

# Async settings
DEFAULT_CONCURRENT_LIMIT = 5
ASYNC_TIMEOUT = 30
