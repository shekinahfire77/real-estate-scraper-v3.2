"""CRUD operations for database models"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .models import Property, ScrapeJob, ScrapeResult, FailedUrl
from ..models import RealEstateProperty

logger = logging.getLogger(__name__)


class PropertyCRUD:
    """CRUD operations for properties"""
    
    def __init__(self, session: Session):
        """Initialize with database session"""
        self.session = session
    
    def create_or_update_property(self, 
                                 property_data: Dict[str, Any]) -> Property:
        """Create new property or update existing"""
        
        # Check if property exists
        existing = None
        
        # Try to find by URL and listing_id
        if property_data.get('url') and property_data.get('listing_id'):
            existing = self.session.query(Property).filter(
                and_(
                    Property.url == property_data['url'],
                    Property.listing_id == property_data['listing_id']
                )
            ).first()
        
        # If not found, try by URL only
        if not existing and property_data.get('url'):
            existing = self.session.query(Property).filter(
                Property.url == property_data['url']
            ).first()
        
        if existing:
            # Update existing property
            logger.debug(f"Updating property: {existing.id}")
            
            # Track price changes
            if property_data.get('price') and existing.price != property_data['price']:
                price_history = existing.price_history or []
                price_history.append({
                    'price': float(existing.price) if existing.price else None,
                    'date': existing.updated_at.isoformat() if existing.updated_at else None
                })
                property_data['price_history'] = price_history
            
            # Update fields
            for key, value in property_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            
            existing.last_scraped_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            
            return existing
        else:
            # Create new property
            logger.debug(f"Creating new property: {property_data.get('url')}")
            
            new_property = Property(**property_data)
            new_property.last_scraped_at = datetime.utcnow()
            
            self.session.add(new_property)
            return new_property
    
    def get_property_by_id(self, property_id: int) -> Optional[Property]:
        """Get property by ID"""
        return self.session.query(Property).filter(
            Property.id == property_id
        ).first()
    
    def get_property_by_url(self, url: str) -> Optional[Property]:
        """Get property by URL"""
        return self.session.query(Property).filter(
            Property.url == url
        ).first()
    
    def search_properties(self,
                         min_price: Optional[float] = None,
                         max_price: Optional[float] = None,
                         bedrooms: Optional[int] = None,
                         bathrooms: Optional[float] = None,
                         min_sqft: Optional[int] = None,
                         address_contains: Optional[str] = None,
                         min_quality_score: Optional[int] = None,
                         limit: int = 100) -> List[Property]:
        """Search properties with filters"""
        
        query = self.session.query(Property)
        
        if min_price:
            query = query.filter(Property.price >= min_price)
        if max_price:
            query = query.filter(Property.price <= max_price)
        if bedrooms:
            query = query.filter(Property.bedrooms == bedrooms)
        if bathrooms:
            query = query.filter(Property.bathrooms >= bathrooms)
        if min_sqft:
            query = query.filter(Property.square_footage >= min_sqft)
        if address_contains:
            query = query.filter(
                Property.address.ilike(f'%{address_contains}%')
            )
        if min_quality_score:
            query = query.filter(Property.quality_score >= min_quality_score)
        
        return query.limit(limit).all()
    
    def get_properties_needing_update(self, 
                                     days_old: int = 7,
                                     limit: int = 100) -> List[Property]:
        """Get properties that haven't been scraped recently"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        return self.session.query(Property).filter(
            or_(
                Property.last_scraped_at.is_(None),
                Property.last_scraped_at < cutoff_date
            )
        ).limit(limit).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get property statistics"""
        
        stats = {
            'total_properties': self.session.query(func.count(Property.id)).scalar(),
            'avg_price': self.session.query(func.avg(Property.price)).scalar(),
            'avg_quality_score': self.session.query(func.avg(Property.quality_score)).scalar(),
            'properties_by_bedrooms': {},
            'properties_by_quality': {}
        }
        
        # Count by bedrooms
        bedroom_counts = self.session.query(
            Property.bedrooms,
            func.count(Property.id)
        ).group_by(Property.bedrooms).all()
        
        for beds, count in bedroom_counts:
            if beds:
                stats['properties_by_bedrooms'][beds] = count
        
        # Count by quality score ranges
        quality_ranges = [
            ('excellent_90+', 90, 100),
            ('good_70-89', 70, 89),
            ('fair_50-69', 50, 69),
            ('poor_below_50', 0, 49)
        ]
        
        for label, min_score, max_score in quality_ranges:
            count = self.session.query(func.count(Property.id)).filter(
                and_(
                    Property.quality_score >= min_score,
                    Property.quality_score <= max_score
                )
            ).scalar()
            stats['properties_by_quality'][label] = count
        
        return stats


class ScrapeJobCRUD:
    """CRUD operations for scrape jobs"""
    
    def __init__(self, session: Session):
        """Initialize with database session"""
        self.session = session
    
    def create_job(self, job_data: Dict[str, Any]) -> ScrapeJob:
        """Create new scrape job"""
        
        job = ScrapeJob(**job_data)
        self.session.add(job)
        return job
    
    def update_job_status(self, 
                         job_id: int,
                         status: str,
                         **kwargs) -> Optional[ScrapeJob]:
        """Update job status and statistics"""
        
        job = self.session.query(ScrapeJob).filter(
            ScrapeJob.id == job_id
        ).first()
        
        if job:
            job.status = status
            job.updated_at = datetime.utcnow()
            
            if status == 'running' and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                job.completed_at = datetime.utcnow()
            
            # Update any additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
        
        return job
    
    def get_recent_jobs(self, limit: int = 10) -> List[ScrapeJob]:
        """Get recent scrape jobs"""
        
        return self.session.query(ScrapeJob).order_by(
            ScrapeJob.created_at.desc()
        ).limit(limit).all()
    
    def get_job_by_id(self, job_id: str) -> Optional[ScrapeJob]:
        """Get job by job_id"""
        
        return self.session.query(ScrapeJob).filter(
            ScrapeJob.job_id == job_id
        ).first()


class FailedUrlCRUD:
    """CRUD operations for failed URLs"""
    
    def __init__(self, session: Session):
        """Initialize with database session"""
        self.session = session
    
    def record_failure(self, 
                      url: str,
                      reason: str,
                      http_status: Optional[int] = None) -> FailedUrl:
        """Record a URL failure"""
        
        failed = self.session.query(FailedUrl).filter(
            FailedUrl.url == url
        ).first()
        
        if failed:
            # Update existing failure
            failed.failure_count += 1
            failed.last_failure_reason = reason
            failed.last_http_status = http_status
            failed.last_failed_at = datetime.utcnow()
            
            # Circuit breaker: block after 5 failures
            if failed.failure_count >= 5:
                failed.is_blocked = True
                failed.blocked_until = datetime.utcnow() + timedelta(days=7)
        else:
            # Create new failure record
            failed = FailedUrl(
                url=url,
                last_failure_reason=reason,
                last_http_status=http_status
            )
            self.session.add(failed)
        
        return failed
    
    def is_url_blocked(self, url: str) -> bool:
        """Check if URL is blocked"""
        
        failed = self.session.query(FailedUrl).filter(
            FailedUrl.url == url
        ).first()
        
        if not failed:
            return False
        
        if failed.is_blocked:
            # Check if temporary block has expired
            if failed.blocked_until and failed.blocked_until < datetime.utcnow():
                failed.is_blocked = False
                failed.blocked_until = None
                return False
            return True
        
        return False
    
    def get_blocked_urls(self) -> List[FailedUrl]:
        """Get all blocked URLs"""
        
        return self.session.query(FailedUrl).filter(
            FailedUrl.is_blocked == True
        ).all()
    
    def reset_url(self, url: str) -> bool:
        """Reset a failed URL to try again"""
        
        failed = self.session.query(FailedUrl).filter(
            FailedUrl.url == url
        ).first()
        
        if failed:
            self.session.delete(failed)
            return True
        
        return False
