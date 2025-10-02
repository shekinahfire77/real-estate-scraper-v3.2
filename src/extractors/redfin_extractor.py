"""Enhanced Redfin extractor using base class functionality"""

import re
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class RedfinEnhancedExtractor(BaseExtractor):
    """Extract comprehensive property data from Redfin
    
    Inherits common functionality from BaseExtractor and adds
    Redfin-specific extraction logic for additional fields.
    """
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Add Redfin-specific patterns to base patterns"""
        patterns = super()._compile_patterns()
        
        # Add Redfin-specific patterns
        patterns.update({
            'days_on_market': re.compile(r'(\d+)\s+days?\s+on\s+(?:redfin|market)', re.IGNORECASE),
            'hoa': re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*/\s*(?:mo|month)', re.IGNORECASE),
            'parking': re.compile(r'(\d+)\s*car\s*(garage|parking|carport)', re.IGNORECASE),
            'listing_id': re.compile(r'/home/(\d+)'),
            'security_deposit': re.compile(r'security\s+deposit[:\s]*\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE),
            'lease_term': re.compile(r'(\d+)\s*(month|year)\s*lease', re.IGNORECASE)
        })
        
        return patterns
    
    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract all available property data from Redfin HTML
        
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
        
        # Extract core fields using base class methods
        data['price'] = self._extract_price(soup)
        data['address'] = self._extract_address(soup)
        data['bedrooms'] = self._extract_bedrooms(soup)
        data['bathrooms'] = self._extract_bathrooms(soup)
        data['square_footage'] = self._extract_sqft(soup)
        
        # Extract additional fields
        data['listing_id'] = self._extract_listing_id(soup, url)
        data['property_description'] = self._extract_description(soup)
        data['photos'] = self._extract_photos(soup)
        data['property_type'] = self._extract_property_type(soup)
        data['year_built'] = self._extract_year_built(soup)
        data['lot_size'] = self._extract_lot_size(soup)
        data['days_on_market'] = self._extract_days_on_market(soup)
        data['parking'] = self._extract_parking(soup)
        data['amenities'] = self._extract_amenities(soup)
        data['schools'] = self._extract_schools(soup)
        
        # Handle rental vs sale specific fields
        if data['page_type'] == 'rental':
            data['monthly_rent'] = data.get('price')  # For rentals, price IS rent
            data['security_deposit'] = self._extract_security_deposit(soup)
            data['lease_terms'] = self._extract_lease_terms(soup)
            data['pet_policy'] = self._extract_pet_policy(soup)
            data['availability_date'] = self._extract_availability_date(soup)
        else:  # for_sale
            data['hoa_fee'] = self._extract_hoa(soup)
            data['property_history'] = self._extract_property_history(soup)
        
        # Apply standard cleaning from base class
        return self.clean_all_fields(data)
    
    # ============== Redfin-Specific Extraction Methods ==============
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property price using Redfin selectors"""
        selectors = [
            '[data-rf-test-id="abp-price"]',
            '.statsValue',
            '[class*="price"]'
        ]
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property address"""
        selectors = [
            '[data-rf-test-id="abp-homeinfo-homeaddress"]',
            '.street-address',
            'h1[class*="address"]'
        ]
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_bedrooms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of bedrooms from Redfin stats section"""
        # Try stats section first
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'bed' in text:
                return text
        
        # Fallback to other selectors
        selectors = ['.bed', '[class*="bed"]', '.beds']
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of bathrooms from Redfin stats section"""
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'bath' in text:
                return text
        
        selectors = ['.bath', '[class*="bath"]', '.baths']
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage from Redfin stats section"""
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'sq' in text or 'ft' in text:
                return text
        
        selectors = ['.sqft', '[class*="square"]']
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_listing_id(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract Redfin listing ID from URL or page"""
        # Try URL first
        match = self._patterns['listing_id'].search(url)
        if match:
            try:
                return match.group(1)
            except (IndexError, AttributeError) as e:
                logger.debug(f"Listing ID regex matched URL but group extraction failed: {e}")

        # Try meta tags
        meta = soup.find('meta', property='og:url')
        if meta and meta.get('content'):
            match = self._patterns['listing_id'].search(meta['content'])
            if match:
                try:
                    return match.group(1)
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Listing ID regex matched meta tag but group extraction failed: {e}")
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description"""
        selectors = [
            '[data-rf-test-id="abp-remarks"]',
            '.remarks',
            '.HomeDetails-description',
            '[class*="description"]'
        ]
        
        text = self.extract_with_fallback(soup, selectors)
        if text and len(text) > 50:  # Ensure meaningful description
            return text[:1000]  # Limit length
        return None
    
    def _extract_photos(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract photo URLs from Redfin gallery"""
        selectors = [
            '[data-rf-test-id^="MB-image"] img',
            '.MediaBlock img',
            '.media-carousel img'
        ]
        
        images = self.extract_images(soup, selectors, max_images=15)
        return ','.join(images) if images else None
    
    def _extract_property_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property type (Single Family, Condo, etc.)"""
        selectors = [
            '[data-rf-test-id="abp-homeType"]',
            '.home-type',
            '[class*="property-type"]'
        ]
        return self.extract_with_fallback(soup, selectors)
    
    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract year built from Redfin facts section"""
        # Look in facts section
        facts = soup.select('.facts-table .KeyDetails-value, [data-rf-test-id*="year"]')
        for fact in facts:
            text = fact.get_text(strip=True)
            if self._patterns['year'].search(text):
                return text

        # Look in full text
        text = soup.get_text()
        match = self._patterns['year'].search(text)
        if match:
            try:
                return match.group()
            except (IndexError, AttributeError) as e:
                logger.debug(f"Year built regex matched but group extraction failed: {e}")
        return None
    
    def _extract_lot_size(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract lot size"""
        selectors = [
            '[data-rf-test-id="abp-lotSize"]',
            '.lot-size',
            '[class*="lot"]'
        ]
        
        text = self.extract_with_fallback(soup, selectors)
        if text and ('acre' in text.lower() or 'sq ft' in text.lower()):
            return text
        return None
    
    def _extract_days_on_market(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract days on market"""
        text = soup.get_text()
        match = self._patterns['days_on_market'].search(text)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, AttributeError, IndexError) as e:
                logger.debug(f"Days on market regex matched but group extraction failed: {e}")
                pass
        return None
    
    def _extract_hoa(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract HOA fees for sale properties"""
        text = soup.get_text()
        match = self._patterns['hoa'].search(text)
        if match:
            try:
                return self.clean_price(match.group(1))
            except (IndexError, AttributeError) as e:
                logger.debug(f"HOA regex matched but group extraction failed: {e}")
                return None
        return None
    
    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information"""
        text = soup.get_text()
        match = self._patterns['parking'].search(text)
        if match:
            try:
                # Extract number and type (e.g., "2 car garage")
                return f"{match.group(1)} car {match.group(2)}"
            except IndexError:
                # Fallback if groups don't exist
                logger.debug(f"Parking regex matched but groups missing: {match.group()}")
                return "Parking available"

        # Check for parking keywords
        if 'garage' in text.lower() or 'parking' in text.lower():
            return "Parking available"
        return None
    
    def _extract_amenities(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property amenities"""
        amenities = []
        
        # Look for amenity lists
        amenity_elems = soup.select('.amenity-item, .feature-item, [class*="amenity"]')
        for elem in amenity_elems:
            text = elem.get_text(strip=True)
            if text and len(text) < 100:
                amenities.append(text)
        
        # Look for common amenities in text
        text = soup.get_text().lower()
        common_amenities = [
            'pool', 'fireplace', 'hardwood', 'granite', 'stainless steel',
            'central air', 'heating', 'washer/dryer', 'dishwasher', 'patio',
            'deck', 'balcony', 'gym', 'spa', 'garden'
        ]
        
        for amenity in common_amenities:
            if amenity in text and amenity not in ' '.join(amenities).lower():
                amenities.append(amenity.title())
        
        return ', '.join(amenities[:20]) if amenities else None  # Max 20
    
    def _extract_schools(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract nearby schools information"""
        schools = []
        school_elems = soup.select('[data-rf-test-id*="school"], .school-name')
        
        for elem in school_elems:
            text = elem.get_text(strip=True)
            if text and len(text) > 3:
                schools.append(text)
        
        return ', '.join(schools[:5]) if schools else None  # Max 5 schools
    
    # ============== Rental-Specific Methods ==============
    
    def _extract_security_deposit(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract security deposit for rentals"""
        text = soup.get_text()
        match = self._patterns['security_deposit'].search(text)
        if match:
            try:
                return self.clean_price(match.group(1))
            except (IndexError, AttributeError) as e:
                logger.debug(f"Security deposit regex matched but group extraction failed: {e}")
                return None
        return None
    
    def _extract_lease_terms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract lease terms for rentals"""
        text = soup.get_text()

        match = self._patterns['lease_term'].search(text)
        if match:
            try:
                return f"{match.group(1)} {match.group(2)} lease"
            except (IndexError, AttributeError) as e:
                logger.debug(f"Lease term regex matched but group extraction failed: {e}")
                # Fallback to generic lease info
                return "Lease available"

        # Check for other lease types
        if 'month-to-month' in text.lower():
            return "Month-to-month"
        if 'short term' in text.lower():
            return "Short term"

        return None
    
    def _extract_pet_policy(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract pet policy for rentals"""
        text = soup.get_text().lower()
        
        if 'pets allowed' in text or 'pet friendly' in text:
            return "Pets allowed"
        elif 'no pets' in text or 'pets not allowed' in text:
            return "No pets"
        elif 'cats ok' in text or 'dogs ok' in text:
            policy = []
            if 'cats ok' in text or 'cats allowed' in text:
                policy.append('Cats OK')
            if 'dogs ok' in text or 'dogs allowed' in text:
                policy.append('Dogs OK')
            return ', '.join(policy)
        
        return None
    
    def _extract_availability_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract availability date for rentals"""
        text = soup.get_text().lower()
        
        # Look for "Available" followed by date
        patterns = [
            r'available\s+(\d{1,2}/\d{1,2}/\d{2,4})',
            r'available\s+(\d{1,2}-\d{1,2}-\d{2,4})',
            r'available\s+(immediately|now)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return match.group(1).title()
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Availability date regex matched but group extraction failed: {e}")

        return None
    
    def _extract_property_history(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property history for sale properties"""
        history_elem = soup.select_one('[class*="price-history"], [data-rf-test-id*="history"]')
        if history_elem:
            text = history_elem.get_text(strip=True)
            if len(text) > 10:
                return text[:500]  # Limit length
        return None
