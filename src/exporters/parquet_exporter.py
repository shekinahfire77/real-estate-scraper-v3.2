"""Parquet exporter for efficient columnar storage"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .base import BaseExporter

logger = logging.getLogger(__name__)


class ParquetExporter(BaseExporter):
    """Export data to Parquet format for efficient storage and analytics"""
    
    def export(self, 
               data: List[Dict[str, Any]], 
               filename: str,
               **kwargs) -> Path:
        """Export data to Parquet file
        
        Args:
            data: List of property dictionaries
            filename: Output filename (without extension)
            **kwargs: Additional options (compression, schema, etc.)
            
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
        
        # Convert to DataFrame
        df = pd.DataFrame(prepared_data)
        
        # Format data types
        df = self.optimize_datatypes(df)
        
        # Get Parquet options
        compression = kwargs.get('compression', 'snappy')  # snappy, gzip, brotli
        
        # Define schema if needed
        schema = self.create_schema(df)
        
        # Write Parquet file
        try:
            # Convert to PyArrow Table
            table = pa.Table.from_pandas(df, schema=schema)
            
            # Write with metadata
            metadata = {
                b'total_records': str(len(prepared_data)).encode(),
                b'export_date': pd.Timestamp.now().isoformat().encode(),
                b'exporter_version': b'1.0.0'
            }
            
            if self.include_metadata:
                existing_metadata = table.schema.metadata or {}
                existing_metadata.update(metadata)
                table = table.replace_schema_metadata(existing_metadata)
            
            # Write Parquet file
            pq.write_table(
                table,
                filepath,
                compression=compression
            )
            
            # Log file size
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            logger.info(f"Exported {len(prepared_data)} records to {filepath} "
                       f"({file_size_mb:.2f} MB with {compression} compression)")
            
            # Note: Parquet is already compressed, no additional compression needed
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export Parquet: {e}")
            raise
    
    def optimize_datatypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame data types for Parquet
        
        Args:
            df: Input DataFrame
            
        Returns:
            Optimized DataFrame
        """
        
        # Convert string columns to categorical if they have low cardinality
        for col in df.select_dtypes(include=['object']).columns:
            if col in df.columns:
                num_unique = df[col].nunique()
                num_total = len(df[col])
                
                # Convert to categorical if less than 50% unique values
                if num_unique / num_total < 0.5:
                    df[col] = df[col].astype('category')
        
        # Optimize numeric types
        for col in df.select_dtypes(include=['int64']).columns:
            if df[col].min() >= 0:
                # Use unsigned if all positive
                if df[col].max() < 255:
                    df[col] = df[col].astype('uint8')
                elif df[col].max() < 65535:
                    df[col] = df[col].astype('uint16')
                elif df[col].max() < 4294967295:
                    df[col] = df[col].astype('uint32')
            else:
                # Use smaller signed types
                if df[col].min() > -128 and df[col].max() < 127:
                    df[col] = df[col].astype('int8')
                elif df[col].min() > -32768 and df[col].max() < 32767:
                    df[col] = df[col].astype('int16')
                elif df[col].min() > -2147483648 and df[col].max() < 2147483647:
                    df[col] = df[col].astype('int32')
        
        # Convert float64 to float32 where possible
        for col in df.select_dtypes(include=['float64']).columns:
            df[col] = df[col].astype('float32')
        
        return df
    
    def create_schema(self, df: pd.DataFrame) -> pa.Schema:
        """Create PyArrow schema for the DataFrame
        
        Args:
            df: Input DataFrame
            
        Returns:
            PyArrow schema
        """
        
        # Let PyArrow infer the schema, but we can customize specific fields
        schema_fields = []
        
        for col in df.columns:
            if col == 'url':
                schema_fields.append(pa.field(col, pa.string()))
            elif col == 'price' or col == 'monthly_rent':
                schema_fields.append(pa.field(col, pa.float32()))
            elif col in ['bedrooms', 'bathrooms']:
                schema_fields.append(pa.field(col, pa.int8()))
            elif col == 'square_footage':
                schema_fields.append(pa.field(col, pa.int32()))
            elif col == 'quality_score':
                schema_fields.append(pa.field(col, pa.int8()))
            elif 'date' in col or 'created' in col or 'updated' in col:
                schema_fields.append(pa.field(col, pa.timestamp('s')))
            else:
                # Let PyArrow infer the type
                continue
        
        # Return None to let PyArrow infer most types
        # Only return custom schema if we need specific control
        return None
    
    def get_extension(self) -> str:
        """Get file extension"""
        return '.parquet'
