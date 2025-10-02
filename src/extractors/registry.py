"""Extractor registry for domain-based extractor selection"""

import logging
from typing import Dict, Type, Optional
from urllib.parse import urlparse

from .base_extractor import BaseExtractor
from .generic_extractor import GenericExtractor
from .redfin_extractor import RedfinEnhancedExtractor
from .zillow_extractor import ZillowExtractor
from .realtor_extractor import RealtorExtractor

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """Registry for managing site-specific extractors
    
    Automatically selects the appropriate extractor based on domain
    and provides caching for extractor instances.
    """
    
    def __init__(self):
        """Initialize the registry with empty caches"""
        self._registry: Dict[str, Type[BaseExtractor]] = {}
        self._instances: Dict[str, BaseExtractor] = {}
        self._initialize_registry()
    
    def _initialize_registry(self):
        """Initialize the default registry mappings
        
        Maps domains to their specific extractor classes.
        New sites can be added here as extractors are developed.
        """
        # Register specific extractors
        self._registry = {
            'redfin.com': RedfinEnhancedExtractor,
            'www.redfin.com': RedfinEnhancedExtractor,
            
            # Zillow
            'zillow.com': ZillowExtractor,
            'www.zillow.com': ZillowExtractor,
            
            # Realtor
            'realtor.com': RealtorExtractor,
            'www.realtor.com': RealtorExtractor,
            
            # Trulia (owned by Zillow) - uses Zillow extractor
            'trulia.com': ZillowExtractor,
            'www.trulia.com': ZillowExtractor,
            
            # Apartments.com - for rentals (using generic for now)
            'apartments.com': GenericExtractor,
            'www.apartments.com': GenericExtractor,
            
            # Default fallback - using None as key
            None: GenericExtractor
        }
        
        logger.info(f"Extractor registry initialized with {len(self._registry)} mappings")
    
    def register(self, domain: str, extractor_class: Type[BaseExtractor]):
        """Register a new domain-extractor mapping
        
        Args:
            domain: Website domain (e.g., 'zillow.com')
            extractor_class: Extractor class to use for this domain
        """
        self._registry[domain] = extractor_class
        # Clear cached instance if exists
        if domain in self._instances:
            del self._instances[domain]
        logger.info(f"Registered {extractor_class.__name__} for domain: {domain}")
    
    def get_extractor_class(self, url: str) -> Type[BaseExtractor]:
        """Get the appropriate extractor class for a URL
        
        Args:
            url: Property URL
            
        Returns:
            Extractor class for the domain
        """
        domain = self._extract_domain(url)
        
        # Check if specific extractor exists
        if domain in self._registry:
            return self._registry[domain]
        
        # Check without www
        if domain.startswith('www.'):
            domain_no_www = domain[4:]
            if domain_no_www in self._registry:
                return self._registry[domain_no_www]
        
        # Log that we're using generic extractor
        logger.debug(f"No specific extractor for {domain}, using GenericExtractor")
        
        # Return generic extractor class
        return GenericExtractor
    
    def get_extractor(self, url: str, use_cache: bool = True) -> BaseExtractor:
        """Get an extractor instance for a URL
        
        Args:
            url: Property URL
            use_cache: If True, reuse cached instances per domain
            
        Returns:
            Extractor instance ready to use
        """
        domain = self._extract_domain(url)
        
        # Check cache if enabled
        if use_cache and domain in self._instances:
            logger.debug(f"Using cached extractor for {domain}")
            return self._instances[domain]
        
        # Get the appropriate class
        extractor_class = self.get_extractor_class(url)
        
        # Create instance
        if extractor_class == GenericExtractor:
            # Generic extractor needs domain parameter
            instance = extractor_class(domain)
        else:
            # Site-specific extractors don't need domain
            instance = extractor_class()
        
        # Cache if enabled
        if use_cache:
            self._instances[domain] = instance
            logger.debug(f"Cached {instance.__class__.__name__} for {domain}")
        
        return instance
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL
        
        Args:
            url: Full URL
            
        Returns:
            Domain (e.g., 'redfin.com')
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            return domain
        except Exception as e:
            logger.error(f"Failed to extract domain from {url}: {e}")
            return 'unknown'
    
    def get_supported_sites(self) -> Dict[str, str]:
        """Get list of supported sites with their extractors
        
        Returns:
            Dictionary mapping domains to extractor names
        """
        sites = {}
        for domain, extractor_class in self._registry.items():
            if domain is not None:  # Skip the None/default key
                sites[domain] = extractor_class.__name__
        return sites
    
    def is_site_supported(self, url: str) -> bool:
        """Check if a URL's domain has a specific extractor
        
        Args:
            url: Property URL
            
        Returns:
            True if site has dedicated extractor, False if using generic
        """
        domain = self._extract_domain(url)
        return domain in self._registry or domain[4:] in self._registry if domain.startswith('www.') else False


# Global registry instance
_registry = ExtractorRegistry()


# Public API functions
def register_extractor(domain: str, extractor_class: Type[BaseExtractor]):
    """Register a new extractor for a domain
    
    Args:
        domain: Website domain
        extractor_class: Extractor class to use
    """
    _registry.register(domain, extractor_class)


def get_extractor_for_url(url: str, use_cache: bool = True) -> BaseExtractor:
    """Get an appropriate extractor for a URL
    
    Args:
        url: Property URL
        use_cache: Whether to cache extractor instances
        
    Returns:
        Extractor instance for the URL's domain
    """
    return _registry.get_extractor(url, use_cache)


def get_supported_sites() -> Dict[str, str]:
    """Get dictionary of supported sites
    
    Returns:
        Dictionary mapping domains to extractor names
    """
    return _registry.get_supported_sites()


def is_site_supported(url: str) -> bool:
    """Check if URL's site has a dedicated extractor
    
    Args:
        url: Property URL
        
    Returns:
        True if site has dedicated extractor
    """
    return _registry.is_site_supported(url)
