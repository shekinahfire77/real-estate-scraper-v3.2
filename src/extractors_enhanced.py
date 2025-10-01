"""Enhanced data extraction for Redfin with more fields"""

import re
import logging
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class RedfinEnhancedExtractor:
    """Extract comprehensive property data from Redfin"""

    def extract_property_data(self, html: str, url: str) -> Dict[str, Any]:
        """Extract all available property data from Redfin HTML"""
        soup = BeautifulSoup(html, 'lxml')
        data = {'url': url}

        # Detect if rental or for sale
        page_type = self._detect_page_type(html)
        data['page_type'] = page_type

        # Core fields
        data['price'] = self._extract_price(soup)
        data['address'] = self._extract_address(soup)
        data['bedrooms'] = self._extract_bedrooms(soup)
        data['bathrooms'] = self._extract_bathrooms(soup)
        data['square_footage'] = self._extract_sqft(soup)

        # Additional fields
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
        data['price_per_sqft'] = self._calculate_price_per_sqft(data)

        # Rental-specific or sale-specific fields
        if page_type == 'rental':
            data['monthly_rent'] = data.get('price')  # For rentals, price IS rent
            data['security_deposit'] = self._extract_security_deposit(soup)
            data['lease_terms'] = self._extract_lease_terms(soup)
            data['pet_policy'] = self._extract_pet_policy(soup)
            data['availability_date'] = self._extract_availability_date(soup)
        else:  # for_sale
            data['hoa_fee'] = self._extract_hoa(soup)
            data['property_history'] = self._extract_property_history(soup)

        # Clean and normalize
        return self._clean_data(data)

    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property price"""
        selectors = [
            '[data-rf-test-id="abp-price"]',
            '.statsValue',
            '[class*="price"]'
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if '$' in text:
                    return text
        return None

    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property address"""
        selectors = [
            '[data-rf-test-id="abp-homeinfo-homeaddress"]',
            '.street-address',
            'h1[class*="address"]'
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                return elem.get_text(strip=True)
        return None

    def _extract_bedrooms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of bedrooms"""
        # Try stats section
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'bed' in text:
                return text

        # Fallback
        for sel in ['.bed', '[class*="bed"]', '.beds']:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if 'bed' in text.lower():
                    return text
        return None

    def _extract_bathrooms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract number of bathrooms"""
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'bath' in text:
                return text

        for sel in ['.bath', '[class*="bath"]', '.baths']:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if 'bath' in text.lower():
                    return text
        return None

    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract square footage"""
        stats = soup.select('[data-rf-test-id="abp-homeinfo-homemainstats"] div')
        for stat in stats:
            text = stat.get_text(strip=True).lower()
            if 'sq' in text or 'ft' in text:
                return text

        for sel in ['.sqft', '[class*="square"]']:
            elem = soup.select_one(sel)
            if elem:
                return elem.get_text(strip=True)
        return None

    def _extract_listing_id(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract listing ID from URL or page"""
        # From URL
        match = re.search(r'/home/(\d+)', url)
        if match:
            return match.group(1)

        # From meta tags
        meta = soup.find('meta', property='og:url')
        if meta and meta.get('content'):
            match = re.search(r'/home/(\d+)', meta['content'])
            if match:
                return match.group(1)
        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description"""
        selectors = [
            '[data-rf-test-id="abp-remarks"]',
            '.remarks',
            '.HomeDetails-description',
            '[class*="description"]'
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 50:  # Meaningful description
                    return text[:1000]  # Limit length
        return None

    def _extract_photos(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract photo URLs"""
        images = []

        # Try image gallery
        img_elems = soup.select('[data-rf-test-id^="MB-image"] img, .MediaBlock img, .media-carousel img')
        for img in img_elems[:15]:  # Max 15 photos
            src = img.get('src') or img.get('data-src')
            if src and ('http' in src or src.startswith('//')):
                if src.startswith('//'):
                    src = 'https:' + src
                images.append(src)

        return ','.join(images) if images else None

    def _extract_property_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property type (Single Family, Condo, etc.)"""
        selectors = [
            '[data-rf-test-id="abp-homeType"]',
            '.home-type',
            '[class*="property-type"]'
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                return elem.get_text(strip=True)
        return None

    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract year built"""
        # Look in facts section
        facts = soup.select('.facts-table .KeyDetails-value, [data-rf-test-id*="year"]')
        for fact in facts:
            text = fact.get_text(strip=True)
            match = re.search(r'\b(19|20)\d{2}\b', text)
            if match:
                try:
                    year = int(match.group())
                    if 1800 < year <= 2030:
                        return year
                except:
                    pass
        return None

    def _extract_lot_size(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract lot size"""
        selectors = [
            '[data-rf-test-id="abp-lotSize"]',
            '.lot-size',
            '[class*="lot"]'
        ]
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if 'acre' in text.lower() or 'sq ft' in text.lower():
                    return text
        return None

    def _extract_days_on_market(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract days on market"""
        text = soup.get_text()
        matches = re.findall(r'(\d+)\s+days?\s+on\s+(redfin|market)', text.lower())
        if matches:
            try:
                return int(matches[0][0])
            except:
                pass
        return None

    def _extract_hoa(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract HOA fees"""
        text = soup.get_text()
        matches = re.findall(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*/\s*(mo|month)', text.lower())
        if matches:
            try:
                return float(matches[0][0].replace(',', ''))
            except:
                pass
        return None

    def _extract_parking(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract parking information"""
        # Look for parking keywords
        text = soup.get_text().lower()
        if 'garage' in text or 'parking' in text or 'carport' in text:
            parking_match = re.search(r'(\d+)\s*car\s*(garage|parking)', text)
            if parking_match:
                return f"{parking_match.group(1)} car {parking_match.group(2)}"
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
        common_amenities = ['pool', 'fireplace', 'hardwood', 'granite', 'stainless steel',
                          'central air', 'heating', 'washer/dryer', 'dishwasher']
        for amenity in common_amenities:
            if amenity in text and amenity not in ' '.join(amenities).lower():
                amenities.append(amenity.title())

        return ', '.join(amenities[:20]) if amenities else None  # Max 20 amenities

    def _extract_schools(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract nearby schools"""
        schools = []
        school_elems = soup.select('[data-rf-test-id*="school"], .school-name')
        for elem in school_elems:
            text = elem.get_text(strip=True)
            if text and len(text) > 3:
                schools.append(text)

        return ', '.join(schools[:5]) if schools else None  # Max 5 schools

    def _calculate_price_per_sqft(self, data: Dict) -> Optional[float]:
        """Calculate price per square foot"""
        price = data.get('price')
        sqft = data.get('square_footage')

        if price and sqft:
            try:
                # Extract numbers
                price_val = float(re.sub(r'[^\d.]', '', str(price)))
                sqft_val = float(re.sub(r'[^\d.]', '', str(sqft)))
                if sqft_val > 0:
                    return round(price_val / sqft_val, 2)
            except:
                pass
        return None

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize extracted data"""

        # Clean price
        if data.get('price'):
            price_str = str(data['price']).replace(',', '').replace('$', '')
            match = re.search(r'\d+\.?\d*', price_str)
            if match:
                try:
                    data['price'] = float(match.group())
                except ValueError:
                    data['price'] = None
            else:
                data['price'] = None

        # Clean bedrooms
        if data.get('bedrooms'):
            match = re.search(r'(\d+)', str(data['bedrooms']))
            if match:
                try:
                    data['bedrooms'] = int(match.group(1))
                except ValueError:
                    data['bedrooms'] = None
            else:
                data['bedrooms'] = None

        # Clean bathrooms
        if data.get('bathrooms'):
            match = re.search(r'(\d+\.?\d*)', str(data['bathrooms']))
            if match:
                try:
                    data['bathrooms'] = float(match.group(1))
                except ValueError:
                    data['bathrooms'] = None
            else:
                data['bathrooms'] = None

        # Clean square footage
        if data.get('square_footage'):
            match = re.search(r'(\d+,?\d*)', str(data['square_footage']))
            if match:
                try:
                    data['square_footage'] = int(match.group(1).replace(',', ''))
                except ValueError:
                    data['square_footage'] = None
            else:
                data['square_footage'] = None

        return data

    def _detect_page_type(self, html: str) -> str:
        """Detect if page is for rental or for sale"""
        html_lower = html.lower()
        
        # Strong rental indicators
        rental_keywords = [
            'monthly rent', 'rent/month', 'rental application',
            'security deposit', 'lease term', 'pet deposit',
            'available to rent', 'for rent'
        ]
        
        # Strong sale indicators
        sale_keywords = [
            'for sale', 'list price', 'sold price',
            'mortgage calculator', 'down payment', 'purchase'
        ]
        
        rental_score = sum(1 for kw in rental_keywords if kw in html_lower)
        sale_score = sum(1 for kw in sale_keywords if kw in html_lower)
        
        # Check URL for rent vs buy
        if '/rent/' in html_lower:
            rental_score += 2
        if '/buy/' in html_lower or '/home/' in html_lower:
            sale_score += 2
        
        return 'rental' if rental_score > sale_score else 'for_sale'

    def _extract_security_deposit(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract security deposit for rentals"""
        text = soup.get_text().lower()
        matches = re.findall(r'security\s+deposit[:\s]*\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if matches:
            try:
                return float(matches[0].replace(',', ''))
            except:
                pass
        return None

    def _extract_lease_terms(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract lease terms for rentals"""
        text = soup.get_text()
        
        # Look for lease duration
        matches = re.findall(r'(\d+)\s*(month|year)\s*lease', text.lower())
        if matches:
            return f"{matches[0][0]} {matches[0][1]} lease"
        
        # Look for lease types
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
        text = soup.get_text()
        
        # Look for "Available" followed by date
        matches = re.findall(r'available\s+(\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-\d{1,2}-\d{2,4}|immediately|now)', text.lower())
        if matches:
            return matches[0].title()
        
        return None

    def _extract_property_history(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property history for sale properties"""
        # Look for price history
        history_elem = soup.select_one('[class*="price-history"], [data-rf-test-id*="history"]')
        if history_elem:
            text = history_elem.get_text(strip=True)
            if len(text) > 10:
                return text[:500]  # Limit length
        return None
