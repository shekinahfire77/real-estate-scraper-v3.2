"""Zillow property extractor"""

import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup, Tag

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class ZillowExtractor(BaseExtractor):
    """Extract property data from Zillow listings
    
    This is a stub implementation that will be enhanced with
    Zillow-specific extraction logic. Currently uses base class
    methods with Zillow-specific selectors.
    """
    
    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract property data from Zillow HTML
        
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
        
        # Zillow-specific selectors
        # These are common Zillow selectors - will need refinement
        price_selectors = [
            '[data-test="property-summary-price"]',
            '.price-text',
            'span[data-testid="price"]',
            '.list-card-price'
        ]
        
        address_selectors = [
            'h1[class*="address"]',
            '[data-test="property-summary-address"]',
            '.property-address',
            '[data-testid="address"]'
        ]
        
        # Core fields extraction
        data['price'] = self.extract_with_fallback(soup, price_selectors)
        data['address'] = self.extract_with_fallback(soup, address_selectors)
        
        # Extract from facts table
        facts = self._extract_facts_table(soup)
        data.update(facts)
        
        # Zillow-specific: Zestimate
        data['zestimate'] = self._extract_zestimate(soup)
        
        # Property details
        data['property_description'] = self._extract_description(soup)
        data['photos'] = self._extract_photos(soup)
        
        # Apply standard cleaning from base class
        return self.clean_all_fields(data)
    
    def _extract_facts_table(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract data from Zillow's facts table

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Dictionary with bedrooms, bathrooms, sqft
        """
        facts: Dict[str, Optional[str]] = {}
        
        # Try to find facts/features section
        fact_selectors: List[str] = [
            '.ds-bed-bath-living-area span',
            '.property-facts span',
            '[data-testid="bed-bath-item"]'
        ]

        for selector in fact_selectors:
            elements: List[Tag] = soup.select(selector)
            for elem in elements:
                text: str = elem.get_text(strip=True).lower()

                if 'bed' in text:
                    facts['bedrooms'] = text
                elif 'bath' in text:
                    facts['bathrooms'] = text
                elif 'sqft' in text or 'sq ft' in text:
                    facts['square_footage'] = text
        
        return facts
    
    def _extract_zestimate(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract Zillow's Zestimate value

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Zestimate value as float, or None
        """
        zestimate_selectors: List[str] = [
            '[data-testid="zestimate-value"]',
            '.zestimate-value',
            'span:contains("Zestimate")'
        ]

        text: Optional[str] = self.extract_with_fallback(soup, zestimate_selectors)
        if text:
            return self.clean_price(text)
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description from Zillow

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Property description text
        """
        desc_selectors: List[str] = [
            '[data-test="description"]',
            '.property-description',
            '[data-testid="description-text"]'
        ]

        text: Optional[str] = self.extract_with_fallback(soup, desc_selectors)
        if text and len(text) > 50:
            return text[:1000]  # Limit length
        return None
    
    def _extract_photos(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract photo URLs from Zillow gallery

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Comma-separated photo URLs
        """
        photo_selectors: List[str] = [
            '.media-carousel img',
            '[data-testid="photo"] img',
            '.photo-carousel img'
        ]

        images: List[str] = self.extract_images(soup, photo_selectors, max_images=15)
        return ','.join(images) if images else None
