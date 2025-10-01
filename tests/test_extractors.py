"""Test data extractors"""

import pytest
from bs4 import BeautifulSoup

from src.extractors import DataExtractor


class TestDataExtractor:
    """Test DataExtractor class"""
    
    def test_extract_with_fallback(self):
        """Test fallback selector extraction"""
        
        html = '''
        <html>
            <body>
                <div class="price">$500,000</div>
            </body>
        </html>
        '''
        
        soup = BeautifulSoup(html, 'lxml')
        extractor = DataExtractor('redfin.com')
        
        # Test successful extraction
        result = extractor.extract_with_fallback(
            soup,
            ['.nonexistent', '.price']
        )
        assert result == '$500,000'
        
        # Test failed extraction
        result = extractor.extract_with_fallback(
            soup,
            ['.nonexistent1', '.nonexistent2']
        )
        assert result is None
    
    def test_extract_images(self):
        """Test image extraction"""
        
        html = '''
        <html>
            <body>
                <img src="https://example.com/photo1.jpg" />
                <img src="https://example.com/photo2.jpg" />
                <img data-src="https://example.com/photo3.jpg" />
            </body>
        </html>
        '''
        
        soup = BeautifulSoup(html, 'lxml')
        extractor = DataExtractor('generic')
        
        images = extractor.extract_images(
            soup,
            ['img'],
            max_images=2
        )
        
        assert len(images) == 2
        assert images[0] == 'https://example.com/photo1.jpg'
        assert images[1] == 'https://example.com/photo2.jpg'
    
    def test_clean_data(self):
        """Test data cleaning"""
        
        extractor = DataExtractor('generic')
        
        data = {
            'price': '$1,250,000',
            'bedrooms': '3 beds',
            'bathrooms': '2.5 baths',
            'square_footage': '1,500 sqft'
        }
        
        cleaned = extractor.clean_data(data)
        
        assert cleaned['price'] == 1250000.0
        assert cleaned['bedrooms'] == 3
        assert cleaned['bathrooms'] == 2.5
        assert cleaned['square_footage'] == 1500
    
    def test_extract_property_data(self):
        """Test complete property extraction"""
        
        html = '''
        <html>
            <body>
                <div class="homecardV2Price">$750,000</div>
                <div class="bp-Homecard__Address">456 Oak Ave, Seattle, WA</div>
                <span class="bp-Homecard__Stats--beds">4 beds</span>
                <span class="bp-Homecard__Stats--baths">3 baths</span>
                <span class="bp-Homecard__Stats--sqft">2200 sqft</span>
            </body>
        </html>
        '''
        
        extractor = DataExtractor('redfin.com')
        data = extractor.extract_property_data(html)
        
        assert data['price'] == 750000.0
        assert data['address'] == '456 Oak Ave, Seattle, WA'
        assert data['bedrooms'] == 4
        assert data['bathrooms'] == 3.0
        assert data['square_footage'] == 2200
