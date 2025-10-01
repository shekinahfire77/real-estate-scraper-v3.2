"""JSON exporter"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime, date

from .base import BaseExporter

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """Export data to JSON format"""
    
    def export(self, 
               data: List[Dict[str, Any]], 
               filename: str,
               **kwargs) -> Path:
        """Export data to JSON file
        
        Args:
            data: List of property dictionaries
            filename: Output filename (without extension)
            **kwargs: Additional options (indent, sort_keys, etc.)
            
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
        
        # Get JSON options
        indent = kwargs.get('indent', 2)
        sort_keys = kwargs.get('sort_keys', True)
        ensure_ascii = kwargs.get('ensure_ascii', False)
        
        # Create export structure with metadata
        export_data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_records': len(prepared_data),
                'exporter_version': '1.0.0'
            },
            'properties': prepared_data
        }
        
        if not self.include_metadata:
            export_data = prepared_data
        
        # Write JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    export_data,
                    f,
                    indent=indent,
                    sort_keys=sort_keys,
                    ensure_ascii=ensure_ascii,
                    default=self.json_serializer
                )
            
            logger.info(f"Exported {len(prepared_data)} records to {filepath}")
            
            # Compress if requested
            if self.compress:
                filepath = self.compress_file(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            raise
    
    def json_serializer(self, obj):
        """Custom JSON serializer for non-serializable objects"""
        
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def get_extension(self) -> str:
        """Get file extension"""
        return '.json'
