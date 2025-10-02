"""Property data extractors for various real estate websites"""

from .base_extractor import BaseExtractor
from .generic_extractor import GenericExtractor, DataExtractor
from .redfin_extractor import RedfinEnhancedExtractor
from .zillow_extractor import ZillowExtractor
from .realtor_extractor import RealtorExtractor
from .registry import (
    get_extractor_for_url,
    register_extractor,
    get_supported_sites,
    is_site_supported
)

__all__ = [
    # Base classes
    'BaseExtractor',
    'GenericExtractor',
    'DataExtractor',  # For backward compatibility
    
    # Site-specific extractors
    'RedfinEnhancedExtractor',
    'ZillowExtractor',
    'RealtorExtractor',
    
    # Registry functions
    'get_extractor_for_url',
    'register_extractor',
    'get_supported_sites',
    'is_site_supported',
]
