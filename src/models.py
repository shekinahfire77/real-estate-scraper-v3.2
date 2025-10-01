"""Pydantic models for data validation"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class RealEstateProperty(BaseModel):
    """Validated real estate property data model"""
    
    # Required fields
    url: str = Field(..., min_length=10, description="Property listing URL")
    
    # Optional fields with validation
    listing_id: Optional[str] = Field(None, description="Unique listing identifier")
    price: Optional[float] = Field(None, ge=0, le=50000000, description="Property price")
    address: Optional[str] = Field(None, min_length=5, description="Property address")
    bedrooms: Optional[int] = Field(None, ge=0, le=20, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, le=20, description="Number of bathrooms")
    square_footage: Optional[int] = Field(None, ge=100, le=50000, description="Square footage")
    
    # Additional fields
    page_type: Optional[str] = None
    property_description: Optional[str] = None
    photos: Optional[str] = None
    days_on_market: Optional[int] = None
    property_history: Optional[str] = None
    
    # Rental-specific fields
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    lease_terms: Optional[str] = None
    amenities: Optional[str] = None
    pet_policy: Optional[str] = None
    contact_info: Optional[str] = None
    availability_date: Optional[str] = None
    application_requirements: Optional[str] = None
    
    # Commercial fields
    lease_rate: Optional[float] = None
    property_size: Optional[str] = None
    zoning_info: Optional[str] = None
    parking: Optional[str] = None
    building_specs: Optional[str] = None
    property_management: Optional[str] = None
    
    # Metadata
    scrape_method: str = Field(default="Unknown", description="Method used for scraping")
    has_api_data: bool = Field(default=False, description="Whether data came from API")
    quality_score: Optional[int] = Field(None, ge=0, le=100, description="Data quality score")
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        """Validate price is within reasonable range"""
        if v is not None and (v < 100 or v > 50000000):
            logger.warning(f'Price {v} seems unrealistic')
        return v
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address is meaningful"""
        if v and (len(v) < 5 or 'n/a' in v.lower()):
            return None
        return v
    
    @field_validator('bedrooms', 'bathrooms')
    @classmethod
    def validate_rooms(cls, v: Optional[float]) -> Optional[float]:
        """Validate room counts are reasonable"""
        if v is not None and v < 0:
            return None
        return v
    
    class Config:
        """Pydantic config"""
        extra = 'allow'
        validate_assignment = True


class ScrapingResult(BaseModel):
    """Result of a scraping operation"""
    
    success: bool
    url: str
    data: Optional[RealEstateProperty] = None
    error: Optional[str] = None
    scrape_method: str = "Unknown"
    response_time: Optional[float] = None
    

class QualityReport(BaseModel):
    """Quality report for scraped data"""
    
    total_records: int
    successful_scrapes: int
    failed_scrapes: int
    validation_failures: int
    success_rate: float
    average_quality_score: float
    quality_distribution: dict
    scrape_methods_used: dict
    average_response_time: Optional[float] = None
