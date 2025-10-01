"""SQLAlchemy database models"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Boolean, Text, ForeignKey, Index, JSON,
    UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Property(Base):
    """Property listing model"""
    
    __tablename__ = 'properties'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Unique identifiers
    url = Column(String(500), nullable=False, index=True)
    listing_id = Column(String(100), index=True)
    
    # Property details
    price = Column(Float)
    address = Column(String(500))
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    square_footage = Column(Integer)

    # Additional fields
    page_type = Column(String(50))
    property_type = Column(String(100))  # e.g., Single Family, Condo, Townhouse
    property_description = Column(Text)
    photos = Column(Text)  # JSON array of photo URLs
    days_on_market = Column(Integer)
    property_history = Column(Text)
    year_built = Column(Integer)
    lot_size = Column(String(100))
    price_per_sqft = Column(Float)
    schools = Column(Text)  # JSON array of nearby schools
    hoa_fee = Column(Float)
    
    # Rental-specific
    monthly_rent = Column(Float)
    security_deposit = Column(Float)
    lease_terms = Column(String(500))
    amenities = Column(Text)
    pet_policy = Column(String(500))
    contact_info = Column(String(500))
    availability_date = Column(DateTime)
    application_requirements = Column(Text)
    
    # Commercial fields
    lease_rate = Column(Float)
    property_size = Column(String(100))
    zoning_info = Column(String(200))
    parking = Column(String(200))
    building_specs = Column(Text)
    property_management = Column(String(500))
    
    # Metadata
    quality_score = Column(Integer)
    scrape_method = Column(String(50))
    has_api_data = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped_at = Column(DateTime)
    
    # Tracking changes
    price_history = Column(JSON)  # Store price changes over time
    status_changes = Column(JSON)  # Track availability changes
    
    # Relationships
    scrape_results = relationship("ScrapeResult", back_populates="property")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_price_bedrooms', 'price', 'bedrooms'),
        Index('idx_address', 'address'),
        Index('idx_quality_score', 'quality_score'),
        Index('idx_last_scraped', 'last_scraped_at'),
        UniqueConstraint('url', 'listing_id', name='uq_url_listing'),
    )
    
    def __repr__(self):
        return f"<Property(id={self.id}, address='{self.address}', price={self.price})>"


class ScrapeJob(Base):
    """Track scraping jobs"""
    
    __tablename__ = 'scrape_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False)
    
    # Job configuration
    input_file = Column(String(500))
    output_file = Column(String(500))
    total_urls = Column(Integer)
    concurrent_limit = Column(Integer)
    quality_threshold = Column(Integer)
    use_async = Column(Boolean, default=True)
    
    # Job status
    status = Column(String(50), default='pending')  # pending, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Statistics
    successful_scrapes = Column(Integer, default=0)
    failed_scrapes = Column(Integer, default=0)
    validation_failures = Column(Integer, default=0)
    average_quality_score = Column(Float)
    average_response_time = Column(Float)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Relationships
    results = relationship("ScrapeResult", back_populates="job")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index for job queries
    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScrapeJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


class ScrapeResult(Base):
    """Individual scrape results"""
    
    __tablename__ = 'scrape_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    job_id = Column(Integer, ForeignKey('scrape_jobs.id'))
    property_id = Column(Integer, ForeignKey('properties.id'))
    
    # Scrape details
    url = Column(String(500), nullable=False)
    success = Column(Boolean, default=False)
    scrape_method = Column(String(50))
    response_time = Column(Float)
    quality_score = Column(Integer)
    
    # Error tracking
    error_type = Column(String(100))
    error_message = Column(Text)
    http_status_code = Column(Integer)
    
    # Raw data (for debugging)
    raw_html = Column(Text)  # Optional: store compressed HTML
    extracted_data = Column(JSON)
    
    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("ScrapeJob", back_populates="results")
    property = relationship("Property", back_populates="scrape_results")
    
    # Indexes
    __table_args__ = (
        Index('idx_result_job', 'job_id'),
        Index('idx_result_property', 'property_id'),
        Index('idx_result_success', 'success'),
        Index('idx_result_scraped', 'scraped_at'),
    )
    
    def __repr__(self):
        return f"<ScrapeResult(id={self.id}, url='{self.url}', success={self.success})>"


class FailedUrl(Base):
    """Track persistently failing URLs"""
    
    __tablename__ = 'failed_urls'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), unique=True, nullable=False)
    
    # Failure tracking
    failure_count = Column(Integer, default=1)
    last_failure_reason = Column(Text)
    last_http_status = Column(Integer)
    
    # Circuit breaker pattern
    is_blocked = Column(Boolean, default=False)  # Stop trying this URL
    blocked_until = Column(DateTime)  # Temporary block
    
    # Timestamps
    first_failed_at = Column(DateTime, default=datetime.utcnow)
    last_failed_at = Column(DateTime, default=datetime.utcnow)
    
    # Index for queries
    __table_args__ = (
        Index('idx_failed_blocked', 'is_blocked'),
        Index('idx_failed_count', 'failure_count'),
    )
    
    def __repr__(self):
        return f"<FailedUrl(url='{self.url}', failures={self.failure_count})>"
