"""Generic data extractor using base class functionality"""

import logging
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_extractor import BaseExtractor
from ..selectors import get_selectors_for_site

logger = logging.getLogger(__name__)


class GenericExtractor(BaseExtractor):
    """Generic extractor for any site using CSS selectors
    
    This extractor uses site-specific CSS selectors from the selectors
    module and applies the base class cleaning methods. It serves as
    a fallback for sites without dedicated extractors.
    """
    
    def __init__(self, domain: str):
        """Initialize with domain-specific selectors
        
        Args:
            domain: Website domain (e.g., 'zillow.com')
        """
        super().__init__()
        self.domain = domain
        self.selectors = get_selectors_for_site(domain)
    
    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract property data using generic selectors
        
        Args:
            html: Raw HTML content
            url: Source URL
            
        Returns:
            Dictionary of extracted and cleaned property data
        """
        soup = BeautifulSoup(html, 'lxml')
        data = {'url': url}
        
        # Detect page type
        data['page_type'] = self.detect_page_type(html, url)
        
        # Extract core fields using selectors
        data['price'] = self.extract_with_fallback(
            soup, self.selectors.get('price', [])
        )
        data['address'] = self.extract_with_fallback(
            soup, self.selectors.get('address', [])
        )
        data['bedrooms'] = self.extract_with_fallback(
            soup, self.selectors.get('beds', [])
        )
        data['bathrooms'] = self.extract_with_fallback(
            soup, self.selectors.get('baths', [])
        )
        data['square_footage'] = self.extract_with_fallback(
            soup, self.selectors.get('sqft', [])
        )
        data['listing_id'] = self.extract_with_fallback(
            soup, self.selectors.get('listing_id', [])
        )
        
        # Extract property type if selectors available
        if 'property_type' in self.selectors:
            data['property_type'] = self.extract_with_fallback(
                soup, self.selectors['property_type']
            )
        
        # Extract year built if selectors available
        if 'year_built' in self.selectors:
            data['year_built'] = self.extract_with_fallback(
                soup, self.selectors['year_built']
            )
        
        # Extract lot size if selectors available
        if 'lot_size' in self.selectors:
            data['lot_size'] = self.extract_with_fallback(
                soup, self.selectors['lot_size']
            )
        
        # Extract description if selectors available
        if 'description' in self.selectors:
            desc = self.extract_with_fallback(
                soup, self.selectors['description']
            )
            if desc and len(desc) > 50:  # Ensure meaningful description
                data['property_description'] = desc[:1000]
        
        # Extract images
        if 'photos' in self.selectors:
            images = self.extract_images(
                soup, self.selectors['photos'], max_images=10
            )
            if images:
                data['photos'] = ','.join(images)
        
        # Apply standard cleaning from base class
        return self.clean_all_fields(data)


class DataExtractor(GenericExtractor):
    """Backward compatibility alias for GenericExtractor
    
    This maintains compatibility with existing code that uses DataExtractor.
    """
    pass
