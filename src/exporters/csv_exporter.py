"""CSV exporter"""

import csv
import logging
from typing import List, Dict, Any
from pathlib import Path

from .base import BaseExporter

logger = logging.getLogger(__name__)


class CSVExporter(BaseExporter):
    """Export data to CSV format"""
    
    def export(self, 
               data: List[Dict[str, Any]], 
               filename: str,
               **kwargs) -> Path:
        """Export data to CSV file
        
        Args:
            data: List of property dictionaries
            filename: Output filename (without extension)
            **kwargs: Additional options (delimiter, quoting, etc.)
            
        Returns:
            Path to exported file
        """
        
        if not data:
            logger.warning("No data to export")
            return None
        
        # Prepare data
        prepared_data = self.prepare_data(data)
        
        # Generate filename
        filepath = self.generate_filename(filename)
        
        # Get CSV options
        delimiter = kwargs.get('delimiter', ',')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        
        # Get all unique keys for headers
        headers = set()
        for item in prepared_data:
            headers.update(item.keys())
        headers = sorted(list(headers))
        
        # Write CSV
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=headers,
                    delimiter=delimiter,
                    quoting=quoting,
                    extrasaction='ignore'
                )
                
                writer.writeheader()
                writer.writerows(prepared_data)
            
            logger.info(f"Exported {len(prepared_data)} records to {filepath}")
            
            # Compress if requested
            if self.compress:
                filepath = self.compress_file(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            raise
    
    def get_extension(self) -> str:
        """Get file extension"""
        return '.csv'
