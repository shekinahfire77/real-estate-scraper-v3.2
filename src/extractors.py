"""Data extraction utilities"""

import re
import logging
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

from .selectors import get_selectors_for_site

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extract property data from HTML"""
    
    def __init__(self, domain: str):
        """Initialize with domain-specific selectors"""
        self.domain = domain
        self.selectors = get_selectors_for_site(domain)
    
    def extract_with_fallback(self, soup: BeautifulSoup, 
                            selector_list: List[str]) -> Optional[str]:
        """Try multiple selectors until one works"""
        for selector in selector_list:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 0:
                        return text
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        return None
    
    def extract_images(self, soup: BeautifulSoup, 
                      selector_list: List[str], 
                      max_images: int = 10) -> List[str]:
        """Extract image URLs"""
        images = []
        
        for selector in selector_list:
            try:
                elements = soup.select(selector)
                for elem in elements[:max_images]:
                    src = elem.get('src') or elem.get('data-src') or elem.get('data-lazy')
                    if src and 'http' in src:
                        images.append(src)
                        if len(images) >= max_images:
                            break
            except Exception as e:
                logger.debug(f"Image selector {selector} failed: {e}")
                continue
                
            if len(images) >= max_images:
                break
        
        return images
    
    def extract_property_data(self, html: str) -> Dict[str, Any]:
        """Extract all property data from HTML"""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Extract text fields
        data['price'] = self.extract_with_fallback(soup, self.selectors.get('price', []))
        data['address'] = self.extract_with_fallback(soup, self.selectors.get('address', []))
        data['bedrooms'] = self.extract_with_fallback(soup, self.selectors.get('beds', []))
        data['bathrooms'] = self.extract_with_fallback(soup, self.selectors.get('baths', []))
        data['square_footage'] = self.extract_with_fallback(soup, self.selectors.get('sqft', []))
        data['listing_id'] = self.extract_with_fallback(soup, self.selectors.get('listing_id', []))
        
        # Extract images
        images = self.extract_images(soup, self.selectors.get('photos', []))
        if images:
            data['photos'] = ','.join(images)
        
        # Clean and normalize data
        data = self.clean_data(data)
        
        return data
    
    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize extracted data"""
        
        # Clean price
        if data.get('price'):
            price_str = data['price'].replace(',', '').replace('$', '')
            match = re.search(r'\d+\.?\d*', price_str)
            if match:
                try:
                    data['price'] = float(match.group())
                except ValueError:
                    pass
        
        # Clean bedrooms
        if data.get('bedrooms'):
            match = re.search(r'\d+', str(data['bedrooms']))
            if match:
                try:
                    data['bedrooms'] = int(match.group())
                except ValueError:
                    pass
        
        # Clean bathrooms
        if data.get('bathrooms'):
            match = re.search(r'\d+\.?\d*', str(data['bathrooms']))
            if match:
                try:
                    data['bathrooms'] = float(match.group())
                except ValueError:
                    pass
        
        # Clean square footage
        if data.get('square_footage'):
            sqft_str = str(data['square_footage']).replace(',', '')
            match = re.search(r'\d+', sqft_str)
            if match:
                try:
                    data['square_footage'] = int(match.group())
                except ValueError:
                    pass
        
        return data
    
    def extract_with_regex(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract data using regex patterns"""
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1) if match.groups() else match.group()
            except Exception as e:
                logger.debug(f"Regex pattern {pattern} failed: {e}")
                continue
        return None
