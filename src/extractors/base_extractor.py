"""Base extractor class with common functionality for all site extractors"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Base class for all property data extractors
    
    Provides common cleaning and extraction utilities that all site-specific
    extractors can use. Subclasses must implement extract_property_data.
    """
    
    def __init__(self):
        """Initialize extractor with compiled regex patterns"""
        self._patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile common regex patterns for reuse
        
        Subclasses can override to add site-specific patterns
        """
        return {
            'price': re.compile(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
            'bedrooms': re.compile(r'(\d+)\s*(?:bed|br|bedroom)', re.IGNORECASE),
            'bathrooms': re.compile(r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)', re.IGNORECASE),
            'sqft': re.compile(r'(\d{1,3}(?:,\d{3})*)\s*(?:sq\.?\s*ft\.?|square\s*feet)', re.IGNORECASE),
            'year': re.compile(r'\b(19|20)\d{2}\b'),
            'lot_size': re.compile(r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:acre|sq\.?\s*ft\.?)', re.IGNORECASE),
            'numeric': re.compile(r'(\d+(?:,\d{3})*(?:\.\d+)?)')
        }
    
    @abstractmethod
    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract property data from HTML
        
        Must be implemented by each site-specific extractor
        
        Args:
            html: Raw HTML content
            url: Source URL for the property
            
        Returns:
            Dictionary of extracted property data
        """
        pass
    
    # ============== Common Extraction Methods ==============
    
    def extract_with_fallback(self, soup: BeautifulSoup, 
                            selectors: List[str]) -> Optional[str]:
        """Try multiple CSS selectors until one works
        
        Args:
            soup: BeautifulSoup parsed HTML
            selectors: List of CSS selectors to try
            
        Returns:
            Text content from first matching selector, or None
        """
        for selector in selectors:
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
                      selectors: List[str], 
                      max_images: int = 15) -> List[str]:
        """Extract image URLs from page
        
        Args:
            soup: BeautifulSoup parsed HTML
            selectors: List of CSS selectors for images
            max_images: Maximum number of images to extract
            
        Returns:
            List of image URLs
        """
        images = []
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements[:max_images]:
                    # Try multiple image source attributes
                    src = (elem.get('src') or 
                          elem.get('data-src') or 
                          elem.get('data-lazy') or 
                          elem.get('data-original'))
                    
                    if src:
                        # Ensure absolute URL
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            # Need base URL - extract from page
                            base_url = self._get_base_url(soup)
                            if base_url:
                                src = base_url + src
                        
                        if 'http' in src:
                            images.append(src)
                            if len(images) >= max_images:
                                break
            except Exception as e:
                logger.debug(f"Image selector {selector} failed: {e}")
                continue
                
            if len(images) >= max_images:
                break
        
        return images
    
    def extract_text_with_patterns(self, soup: BeautifulSoup, 
                                  selectors: List[str],
                                  patterns: List[str]) -> Optional[str]:
        """Extract text using selectors, then apply regex patterns
        
        Args:
            soup: BeautifulSoup parsed HTML
            selectors: CSS selectors to find text
            patterns: Regex patterns to extract from text
            
        Returns:
            Extracted text matching pattern, or None
        """
        text = self.extract_with_fallback(soup, selectors)
        if not text:
            return None
            
        for pattern in patterns:
            try:
                if isinstance(pattern, str):
                    match = re.search(pattern, text, re.IGNORECASE)
                else:
                    match = pattern.search(text)
                    
                if match:
                    return match.group(1) if match.groups() else match.group()
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                
        return None
    
    # ============== Common Cleaning Methods ==============
    
    def clean_price(self, price_str: Optional[str]) -> Optional[float]:
        """Clean and convert price string to float
        
        Args:
            price_str: Raw price string (e.g., "$450,000")
            
        Returns:
            Cleaned price as float, or None if invalid
        """
        if not price_str:
            return None
            
        try:
            # Remove currency symbols and whitespace
            cleaned = re.sub(r'[$,\s]', '', str(price_str))
            
            # Extract numeric value
            match = self._patterns['numeric'].search(cleaned)
            if match:
                return float(match.group(1).replace(',', ''))
        except (ValueError, AttributeError) as e:
            logger.debug(f"Price cleaning failed for '{price_str}': {e}")
            
        return None
    
    def clean_numeric(self, value: Optional[str], 
                     as_int: bool = True) -> Optional[float]:
        """Clean and convert numeric string to int or float
        
        Args:
            value: Raw numeric string
            as_int: If True, convert to int; else float
            
        Returns:
            Cleaned numeric value, or None if invalid
        """
        if not value:
            return None
            
        try:
            # Remove commas and extract number
            cleaned = str(value).replace(',', '')
            match = self._patterns['numeric'].search(cleaned)
            
            if match:
                num = float(match.group(1).replace(',', ''))
                return int(num) if as_int else num
        except (ValueError, AttributeError) as e:
            logger.debug(f"Numeric cleaning failed for '{value}': {e}")
            
        return None
    
    def clean_bedrooms(self, bed_str: Optional[str]) -> Optional[int]:
        """Extract bedroom count from string
        
        Args:
            bed_str: Raw bedroom string (e.g., "3 beds")
            
        Returns:
            Number of bedrooms as int, or None
        """
        if not bed_str:
            return None
            
        match = self._patterns['bedrooms'].search(str(bed_str))
        if match:
            try:
                beds = int(match.group(1))
                # Sanity check
                if 0 <= beds <= 20:
                    return beds
            except (ValueError, AttributeError):
                pass
                
        return None
    
    def clean_bathrooms(self, bath_str: Optional[str]) -> Optional[float]:
        """Extract bathroom count from string
        
        Args:
            bath_str: Raw bathroom string (e.g., "2.5 baths")
            
        Returns:
            Number of bathrooms as float, or None
        """
        if not bath_str:
            return None
            
        match = self._patterns['bathrooms'].search(str(bath_str))
        if match:
            try:
                baths = float(match.group(1))
                # Sanity check
                if 0 <= baths <= 10:
                    return baths
            except (ValueError, AttributeError):
                pass
                
        return None
    
    def clean_sqft(self, sqft_str: Optional[str]) -> Optional[int]:
        """Extract square footage from string
        
        Args:
            sqft_str: Raw square footage string (e.g., "1,500 sq ft")
            
        Returns:
            Square footage as int, or None
        """
        if not sqft_str:
            return None
            
        match = self._patterns['sqft'].search(str(sqft_str))
        if match:
            try:
                sqft = int(match.group(1).replace(',', ''))
                # Sanity check
                if 100 <= sqft <= 100000:
                    return sqft
            except (ValueError, AttributeError):
                pass
                
        return None
    
    def clean_year_built(self, year_str: Optional[str]) -> Optional[int]:
        """Extract year built from string
        
        Args:
            year_str: Raw year string
            
        Returns:
            Year as int, or None
        """
        if not year_str:
            return None
            
        match = self._patterns['year'].search(str(year_str))
        if match:
            try:
                year = int(match.group())
                # Sanity check
                if 1800 <= year <= 2030:
                    return year
            except (ValueError, AttributeError):
                pass
                
        return None
    
    def clean_all_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply standard cleaning to common fields
        
        Args:
            data: Raw extracted data
            
        Returns:
            Cleaned data dictionary
        """
        # Clean standard fields if they exist
        if 'price' in data:
            data['price'] = self.clean_price(data['price'])
            
        if 'bedrooms' in data:
            data['bedrooms'] = self.clean_bedrooms(data['bedrooms'])
            
        if 'bathrooms' in data:
            data['bathrooms'] = self.clean_bathrooms(data['bathrooms'])
            
        if 'square_footage' in data:
            data['square_footage'] = self.clean_sqft(data['square_footage'])
            
        if 'year_built' in data:
            data['year_built'] = self.clean_year_built(data['year_built'])
            
        if 'lot_size' in data and data['lot_size']:
            # Just clean numeric part, keep units in string if needed
            data['lot_size'] = str(data['lot_size'])
            
        # Calculate price per sqft if possible
        if data.get('price') and data.get('square_footage'):
            try:
                data['price_per_sqft'] = round(
                    data['price'] / data['square_footage'], 2
                )
            except (TypeError, ZeroDivisionError):
                data['price_per_sqft'] = None
                
        return data
    
    # ============== Helper Methods ==============
    
    def _get_base_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract base URL from page for relative URL resolution
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            Base URL, or None
        """
        # Try base tag
        base_tag = soup.find('base')
        if base_tag and base_tag.get('href'):
            return base_tag['href'].rstrip('/')
            
        # Try og:url meta tag
        meta_url = soup.find('meta', property='og:url')
        if meta_url and meta_url.get('content'):
            url = meta_url['content']
            # Extract protocol and domain
            match = re.match(r'(https?://[^/]+)', url)
            if match:
                return match.group(1)
                
        return None
    
    def detect_page_type(self, html: str, url: str) -> str:
        """Detect if page is for rental or for sale
        
        Args:
            html: Raw HTML content
            url: Page URL
            
        Returns:
            'rental' or 'for_sale'
        """
        html_lower = html.lower()
        url_lower = url.lower()
        
        # Strong rental indicators
        rental_keywords = [
            'monthly rent', 'rent/month', 'rental application',
            'security deposit', 'lease term', 'pet deposit',
            'available to rent', 'for rent', '/rent/'
        ]
        
        # Strong sale indicators
        sale_keywords = [
            'for sale', 'list price', 'sold price',
            'mortgage calculator', 'down payment', 'purchase',
            '/buy/', '/home/'
        ]
        
        rental_score = sum(1 for kw in rental_keywords 
                          if kw in html_lower or kw in url_lower)
        sale_score = sum(1 for kw in sale_keywords 
                        if kw in html_lower or kw in url_lower)
        
        return 'rental' if rental_score > sale_score else 'for_sale'
