"""Test data validators"""

import pytest

from src.validators import DataValidator
from src.models import RealEstateProperty


class TestDataValidator:
    """Test DataValidator class"""
    
    def test_validate_property(self):
        """Test property validation"""
        
        validator = DataValidator()
        
        # Valid data
        valid_data = {
            'url': 'https://www.redfin.com/test',
            'price': 500000.0,
            'address': '123 Main St',
            'bedrooms': 3,
            'bathrooms': 2.0
        }
        
        result = validator.validate_property(valid_data)
        assert isinstance(result, RealEstateProperty)
        assert result.price == 500000.0
        
        # Invalid data (price too high)
        invalid_data = {
            'url': 'https://www.redfin.com/test',
            'price': 100000000.0  # Exceeds max
        }
        
        result = validator.validate_property(invalid_data)
        assert result is None
    
    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        
        validator = DataValidator()
        
        # High quality data
        good_property = RealEstateProperty(
            url='https://www.redfin.com/test',
            price=500000.0,
            address='123 Main Street, Atlanta, GA 30309',
            bedrooms=3,
            bathrooms=2.0,
            square_footage=1500,
            listing_id='12345',
            photos='photo1.jpg,photo2.jpg'
        )
        
        score = validator.calculate_quality_score(good_property)
        assert score >= 70  # Should be a good score
        
        # Low quality data
        poor_property = RealEstateProperty(
            url='https://www.redfin.com/test',
            price=None,
            address=None,
            bedrooms=None,
            bathrooms=None
        )
        
        score = validator.calculate_quality_score(poor_property)
        assert score < 50  # Should be a poor score
    
    def test_validate_and_score(self):
        """Test combined validation and scoring"""
        
        validator = DataValidator()
        
        data = {
            'url': 'https://www.redfin.com/test',
            'price': '750000',
            'address': '789 Pine Street, Seattle, WA',
            'bedrooms': '4',
            'bathrooms': '3.5',
            'square_footage': '2500'
        }
        
        result = validator.validate_and_score(data)
        
        assert result is not None
        assert 'quality_score' in result
        assert result['quality_score'] >= 60
        assert result['price'] == 750000.0
        assert result['bedrooms'] == 4
    
    def test_is_acceptable_quality(self):
        """Test quality threshold check"""
        
        validator = DataValidator()
        
        assert validator.is_acceptable_quality(75, threshold=50) is True
        assert validator.is_acceptable_quality(40, threshold=50) is False
        assert validator.is_acceptable_quality(50, threshold=50) is True
