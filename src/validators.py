"""Data validation and quality scoring"""

import logging
from typing import Dict, Any, Optional

from .models import RealEstateProperty

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate and score property data"""
    
    def validate_property(self, raw_data: Dict[str, Any]) -> Optional[RealEstateProperty]:
        """Validate raw data using Pydantic model"""
        try:
            # Create validated property instance
            property_data = RealEstateProperty(**raw_data)
            return property_data
        except Exception as e:
            logger.warning(f"Validation failed for {raw_data.get('url')}: {e}")
            return None
    
    def calculate_quality_score(self, property_data: RealEstateProperty) -> int:
        """Calculate quality score from 0-100"""
        score = 0
        data = property_data.model_dump()
        
        # Required fields (40 points)
        required_fields = ['price', 'address', 'bedrooms', 'bathrooms']
        filled_required = sum(1 for field in required_fields if data.get(field) is not None)
        score += (filled_required / len(required_fields)) * 40
        
        # Optional fields (20 points)
        optional_fields = ['square_footage', 'property_description', 'photos', 'listing_id']
        filled_optional = sum(1 for field in optional_fields if data.get(field) is not None)
        if optional_fields:
            score += (filled_optional / len(optional_fields)) * 20
        
        # Data quality checks (40 points)
        
        # Price reasonableness (15 points)
        if data.get('price') is not None:
            price = data['price']
            if 1000 <= price <= 10000000:  # Reasonable price range
                score += 15
            elif 100 <= price <= 50000000:  # Acceptable but unusual
                score += 8
        
        # Address quality (10 points)
        if data.get('address'):
            address = str(data['address'])
            if len(address.split()) >= 3:  # At least 3 words
                score += 5
            if any(keyword in address.lower() for keyword in ['st', 'ave', 'rd', 'dr', 'lane', 'way']):
                score += 5
        
        # Bedrooms reasonableness (8 points)
        if data.get('bedrooms') is not None:
            bedrooms = data['bedrooms']
            if 0 <= bedrooms <= 10:
                score += 8
            elif 0 <= bedrooms <= 20:
                score += 4
        
        # Square footage reasonableness (7 points)
        if data.get('square_footage') is not None:
            sqft = data['square_footage']
            if 200 <= sqft <= 20000:
                score += 7
            elif 100 <= sqft <= 50000:
                score += 3
        
        # Ensure score is within bounds
        return min(int(score), 100)
    
    def validate_and_score(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate data and add quality score"""
        
        # Validate using Pydantic
        property_data = self.validate_property(raw_data)
        if not property_data:
            return None
        
        # Calculate quality score
        quality_score = self.calculate_quality_score(property_data)
        
        # Convert to dict and add score
        result = property_data.model_dump()
        result['quality_score'] = quality_score
        
        return result
    
    def is_acceptable_quality(self, quality_score: int, threshold: int = 50) -> bool:
        """Check if quality score meets threshold"""
        return quality_score >= threshold
