#!/usr/bin/env python3
"""
Real Estate Scraper V3.1 - Main entry point
Modularized version with async support
"""

import csv
import json
import time
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import defaultdict

from .config import (
    DATA_DIR, LOGS_DIR, CSV_HEADERS,
    QUALITY_THRESHOLDS
)
from .models import RealEstateProperty, ScrapingResult, QualityReport
from .extractors import DataExtractor
from .validators import DataValidator
from .scrapers import BeautifulSoupScraper, AsyncScraper

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


class RealEstateScraperV3:
    """Main scraper orchestrator"""
    
    def __init__(self,
                 input_csv: str = 'real_estate_urls.csv',
                 output_csv: str = 'real_estate_data.csv',
                 quality_report: str = 'quality_report.json',
                 use_async: bool = True,
                 concurrent_limit: int = 5,
                 quality_threshold: int = 50):
        """
        Initialize the scraper
        
        Args:
            input_csv: Path to input CSV with URLs
            output_csv: Path to output CSV for results
            quality_report: Path to quality report JSON
            use_async: Whether to use async scraping
            concurrent_limit: Max concurrent requests for async
            quality_threshold: Minimum quality score to accept
        """
        
        self.input_csv = Path(input_csv)
        self.output_csv = DATA_DIR / output_csv
        self.quality_report_file = DATA_DIR / quality_report
        self.use_async = use_async
        self.concurrent_limit = concurrent_limit
        self.quality_threshold = quality_threshold
        
        # Initialize components
        self.validator = DataValidator()
        self.sync_scraper = BeautifulSoupScraper()
        
        # Statistics
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.scraped_data = []
        self.failed_urls = []
        self.validation_failures = []
        self.response_times = []
    
    def read_urls(self) -> List[str]:
        """Read URLs from CSV file"""
        urls = []
        
        if not self.input_csv.exists():
            logger.error(f"Input file {self.input_csv} does not exist")
            return urls
        
        try:
            with open(self.input_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Support both 'URL' and 'url' column names
                    url = row.get('URL') or row.get('url', '')
                    url = url.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
            
            logger.info(f"Loaded {len(urls)} URLs from {self.input_csv}")
        except Exception as e:
            logger.error(f"Failed to read URLs: {e}")
        
        return urls
    
    def process_url(self, url: str, html: Optional[str]) -> Optional[Dict[str, Any]]:
        """Process a single URL's HTML content"""
        
        if not html:
            self.failed_scrapes += 1
            self.failed_urls.append(url)
            return None
        
        # Extract data
        domain = self.sync_scraper.get_domain(url)
        extractor = DataExtractor(domain)
        raw_data = extractor.extract_property_data(html)
        
        # Add URL to data
        raw_data['url'] = url
        
        # Validate and score
        validated_data = self.validator.validate_and_score(raw_data)
        
        if validated_data:
            # Check quality threshold
            quality_score = validated_data.get('quality_score', 0)
            
            if quality_score >= self.quality_threshold:
                self.successful_scrapes += 1
                return validated_data
            else:
                logger.warning(f"Quality score {quality_score} below threshold for {url}")
                self.validation_failures.append({
                    'url': url,
                    'reason': f'Quality score {quality_score} below threshold {self.quality_threshold}'
                })
        else:
            self.validation_failures.append({
                'url': url,
                'reason': 'Validation failed'
            })
        
        self.failed_scrapes += 1
        return None
    
    async def scrape_async(self, urls: List[str]) -> None:
        """Scrape URLs asynchronously"""
        
        async with AsyncScraper(self.concurrent_limit) as scraper:
            # Process in batches to avoid overwhelming
            batch_size = self.concurrent_limit * 2
            
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} URLs)")
                
                start_time = time.time()
                results = await scraper.scrape_multiple(batch)
                batch_time = time.time() - start_time
                
                for result in results:
                    url = result['url']
                    html = result['html']
                    
                    # Track response time
                    self.response_times.append(batch_time / len(batch))
                    
                    # Process the result
                    data = self.process_url(url, html)
                    if data:
                        data['scrape_method'] = 'AsyncScraper'
                        self.scraped_data.append(data)
    
    def scrape_sync(self, urls: List[str]) -> None:
        """Scrape URLs synchronously"""
        
        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] Scraping: {url}")
            
            start_time = time.time()
            html = self.sync_scraper.scrape(url)
            response_time = time.time() - start_time
            
            # Track response time
            self.response_times.append(response_time)
            
            # Process the result
            data = self.process_url(url, html)
            if data:
                data['scrape_method'] = 'BeautifulSoup'
                self.scraped_data.append(data)
            
            # Delay between requests
            if i < len(urls):
                self.sync_scraper.random_delay(url)
    
    def save_to_csv(self) -> None:
        """Save scraped data to CSV"""
        
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
    
    def generate_quality_report(self) -> None:
        """Generate and save quality report"""
        
        if not self.scraped_data:
            return
        
        quality_scores = [d.get('quality_score', 0) for d in self.scraped_data]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Count scrape methods used
        scrape_methods = defaultdict(int)
        for data in self.scraped_data:
            scrape_methods[data.get('scrape_method', 'Unknown')] += 1
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else None
        
        report_data = {
            'total_records': len(self.scraped_data),
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'validation_failures': len(self.validation_failures),
            'success_rate': (self.successful_scrapes / (self.successful_scrapes + self.failed_scrapes) * 100)
                           if (self.successful_scrapes + self.failed_scrapes) > 0 else 0,
            'average_quality_score': avg_quality,
            'quality_distribution': {
                'excellent_90+': sum(1 for s in quality_scores if s >= QUALITY_THRESHOLDS['excellent']),
                'good_70-89': sum(1 for s in quality_scores if QUALITY_THRESHOLDS['good'] <= s < QUALITY_THRESHOLDS['excellent']),
                'fair_50-69': sum(1 for s in quality_scores if QUALITY_THRESHOLDS['fair'] <= s < QUALITY_THRESHOLDS['good']),
                'poor_below_50': sum(1 for s in quality_scores if s < QUALITY_THRESHOLDS['fair'])
            },
            'scrape_methods_used': dict(scrape_methods),
            'average_response_time': avg_response_time
        }
        
        # Create QualityReport model
        report = QualityReport(**report_data)
        
        # Save report
        try:
            with open(self.quality_report_file, 'w') as f:
                json.dump(report.model_dump(), f, indent=2)
            
            logger.info(f"Quality report saved to {self.quality_report_file}")
            
            # Print summary
            self.print_summary(report)
            
        except Exception as e:
            logger.error(f"Failed to save quality report: {e}")
    
    def print_summary(self, report: QualityReport) -> None:
        """Print execution summary"""
        
        print(f"\n{'='*70}")
        print("DATA QUALITY REPORT")
        print(f"{'='*70}")
        print(f"Total Records: {report.total_records}")
        print(f"Success Rate: {report.success_rate:.1f}%")
        print(f"Average Quality Score: {report.average_quality_score:.1f}/100")
        
        if report.average_response_time:
            print(f"Average Response Time: {report.average_response_time:.2f}s")
        
        print(f"\nQuality Distribution:")
        for category, count in report.quality_distribution.items():
            print(f"  {category}: {count}")
        
        print(f"\nScrape Methods Used:")
        for method, count in report.scrape_methods_used.items():
            print(f"  {method}: {count}")
        
        print(f"{'='*70}\n")
    
    def run(self, limit: Optional[int] = None) -> None:
        """Main execution method"""
        
        print(f"\n{'='*70}")
        print("REAL ESTATE SCRAPER V3.1 - Modular Edition")
        print(f"{'='*70}")
        
        # Read URLs
        urls = self.read_urls()
        if not urls:
            logger.error("No URLs to process")
            return
        
        # Apply limit if specified
        if limit:
            urls = urls[:limit]
            print(f"Processing first {limit} URLs (test mode)")
        
        print(f"Total URLs to scrape: {len(urls)}")
        print(f"Async mode: {self.use_async}")
        print(f"Quality threshold: {self.quality_threshold}")
        print(f"{'='*70}\n")
        
        # Scrape URLs
        if self.use_async:
            # Run async scraping
            asyncio.run(self.scrape_async(urls))
        else:
            # Run sync scraping
            self.scrape_sync(urls)
        
        # Save results
        self.save_to_csv()
        self.generate_quality_report()
        
        # Clean up
        self.sync_scraper.close()


def main():
    """Command-line entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description='Real Estate Web Scraper V3.1')
    parser.add_argument('--input', default='real_estate_urls.csv',
                       help='Input CSV file with URLs')
    parser.add_argument('--output', default='real_estate_data.csv',
                       help='Output CSV file for results')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of URLs to process')
    parser.add_argument('--async', dest='use_async', action='store_true', default=True,
                       help='Use async scraping (default: True)')
    parser.add_argument('--sync', dest='use_async', action='store_false',
                       help='Use synchronous scraping')
    parser.add_argument('--concurrent', type=int, default=5,
                       help='Max concurrent requests for async mode')
    parser.add_argument('--threshold', type=int, default=50,
                       help='Minimum quality score threshold')

    args = parser.parse_args()

    # Create scraper instance
    scraper = RealEstateScraperV3(
        input_csv=args.input,
        output_csv=args.output,
        use_async=args.use_async,
        concurrent_limit=args.concurrent,
        quality_threshold=args.threshold
    )
    
    # Run scraper
    scraper.run(limit=args.limit)


if __name__ == '__main__':
    main()
