"""Pytest configuration and fixtures"""

import os
import sys
import tempfile
from pathlib import Path
import pytest
from typing import Generator
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseConnection
from src.database.models import Base


@pytest.fixture
def temp_db() -> Generator[DatabaseConnection, None, None]:
    """Create temporary database for testing"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create database connection
    db = DatabaseConnection(
        db_type='sqlite',
        db_path=db_path,
        echo=False
    )
    
    # Create tables
    db.create_tables()
    
    yield db
    
    # Cleanup
    db.close()
    os.unlink(db_path)


@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    
    mock = MagicMock()
    mock.status_code = 200
    mock.text = '''
    <html>
        <body>
            <div class="price">$500,000</div>
            <address>123 Main St, Atlanta, GA 30309</address>
            <span class="beds">3 beds</span>
            <span class="baths">2 baths</span>
            <span class="sqft">1500 sqft</span>
        </body>
    </html>
    '''
    
    return mock


@pytest.fixture
def sample_property_data():
    """Sample property data for testing"""
    
    return {
        'url': 'https://www.redfin.com/GA/Atlanta/123-Main-St/home/12345',
        'listing_id': '12345',
        'price': 500000.0,
        'address': '123 Main St, Atlanta, GA 30309',
        'bedrooms': 3,
        'bathrooms': 2.0,
        'square_footage': 1500,
        'quality_score': 75,
        'scrape_method': 'BeautifulSoup'
    }


@pytest.fixture
def sample_urls():
    """Sample URLs for testing"""
    
    return [
        'https://www.redfin.com/GA/Atlanta/123-Main-St/home/12345',
        'https://www.zillow.com/homedetails/456-Oak-Ave/98765',
        'https://www.realtor.com/realestateandhomes-detail/789-Pine-St'
    ]
