"""Test database operations"""

import pytest
from datetime import datetime, timedelta

from src.database.crud import PropertyCRUD, ScrapeJobCRUD, FailedUrlCRUD
from src.database.models import Property, ScrapeJob, FailedUrl


class TestPropertyCRUD:
    """Test PropertyCRUD operations"""
    
    def test_create_property(self, temp_db, sample_property_data):
        """Test creating a new property"""
        
        with temp_db.get_session() as session:
            crud = PropertyCRUD(session)
            
            property_obj = crud.create_or_update_property(sample_property_data)
            
            assert property_obj.id is not None
            assert property_obj.price == 500000.0
            assert property_obj.address == '123 Main St, Atlanta, GA 30309'
    
    def test_update_property(self, temp_db, sample_property_data):
        """Test updating existing property"""
        
        with temp_db.get_session() as session:
            crud = PropertyCRUD(session)
            
            # Create property
            property_obj = crud.create_or_update_property(sample_property_data)
            original_id = property_obj.id
            
            # Update with new price
            sample_property_data['price'] = 525000.0
            updated_property = crud.create_or_update_property(sample_property_data)
            
            assert updated_property.id == original_id
            assert updated_property.price == 525000.0
            assert updated_property.price_history is not None
    
    def test_search_properties(self, temp_db):
        """Test searching properties"""
        
        with temp_db.get_session() as session:
            crud = PropertyCRUD(session)
            
            # Create test properties
            properties = [
                {
                    'url': f'https://test.com/{i}',
                    'price': 100000 * i,
                    'bedrooms': i,
                    'address': f'{i}00 Street Name',
                    'quality_score': 50 + i * 10
                }
                for i in range(1, 6)
            ]
            
            for prop in properties:
                crud.create_or_update_property(prop)
            
            # Search tests
            results = crud.search_properties(min_price=200000, max_price=400000)
            assert len(results) == 3
            
            results = crud.search_properties(bedrooms=3)
            assert len(results) == 1
            
            results = crud.search_properties(min_quality_score=70)
            assert len(results) == 3
    
    def test_get_properties_needing_update(self, temp_db):
        """Test finding properties that need updating"""
        
        with temp_db.get_session() as session:
            crud = PropertyCRUD(session)
            
            # Create old property
            old_property = crud.create_or_update_property({
                'url': 'https://old.com/1',
                'price': 100000
            })
            
            # Manually set old scrape date
            old_property.last_scraped_at = datetime.utcnow() - timedelta(days=10)
            
            # Create recent property
            crud.create_or_update_property({
                'url': 'https://new.com/1',
                'price': 200000
            })
            
            # Get properties older than 7 days
            results = crud.get_properties_needing_update(days_old=7)
            
            assert len(results) == 1
            assert results[0].url == 'https://old.com/1'


class TestScrapeJobCRUD:
    """Test ScrapeJobCRUD operations"""
    
    def test_create_job(self, temp_db):
        """Test creating scrape job"""
        
        with temp_db.get_session() as session:
            crud = ScrapeJobCRUD(session)
            
            job = crud.create_job({
                'job_id': 'test-job-123',
                'input_file': 'test.csv',
                'total_urls': 100,
                'status': 'pending'
            })
            
            assert job.id is not None
            assert job.job_id == 'test-job-123'
            assert job.status == 'pending'
    
    def test_update_job_status(self, temp_db):
        """Test updating job status"""
        
        with temp_db.get_session() as session:
            crud = ScrapeJobCRUD(session)
            
            # Create job
            job = crud.create_job({
                'job_id': 'test-job-456',
                'total_urls': 50
            })
            
            # Update to running
            crud.update_job_status(
                job.id,
                'running',
                successful_scrapes=10
            )
            
            updated_job = crud.get_job_by_id('test-job-456')
            assert updated_job.status == 'running'
            assert updated_job.successful_scrapes == 10
            assert updated_job.started_at is not None


class TestFailedUrlCRUD:
    """Test FailedUrlCRUD operations"""
    
    def test_record_failure(self, temp_db):
        """Test recording URL failures"""
        
        with temp_db.get_session() as session:
            crud = FailedUrlCRUD(session)
            
            # First failure
            failed = crud.record_failure(
                'https://blocked.com/1',
                'Connection timeout',
                None
            )
            
            assert failed.failure_count == 1
            assert failed.is_blocked is False
            
            # Multiple failures
            for _ in range(5):
                crud.record_failure(
                    'https://blocked.com/1',
                    'Connection timeout',
                    None
                )
            
            # Should be blocked after 5 failures
            assert crud.is_url_blocked('https://blocked.com/1') is True
    
    def test_reset_url(self, temp_db):
        """Test resetting failed URL"""
        
        with temp_db.get_session() as session:
            crud = FailedUrlCRUD(session)
            
            # Record failure
            crud.record_failure(
                'https://reset.com/1',
                'Temporary error',
                500
            )
            
            # Reset
            success = crud.reset_url('https://reset.com/1')
            assert success is True
            
            # Should not be blocked anymore
            assert crud.is_url_blocked('https://reset.com/1') is False
