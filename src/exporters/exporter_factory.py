"""Factory for creating exporters"""

import logging
from typing import Optional

from .base import BaseExporter
from .csv_exporter import CSVExporter
from .json_exporter import JSONExporter
from .excel_exporter import ExcelExporter
from .parquet_exporter import ParquetExporter

logger = logging.getLogger(__name__)


class ExporterFactory:
    """Factory for creating data exporters"""
    
    EXPORTERS = {
        'csv': CSVExporter,
        'json': JSONExporter,
        'excel': ExcelExporter,
        'xlsx': ExcelExporter,
        'parquet': ParquetExporter
    }
    
    @classmethod
    def create(cls, 
               format_type: str,
               output_dir: str = 'data/exports',
               compress: bool = False,
               include_metadata: bool = True) -> Optional[BaseExporter]:
        """Create an exporter for the specified format
        
        Args:
            format_type: Export format (csv, json, excel, parquet)
            output_dir: Output directory
            compress: Whether to compress output
            include_metadata: Include metadata in export
            
        Returns:
            Exporter instance or None if format not supported
        """
        
        format_type = format_type.lower()
        
        if format_type not in cls.EXPORTERS:
            logger.error(f"Unsupported export format: {format_type}")
            logger.info(f"Supported formats: {', '.join(cls.EXPORTERS.keys())}")
            return None
        
        exporter_class = cls.EXPORTERS[format_type]
        
        return exporter_class(
            output_dir=output_dir,
            compress=compress,
            include_metadata=include_metadata
        )
    
    @classmethod
    def get_supported_formats(cls) -> list:
        """Get list of supported export formats
        
        Returns:
            List of format names
        """
        
        return list(cls.EXPORTERS.keys())
