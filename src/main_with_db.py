#!/usr/bin/env python3
"""
Real Estate Scraper V3.2 - With Database Support
Extended version with database integration
"""

import csv
import json
import time
import logging
import asyncio
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .config import (
    DATA_DIR, LOGS_DIR, CSV_HEADERS,
    QUALITY_THRESHOLDS
)
from .models import RealEstateProperty, ScrapingResult, QualityReport
from .extractors import DataExtractor
from .validators import DataValidator
from .scrapers import BeautifulSoupScraper, AsyncScraper
from .scrapers.retry_handler import (
    DomainCircuitBreaker,
    AdaptiveRateLimiter,
    retry_with_backoff
)
from .database.connection import DatabaseConnection
from .database.crud import PropertyCRUD, ScrapeJobCRUD, FailedUrlCRUD

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RealEstateScraperWithDB:
    """Enhanced scraper with database support"""
    
    def __init__(self,
                 input_csv: str = 'real_estate_urls.csv',
                 output_csv: str = 'real_estate_data.csv',
                 quality_report: str = 'quality_report.json',
                 use_async: bool = True,
                 concurrent_limit: int = 5,
                 quality_threshold: int = 50,
                 use_database: bool = True,
                 db_type: str = 'sqlite',
                 db_path: Optional[str] = None):
        """
        Initialize scraper with database support
        
        Args:
            input_csv: Path to input CSV
            output_csv: Path to output CSV
            quality_report: Path to quality report
            use_async: Whether to use async scraping
            concurrent_limit: Max concurrent requests
            quality_threshold: Minimum quality score
            use_database: Whether to use database
            db_type: 'sqlite' or 'postgresql'
            db_path: Database path for SQLite
        """
        
        self.input_csv = Path(input_csv)
        self.output_csv = DATA_DIR / output_csv
        self.quality_report_file = DATA_DIR / quality_report
        self.use_async = use_async
        self.concurrent_limit = concurrent_limit
        self.quality_threshold = quality_threshold
        self.use_database = use_database
        
        # Initialize components
        self.validator = DataValidator()
        self.sync_scraper = BeautifulSoupScraper()
        self.circuit_breaker = DomainCircuitBreaker()
        self.rate_limiter = AdaptiveRateLimiter()
        
        # Database connection
        self.db = None
        self.job_id = None
        
        if use_database:
            self.db = DatabaseConnection(
                db_type=db_type,
                db_path=db_path
            )
            self.db.create_tables()
            
            # Create job ID
            self.job_id = str(uuid.uuid4())
        
        # Statistics
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.scraped_data = []
        self.failed_urls = []
        self.validation_failures = []
        self.response_times = []
    
    def read_urls(self) -> List[str]:
        """Read URLs from CSV or database"""
        
        urls = []
        
        # Try to get URLs needing update from database
        if self.use_database:
            with self.db.get_session() as session:
                crud = PropertyCRUD(session)
                
                # Get properties that haven't been updated recently
                properties = crud.get_properties_needing_update(
                    days_old=7,
                    limit=100
                )
                
                if properties:
                    logger.info(f"Found {len(properties)} properties needing update")
                    urls.extend([p.url for p in properties])
        
        # Also read from CSV
        if self.input_csv.exists():
            try:
                with open(self.input_csv, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get('URL') or row.get('url', '')
                        url = url.strip()
                        if url and url.startswith('http') and url not in urls:
                            urls.append(url)
                
                logger.info(f"Loaded {len(urls)} total URLs")
            except Exception as e:
                logger.error(f"Failed to read URLs: {e}")
        
        return urls
    
    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    def process_url_with_retry(self, url: str, html: Optional[str]) -> Optional[Dict[str, Any]]:
        """Process URL with retry logic"""
        
        if not html:
            raise Exception("No HTML content")
        
        # Extract data
        domain = self.sync_scraper.get_domain(url)
        extractor = DataExtractor(domain)
        raw_data = extractor.extract_property_data(html)
        
        # Add URL to data
        raw_data['url'] = url
        
        # Validate and score
        validated_data = self.validator.validate_and_score(raw_data)
        
        if not validated_data:
            raise Exception("Validation failed")
        
        return validated_data
    
    def save_to_database(self, property_data: Dict[str, Any]):
        """Save property to database"""
        
        if not self.use_database:
            return
        
        try:
            with self.db.get_session() as session:
                property_crud = PropertyCRUD(session)
                
                # Save property
                property_obj = property_crud.create_or_update_property(
                    property_data
                )
                
                # Save scrape result
                if self.job_id:
                    job_crud = ScrapeJobCRUD(session)
                    job = job_crud.get_job_by_id(self.job_id)
                    
                    if job:
                        from src.database.models import ScrapeResult
                        
                        result = ScrapeResult(
                            job_id=job.id,
                            property_id=property_obj.id,
                            url=property_data['url'],
                            success=True,
                            scrape_method=property_data.get('scrape_method'),
                            quality_score=property_data.get('quality_score'),
                            response_time=None  # Add if tracking
                        )
                        
                        session.add(result)
                
                logger.debug(f"Saved property {property_obj.id} to database")
                
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
    
    async def scrape_with_circuit_breaker(self, scraper: AsyncScraper, url: str) -> Optional[str]:
        """Scrape URL with circuit breaker protection"""
        
        domain = self.sync_scraper.get_domain(url)
        
        # Check circuit breaker
        if self.circuit_breaker.is_open(domain):
            logger.warning(f"Circuit open for {domain}, skipping {url}")
            return None
        
        # Check if URL is blocked in database
        if self.use_database:
            with self.db.get_session() as session:
                failed_crud = FailedUrlCRUD(session)
                if failed_crud.is_url_blocked(url):
                    logger.warning(f"URL is blocked in database: {url}")
                    return None
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        start_time = time.time()
        
        try:
            html = await scraper.scrape(url)
            response_time = time.time() - start_time
            
            # Record success
            self.rate_limiter.record_response(response_time, success=True)
            
            return html
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Record failure
            self.rate_limiter.record_response(response_time, success=False)
            
            # Record in database
            if self.use_database:
                with self.db.get_session() as session:
                    failed_crud = FailedUrlCRUD(session)
                    failed_crud.record_failure(
                        url=url,
                        reason=str(e),
                        http_status=None
                    )
            
            logger.error(f"Failed to scrape {url}: {e}")
            return None
    
    async def scrape_async_with_db(self, urls: List[str]):
        """Enhanced async scraping with database support"""
        
        async with AsyncScraper(self.concurrent_limit) as scraper:
            batch_size = self.concurrent_limit * 2
            
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} URLs)")
                
                # Create tasks with circuit breaker
                tasks = [
                    self.scrape_with_circuit_breaker(scraper, url)
                    for url in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"Exception for {url}: {result}")
                        self.failed_scrapes += 1
                        continue
                    
                    # Process the result
                    try:
                        data = self.process_url_with_retry(url, result)
                        
                        if data:
                            quality_score = data.get('quality_score', 0)
                            
                            if quality_score >= self.quality_threshold:
                                data['scrape_method'] = 'AsyncScraper'
                                self.scraped_data.append(data)
                                self.successful_scrapes += 1
                                
                                # Save to database
                                self.save_to_database(data)
                            else:
                                logger.warning(f"Quality too low for {url}: {quality_score}")
                                self.failed_scrapes += 1
                    except Exception as e:
                        logger.error(f"Failed to process {url}: {e}")
                        self.failed_scrapes += 1
    
    def run(self, limit: Optional[int] = None):
        """Main execution with database support"""
        
        print(f"\n{'='*70}")
        print("REAL ESTATE SCRAPER V3.2 - Database Edition")
        print(f"{'='*70}")
        
        # Create job in database
        if self.use_database:
            with self.db.get_session() as session:
                job_crud = ScrapeJobCRUD(session)
                
                job = job_crud.create_job({
                    'job_id': self.job_id,
                    'input_file': str(self.input_csv),
                    'output_file': str(self.output_csv),
                    'total_urls': 0,  # Will update
                    'concurrent_limit': self.concurrent_limit,
                    'quality_threshold': self.quality_threshold,
                    'use_async': self.use_async,
                    'status': 'pending'
                })
                
                self.db_job_id = job.id
        
        # Read URLs
        urls = self.read_urls()
        if not urls:
            logger.error("No URLs to process")
            return
        
        if limit:
            urls = urls[:limit]
        
        print(f"Total URLs to scrape: {len(urls)}")
        print(f"Database enabled: {self.use_database}")
        print(f"Circuit breaker enabled: True")
        print(f"Adaptive rate limiting: True")
        print(f"{'='*70}\n")
        
        # Update job status
        if self.use_database:
            with self.db.get_session() as session:
                job_crud = ScrapeJobCRUD(session)
                job_crud.update_job_status(
                    self.db_job_id,
                    'running',
                    total_urls=len(urls)
                )
        
        # Run scraping
        start_time = time.time()
        
        if self.use_async:
            asyncio.run(self.scrape_async_with_db(urls))
        else:
            # Sync scraping (implement if needed)
            logger.warning("Sync mode with DB not fully implemented")
        
        total_time = time.time() - start_time
        
        # Update job completion
        if self.use_database:
            with self.db.get_session() as session:
                job_crud = ScrapeJobCRUD(session)
                job_crud.update_job_status(
                    self.db_job_id,
                    'completed',
                    successful_scrapes=self.successful_scrapes,
                    failed_scrapes=self.failed_scrapes,
                    validation_failures=len(self.validation_failures)
                )
        
        # Save results
        self.save_to_csv()
        self.generate_quality_report()
        
        # Print database statistics
        if self.use_database:
            self.print_database_stats()
        
        print(f"\nTotal execution time: {total_time:.2f} seconds")
        print(f"Average time per URL: {total_time/len(urls):.2f} seconds")
    
    def print_database_stats(self):
        """Print database statistics"""
        
        if not self.use_database:
            return
        
        print(f"\n{'='*70}")
        print("DATABASE STATISTICS")
        print(f"{'='*70}")
        
        with self.db.get_session() as session:
            property_crud = PropertyCRUD(session)
            stats = property_crud.get_statistics()
            
            print(f"Total Properties: {stats['total_properties']}")
            print(f"Average Price: ${stats['avg_price']:,.0f}" if stats['avg_price'] else "N/A")
            print(f"Average Quality Score: {stats['avg_quality_score']:.1f}" if stats['avg_quality_score'] else "N/A")
            
            print("\nProperties by Bedrooms:")
            for beds, count in sorted(stats['properties_by_bedrooms'].items()):
                print(f"  {beds} bed: {count}")
            
            print("\nQuality Distribution:")
            for category, count in stats['properties_by_quality'].items():
                print(f"  {category}: {count}")
        
        # Circuit breaker stats
        cb_stats = self.circuit_breaker.get_stats()
        if cb_stats:
            print("\nCircuit Breaker Status:")
            for domain, status in cb_stats.items():
                print(f"  {domain}: {status['state']} (failures: {status['failure_count']})")
        
        print(f"{'='*70}\n")
    
    def save_to_csv(self):
        """Save to CSV (inherited from parent)"""
        
        if not self.scraped_data:
            logger.warning("No data to save")
            return
        
        try:
            with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.scraped_data)
            
            logger.info(f"Saved {len(self.scraped_data)} records to {self.output_csv}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")
    
    def generate_quality_report(self):
        """Generate quality report (inherited)"""
        
        if not self.scraped_data:
            return
        
        quality_scores = [d.get('quality_score', 0) for d in self.scraped_data]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        report_data = {
            'job_id': self.job_id,
            'total_records': len(self.scraped_data),
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'validation_failures': len(self.validation_failures),
            'success_rate': (self.successful_scrapes / (self.successful_scrapes + self.failed_scrapes) * 100)
                           if (self.successful_scrapes + self.failed_scrapes) > 0 else 0,
            'average_quality_score': avg_quality,
            'quality_distribution': {
                'excellent_90+': sum(1 for s in quality_scores if s >= 90),
                'good_70-89': sum(1 for s in quality_scores if 70 <= s < 90),
                'fair_50-69': sum(1 for s in quality_scores if 50 <= s < 70),
                'poor_below_50': sum(1 for s in quality_scores if s < 50)
            },
            'circuit_breaker_stats': self.circuit_breaker.get_stats(),
            'current_rate_limit': self.rate_limiter.get_current_rate()
        }
        
        try:
            with open(self.quality_report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"Quality report saved to {self.quality_report_file}")
        except Exception as e:
            logger.error(f"Failed to save quality report: {e}")


def main():
    """Enhanced command-line entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Real Estate Web Scraper V3.2 with Database')
    parser.add_argument('--input', default='real_estate_urls.csv',
                       help='Input CSV file with URLs')
    parser.add_argument('--output', default='real_estate_data.csv',
                       help='Output CSV file for results')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of URLs to process')
    parser.add_argument('--async', action='store_true', default=True,
                       help='Use async scraping (default: True)')
    parser.add_argument('--sync', dest='use_async', action='store_false',
                       help='Use synchronous scraping')
    parser.add_argument('--concurrent', type=int, default=5,
                       help='Max concurrent requests for async mode')
    parser.add_argument('--threshold', type=int, default=50,
                       help='Minimum quality score threshold')
    parser.add_argument('--db', action='store_true', default=True,
                       help='Use database (default: True)')
    parser.add_argument('--no-db', dest='db', action='store_false',
                       help='Disable database')
    parser.add_argument('--db-type', default='sqlite',
                       choices=['sqlite', 'postgresql'],
                       help='Database type')
    parser.add_argument('--db-path', default=None,
                       help='Database path for SQLite')
    
    args = parser.parse_args()
    
    # Create scraper instance
    scraper = RealEstateScraperWithDB(
        input_csv=args.input,
        output_csv=args.output,
        use_async=args.use_async,
        concurrent_limit=args.concurrent,
        quality_threshold=args.threshold,
        use_database=args.db,
        db_type=args.db_type,
        db_path=args.db_path
    )
    
    # Run scraper
    scraper.run(limit=args.limit)


if __name__ == '__main__':
    main()
