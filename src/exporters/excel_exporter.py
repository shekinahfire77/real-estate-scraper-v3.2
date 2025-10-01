"""Excel exporter using pandas and openpyxl"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from datetime import datetime

from .base import BaseExporter

logger = logging.getLogger(__name__)


class ExcelExporter(BaseExporter):
    """Export data to Excel format"""
    
    def export(self, 
               data: List[Dict[str, Any]], 
               filename: str,
               **kwargs) -> Path:
        """Export data to Excel file
        
        Args:
            data: List of property dictionaries
            filename: Output filename (without extension)
            **kwargs: Additional options (sheet_name, index, etc.)
            
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
        
        # Format columns
        df = self.format_dataframe(df)
        
        # Get Excel options
        sheet_name = kwargs.get('sheet_name', 'Properties')
        index = kwargs.get('index', False)
        
        # Create Excel writer
        try:
            with pd.ExcelWriter(
                filepath,
                engine='openpyxl',
                datetime_format='YYYY-MM-DD HH:MM:SS'
            ) as writer:
                
                # Write main data
                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=index,
                    freeze_panes=(1, 0)
                )
                
                # Add metadata sheet if requested
                if self.include_metadata:
                    metadata_df = pd.DataFrame([
                        {'Property': 'Export Date', 'Value': datetime.now().isoformat()},
                        {'Property': 'Total Records', 'Value': len(prepared_data)},
                        {'Property': 'Average Price', 'Value': df['price'].mean() if 'price' in df else 'N/A'},
                        {'Property': 'Average Quality Score', 'Value': df['quality_score'].mean() if 'quality_score' in df else 'N/A'}
                    ])
                    
                    metadata_df.to_excel(
                        writer,
                        sheet_name='Metadata',
                        index=False
                    )
                
                # Add summary statistics sheet
                if kwargs.get('include_stats', True) and 'price' in df:
                    stats_df = self.create_statistics_sheet(df)
                    stats_df.to_excel(
                        writer,
                        sheet_name='Statistics',
                        index=False
                    )
                
                # Format the worksheets
                self.format_excel_sheets(writer)
            
            logger.info(f"Exported {len(prepared_data)} records to {filepath}")
            
            # Note: Excel files don't compress well, so skip compression
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export Excel: {e}")
            raise
    
    def format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame columns for Excel
        
        Args:
            df: Input DataFrame
            
        Returns:
            Formatted DataFrame
        """
        
        # Format price columns
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        
        if 'monthly_rent' in df.columns:
            df['monthly_rent'] = pd.to_numeric(df['monthly_rent'], errors='coerce')
        
        # Format date columns
        date_columns = ['created_at', 'updated_at', 'last_scraped_at', 'availability_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Sort by quality score if available
        if 'quality_score' in df.columns:
            df = df.sort_values('quality_score', ascending=False)
        
        return df
    
    def create_statistics_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create statistics summary sheet
        
        Args:
            df: Property DataFrame
            
        Returns:
            Statistics DataFrame
        """
        
        stats = []
        
        # Price statistics
        if 'price' in df.columns:
            price_stats = df['price'].describe()
            for stat_name, value in price_stats.items():
                stats.append({
                    'Metric': f'Price - {stat_name}',
                    'Value': value
                })
        
        # Bedroom distribution
        if 'bedrooms' in df.columns:
            bedroom_dist = df['bedrooms'].value_counts().to_dict()
            for beds, count in sorted(bedroom_dist.items()):
                stats.append({
                    'Metric': f'{beds} Bedroom Properties',
                    'Value': count
                })
        
        # Quality score distribution
        if 'quality_score' in df.columns:
            stats.append({
                'Metric': 'Average Quality Score',
                'Value': df['quality_score'].mean()
            })
            
            # Quality bins
            quality_bins = [
                ('Excellent (90+)', df[df['quality_score'] >= 90].shape[0]),
                ('Good (70-89)', df[(df['quality_score'] >= 70) & (df['quality_score'] < 90)].shape[0]),
                ('Fair (50-69)', df[(df['quality_score'] >= 50) & (df['quality_score'] < 70)].shape[0]),
                ('Poor (<50)', df[df['quality_score'] < 50].shape[0])
            ]
            
            for label, count in quality_bins:
                stats.append({
                    'Metric': f'Quality - {label}',
                    'Value': count
                })
        
        return pd.DataFrame(stats)
    
    def format_excel_sheets(self, writer):
        """Apply formatting to Excel sheets
        
        Args:
            writer: ExcelWriter object
        """
        
        try:
            # Get the workbook and worksheets
            workbook = writer.book
            
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except (TypeError, AttributeError):
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        except Exception as e:
            logger.debug(f"Could not format Excel sheets: {e}")
    
    def get_extension(self) -> str:
        """Get file extension"""
        return '.xlsx'
