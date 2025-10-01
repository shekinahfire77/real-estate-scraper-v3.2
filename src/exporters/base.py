"""Base exporter class"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import gzip
import shutil

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for data exporters"""
    
    def __init__(self, 
                 output_dir: str = 'data/exports',
                 compress: bool = False,
                 include_metadata: bool = True):
        """Initialize exporter
        
        Args:
            output_dir: Directory for exports
            compress: Whether to compress output
            include_metadata: Include metadata in export
        """
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.compress = compress
        self.include_metadata = include_metadata
    
    @abstractmethod
    def export(self, 
               data: List[Dict[str, Any]], 
               filename: str,
               **kwargs) -> Path:
        """Export data to file
        
        Args:
            data: List of property dictionaries
            filename: Output filename (without extension)
            **kwargs: Additional exporter-specific options
            
        Returns:
            Path to exported file
        """
        pass
    
    @abstractmethod
    def get_extension(self) -> str:
        """Get file extension for this exporter"""
        pass
    
    def compress_file(self, filepath: Path) -> Path:
        """Compress file with gzip
        
        Args:
            filepath: Path to file to compress
            
        Returns:
            Path to compressed file
        """
        
        compressed_path = filepath.with_suffix(filepath.suffix + '.gz')
        
        with open(filepath, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        filepath.unlink()
        
        logger.info(f"Compressed {filepath} to {compressed_path}")
        
        return compressed_path
    
    def prepare_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare data for export
        
        Args:
            data: Raw data
            
        Returns:
            Prepared data
        """
        
        # Remove internal fields if not including metadata
        if not self.include_metadata:
            cleaned_data = []
            
            metadata_fields = [
                'scrape_method', 
                'has_api_data', 
                'quality_score',
                'created_at',
                'updated_at'
            ]
            
            for item in data:
                cleaned_item = {k: v for k, v in item.items() 
                              if k not in metadata_fields}
                cleaned_data.append(cleaned_item)
            
            return cleaned_data
        
        return data
    
    def generate_filename(self, base_name: str) -> Path:
        """Generate full filename with extension
        
        Args:
            base_name: Base filename without extension
            
        Returns:
            Full file path
        """
        
        extension = self.get_extension()
        filename = f"{base_name}{extension}"
        
        return self.output_dir / filename
