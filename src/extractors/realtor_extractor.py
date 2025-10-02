"""Realtor.com property extractor"""

import logging
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup, Tag

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class RealtorExtractor(BaseExtractor):
    """Extract property data from Realtor.com listings
    
    This is a stub implementation that will be enhanced with
    Realtor.com-specific extraction logic. Currently uses base
    class methods with Realtor-specific selectors.
    """
    
    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract property data from Realtor.com HTML
        
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
        
        # Realtor.com-specific selectors
        price_selectors = [
            '[data-testid="list-price"]',
            '.ldp-header-price span',
            '.Price__Component',
            '[itemprop="price"]'
        ]
        
        address_selectors = [
            '[data-testid="address"]',
            '.ldp-header-address h1',
            '[itemprop="streetAddress"]',
            '.property-address'
        ]
        
        # Core fields extraction
        data['price'] = self.extract_with_fallback(soup, price_selectors)
        data['address'] = self.extract_with_fallback(soup, address_selectors)
        
        # Extract from property meta section
        meta_data = self._extract_meta_section(soup)
        data.update(meta_data)
        
        # Property details
        data['property_description'] = self._extract_description(soup)
        data['photos'] = self._extract_photos(soup)
        data['property_type'] = self._extract_property_type(soup)
        data['year_built'] = self._extract_year_built(soup)
        
        # Realtor-specific: listing details
        data['listing_id'] = self._extract_listing_id(url)
        data['days_on_market'] = self._extract_days_on_market(soup)
        
        # Apply standard cleaning from base class
        return self.clean_all_fields(data)
    
    def _extract_meta_section(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract data from Realtor.com's property meta section

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Dictionary with bedrooms, bathrooms, sqft
        """
        meta: Dict[str, Optional[str]] = {}
        
        # Try to find meta/key facts section
        meta_selectors: List[str] = [
            '.property-meta li',
            '[data-testid="property-meta"] span',
            '.key-fact',
            '.summary-table span'
        ]

        for selector in meta_selectors:
            elements: List[Tag] = soup.select(selector)
            for elem in elements:
                text: str = elem.get_text(strip=True).lower()
                
                if 'bed' in text:
                    meta['bedrooms'] = text
                elif 'bath' in text:
                    meta['bathrooms'] = text
                elif 'sqft' in text or 'sq ft' in text:
                    meta['square_footage'] = text
                elif 'acre' in text:
                    meta['lot_size'] = elem.get_text(strip=True)
        
        return meta
    
    def _extract_property_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property type from Realtor.com

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Property type (e.g., Single Family, Condo)
        """
        type_selectors: List[str] = [
            '[data-testid="property-type"]',
            '.property-type',
            '[itemprop="propertyType"]'
        ]

        return self.extract_with_fallback(soup, type_selectors)
    
    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract year built from Realtor.com

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Year built as string
        """
        # Look for year in details section
        details: List[Tag] = soup.select('.property-details span, .key-details span')
        
        for detail in details:
            text: str = detail.get_text(strip=True)
            if 'built' in text.lower():
                # Next element might have the year
                next_elem: Optional[Tag] = detail.find_next_sibling()
                if next_elem:
                    return next_elem.get_text(strip=True)
                # Or it might be in the same element
                if self._patterns['year'].search(text):
                    return text
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description from Realtor.com

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Property description text
        """
        desc_selectors: List[str] = [
            '[data-testid="description"]',
            '.property-description',
            '[itemprop="description"]',
            '.listing-description'
        ]

        text: Optional[str] = self.extract_with_fallback(soup, desc_selectors)
        if text and len(text) > 50:
            return text[:1000]  # Limit length
        return None
    
    def _extract_photos(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract photo URLs from Realtor.com gallery

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Comma-separated photo URLs
        """
        photo_selectors: List[str] = [
            '.photo-carousel img',
            '[data-testid="photo"] img',
            '.gallery-image img',
            '[itemprop="photo"]'
        ]

        images: List[str] = self.extract_images(soup, photo_selectors, max_images=15)
        return ','.join(images) if images else None
    
    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from Realtor.com URL

        Args:
            url: Property URL

        Returns:
            Listing ID or None
        """
        # Realtor URLs often have format: /realestateandhomes-detail/.../{listing_id}
        match: Optional[re.Match] = re.search(r'/([A-Z0-9]+)(?:\?|$)', url)
        if match:
            return match.group(1)
        return None
    
    def _extract_days_on_market(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract days on market from Realtor.com

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Days on market as integer
        """
        # Look for days on market text
        text: str = soup.get_text().lower()

        patterns: List[str] = [
            r'(\d+)\s*days?\s*on\s*realtor',
            r'(\d+)\s*days?\s*on\s*market',
            r'listed\s*(\d+)\s*days?\s*ago'
        ]

        for pattern in patterns:
            match: Optional[re.Match] = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, AttributeError):
                    pass
        
        return None
