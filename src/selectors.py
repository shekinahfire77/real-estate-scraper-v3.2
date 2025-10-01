"""Site-specific CSS selectors for data extraction"""

from typing import Dict, List

# Zillow selectors with fallbacks
ZILLOW_SELECTORS: Dict[str, List[str]] = {
    'price': [
        '[data-testid="price"]',
        'span[data-test="property-card-price"]',
        '.list-card-price',
        '.property-card-price'
    ],
    'address': [
        '[data-testid="property-card-addr"]',
        'address',
        '.list-card-addr',
        '.property-card-address'
    ],
    'beds': [
        '[data-testid="property-card-bed"]',
        'span[data-test="property-card-beds"]',
        '.property-card-bed'
    ],
    'baths': [
        '[data-testid="property-card-bath"]',
        'span[data-test="property-card-baths"]',
        '.property-card-bath'
    ],
    'sqft': [
        '[data-testid="property-card-sqft"]',
        'span[data-test="property-card-sqft"]',
        '.property-card-sqft'
    ],
    'listing_id': [
        '[data-zpid]',
        '[data-listing-id]'
    ],
    'photos': [
        'picture img[src*="photos.zillowstatic.com"]',
        '.media-stream img',
        '.property-card-img img'
    ]
}

# Realtor.com selectors with fallbacks
REALTOR_SELECTORS: Dict[str, List[str]] = {
    'price': [
        '[data-testid="card-price"]',
        '.price',
        '[class*="price"]',
        '.card-price'
    ],
    'address': [
        '[data-testid="card-address"]',
        'address',
        '.card-address',
        '[class*="address"]'
    ],
    'beds': [
        '[data-testid="meta-beds"]',
        'li[data-label="bed"]',
        '.beds-label'
    ],
    'baths': [
        '[data-testid="meta-baths"]',
        'li[data-label="bath"]',
        '.baths-label'
    ],
    'sqft': [
        '[data-testid="meta-sqft"]',
        'li[data-label="sqft"]',
        '.sqft-label'
    ],
    'listing_id': [
        '[data-listingid]',
        '[data-testid="property-card"]',
        '[data-property-id]'
    ],
    'photos': [
        '.photo img',
        '[data-testid="property-photo"]',
        '.property-photo img'
    ]
}

# Redfin selectors
REDFIN_SELECTORS: Dict[str, List[str]] = {
    'price': [
        '.homecardV2Price',
        '.bp-Homecard__Price',
        '[data-rf-test-id="abp-price"]',
        '.price'
    ],
    'address': [
        '.bp-Homecard__Address',
        '.homecard-address',
        '[data-rf-test-id="abp-address"]',
        'address'
    ],
    'beds': [
        '.bp-Homecard__Stats--beds',
        '[data-rf-test-id="abp-beds"]',
        '.beds'
    ],
    'baths': [
        '.bp-Homecard__Stats--baths',
        '[data-rf-test-id="abp-baths"]',
        '.baths'
    ],
    'sqft': [
        '.bp-Homecard__Stats--sqft',
        '[data-rf-test-id="abp-sqft"]',
        '.sqft'
    ],
    'listing_id': [
        '[data-rf-test-id="property-card"]',
        '[data-listing-id]'
    ],
    'photos': [
        '.bp-Homecard__Photo img',
        '.homecard-photo img',
        '[data-rf-test-id="abp-photo"] img'
    ]
}

# Generic selectors for unknown sites
GENERIC_SELECTORS: Dict[str, List[str]] = {
    'price': [
        '.price',
        '[class*="price"]',
        '[data-price]',
        '.listing-price',
        '.property-price'
    ],
    'address': [
        'address',
        '.address',
        '[class*="address"]',
        '.property-address',
        '.listing-address'
    ],
    'beds': [
        '[class*="bed"]',
        '.beds',
        '.bedrooms',
        '[data-beds]'
    ],
    'baths': [
        '[class*="bath"]',
        '.baths',
        '.bathrooms',
        '[data-baths]'
    ],
    'sqft': [
        '[class*="sqft"]',
        '[class*="square"]',
        '.square-feet',
        '[data-sqft]'
    ],
    'listing_id': [
        '[data-listing-id]',
        '[data-property-id]',
        '[data-id]'
    ],
    'photos': [
        '.property-photo img',
        '.listing-photo img',
        '.gallery img',
        'img[class*="property"]',
        'img[class*="listing"]'
    ]
}


def get_selectors_for_site(domain: str) -> Dict[str, List[str]]:
    """Get the appropriate selectors for a given domain"""
    
    selectors_map = {
        'zillow.com': ZILLOW_SELECTORS,
        'realtor.com': REALTOR_SELECTORS,
        'redfin.com': REDFIN_SELECTORS,
    }
    
    # Check if domain matches any known site
    for site, selectors in selectors_map.items():
        if site in domain:
            return selectors
    
    # Return generic selectors for unknown sites
    return GENERIC_SELECTORS
