#!/usr/bin/env python3
"""
CLI tool for database management and data export
"""

import click
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import track
from tabulate import tabulate
import pandas as pd

from .database.connection import DatabaseConnection
from .database.crud import PropertyCRUD, ScrapeJobCRUD, FailedUrlCRUD
from .exporters.exporter_factory import ExporterFactory
from .config_manager import ConfigManager

# Rich console for beautiful output
console = Console()

logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', default='config.yaml', help='Configuration file')
@click.pass_context
def cli(ctx, config):
    """Real Estate Scraper CLI - Database Management & Export Tool"""
    
    ctx.ensure_object(dict)
    
    # Load configuration
    config_manager = ConfigManager(config)
    ctx.obj['config'] = config_manager.config
    
    # Initialize database connection
    db_config = config_manager.config.get('database', {})
    ctx.obj['db'] = DatabaseConnection(
        db_type=db_config.get('type', 'sqlite'),
        db_path=db_config.get('sqlite', {}).get('path')
    )


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics"""
    
    console.print("[bold cyan]Database Statistics[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        stats_data = crud.get_statistics()
        
        # Create properties table
        table = Table(title="Property Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Properties", str(stats_data['total_properties']))
        table.add_row("Average Price", f"${stats_data['avg_price']:,.0f}" if stats_data['avg_price'] else "N/A")
        table.add_row("Average Quality Score", f"{stats_data['avg_quality_score']:.1f}" if stats_data['avg_quality_score'] else "N/A")
        
        console.print(table)
        
        # Bedroom distribution
        if stats_data['properties_by_bedrooms']:
            console.print("\n[bold]Properties by Bedrooms:[/bold]")
            for beds, count in sorted(stats_data['properties_by_bedrooms'].items()):
                console.print(f"  {beds} bed: {count}")
        
        # Quality distribution
        if stats_data['properties_by_quality']:
            console.print("\n[bold]Quality Distribution:[/bold]")
            for category, count in stats_data['properties_by_quality'].items():
                console.print(f"  {category}: {count}")


@cli.command()
@click.option('--min-price', type=float, help='Minimum price')
@click.option('--max-price', type=float, help='Maximum price')
@click.option('--bedrooms', type=int, help='Number of bedrooms')
@click.option('--min-quality', type=int, default=50, help='Minimum quality score')
@click.option('--address', help='Address contains text')
@click.option('--limit', type=int, default=20, help='Maximum results')
@click.option('--export', type=click.Choice(['csv', 'json', 'excel', 'parquet']), help='Export results')
@click.pass_context
def search(ctx, min_price, max_price, bedrooms, min_quality, address, limit, export):
    """Search properties in database"""
    
    console.print("[bold cyan]Searching properties...[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        
        results = crud.search_properties(
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            min_quality_score=min_quality,
            address_contains=address,
            limit=limit
        )
        
        if not results:
            console.print("[yellow]No properties found matching criteria[/yellow]")
            return
        
        # Display results
        table = Table(title=f"Found {len(results)} Properties")
        table.add_column("ID", style="cyan")
        table.add_column("Address", style="white")
        table.add_column("Price", style="green")
        table.add_column("Beds", style="yellow")
        table.add_column("Baths", style="yellow")
        table.add_column("Sqft", style="blue")
        table.add_column("Quality", style="magenta")
        
        for prop in results[:10]:  # Show first 10 in table
            table.add_row(
                str(prop.id),
                prop.address[:30] if prop.address else "N/A",
                f"${prop.price:,.0f}" if prop.price else "N/A",
                str(prop.bedrooms) if prop.bedrooms else "N/A",
                f"{prop.bathrooms:.1f}" if prop.bathrooms else "N/A",
                str(prop.square_footage) if prop.square_footage else "N/A",
                str(prop.quality_score) if prop.quality_score else "N/A"
            )
        
        console.print(table)
        
        if len(results) > 10:
            console.print(f"\n[italic]Showing first 10 of {len(results)} results[/italic]")
        
        # Export if requested
        if export:
            export_data(results, f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}", export)
            console.print(f"\n[green]✓ Exported {len(results)} results to {export} format[/green]")


@cli.command()
@click.option('--format', type=click.Choice(['csv', 'json', 'excel', 'parquet']), default='csv', help='Export format')
@click.option('--min-quality', type=int, default=0, help='Minimum quality score')
@click.option('--compress', is_flag=True, help='Compress output file')
@click.option('--output', help='Output filename')
@click.pass_context
def export(ctx, format, min_quality, compress, output):
    """Export all properties to file"""
    
    console.print(f"[bold cyan]Exporting properties to {format.upper()}...[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        
        # Get all properties with quality filter
        properties = crud.search_properties(
            min_quality_score=min_quality,
            limit=100000  # Large limit
        )
        
        if not properties:
            console.print("[yellow]No properties to export[/yellow]")
            return
        
        # Convert to dictionaries
        data = []
        for prop in track(properties, description="Preparing data..."):
            prop_dict = {
                'id': prop.id,
                'url': prop.url,
                'listing_id': prop.listing_id,
                'price': prop.price,
                'address': prop.address,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'square_footage': prop.square_footage,
                'quality_score': prop.quality_score,
                'last_scraped_at': prop.last_scraped_at.isoformat() if prop.last_scraped_at else None
            }
            data.append(prop_dict)
        
        # Export
        filename = output or f"properties_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        exported_file = export_data(data, filename, format, compress)
        
        console.print(f"\n[green]✓ Exported {len(data)} properties to {exported_file}[/green]")


@cli.command()
@click.option('--days', type=int, default=7, help='Properties older than X days')
@click.pass_context
def find_stale(ctx, days):
    """Find properties that need updating"""
    
    console.print(f"[bold cyan]Finding properties not updated in {days} days...[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        
        stale_properties = crud.get_properties_needing_update(
            days_old=days,
            limit=100
        )
        
        if not stale_properties:
            console.print("[green]All properties are up to date![/green]")
            return
        
        # Display stale properties
        table = Table(title=f"Properties Needing Update ({len(stale_properties)} found)")
        table.add_column("ID", style="cyan")
        table.add_column("URL", style="white")
        table.add_column("Last Scraped", style="yellow")
        table.add_column("Days Old", style="red")
        
        for prop in stale_properties[:20]:
            if prop.last_scraped_at:
                days_old = (datetime.utcnow() - prop.last_scraped_at).days
                last_scraped = prop.last_scraped_at.strftime('%Y-%m-%d')
            else:
                days_old = "Never"
                last_scraped = "Never"
            
            table.add_row(
                str(prop.id),
                prop.url[:50] if prop.url else "N/A",
                last_scraped,
                str(days_old)
            )
        
        console.print(table)
        
        if len(stale_properties) > 20:
            console.print(f"\n[italic]Showing first 20 of {len(stale_properties)} stale properties[/italic]")
        
        # Export URLs for re-scraping
        if click.confirm("\nExport URLs for re-scraping?"):
            urls_file = Path('data') / f"stale_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            urls_file.parent.mkdir(exist_ok=True)
            
            with open(urls_file, 'w') as f:
                f.write("url\n")
                for prop in stale_properties:
                    f.write(f"{prop.url}\n")
            
            console.print(f"\n[green]✓ Exported {len(stale_properties)} URLs to {urls_file}[/green]")


@cli.command()
@click.pass_context
def recent_jobs(ctx):
    """Show recent scraping jobs"""
    
    console.print("[bold cyan]Recent Scraping Jobs[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        job_crud = ScrapeJobCRUD(session)
        
        jobs = job_crud.get_recent_jobs(limit=10)
        
        if not jobs:
            console.print("[yellow]No jobs found[/yellow]")
            return
        
        # Display jobs
        table = Table(title="Recent Jobs")
        table.add_column("Job ID", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("URLs", style="yellow")
        table.add_column("Success", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Started", style="blue")
        
        for job in jobs:
            status_color = {
                'completed': 'green',
                'running': 'yellow',
                'failed': 'red',
                'pending': 'white'
            }.get(job.status, 'white')
            
            table.add_row(
                job.job_id[:8],  # Short ID
                f"[{status_color}]{job.status}[/{status_color}]",
                str(job.total_urls) if job.total_urls else "0",
                str(job.successful_scrapes) if job.successful_scrapes else "0",
                str(job.failed_scrapes) if job.failed_scrapes else "0",
                job.started_at.strftime('%Y-%m-%d %H:%M') if job.started_at else "Not started"
            )
        
        console.print(table)


@cli.command()
@click.pass_context
def failed_urls(ctx):
    """Show blocked/failed URLs"""
    
    console.print("[bold cyan]Failed URLs (Circuit Breaker)[/bold cyan]\n")
    
    db = ctx.obj['db']
    
    with db.get_session() as session:
        failed_crud = FailedUrlCRUD(session)
        
        blocked = failed_crud.get_blocked_urls()
        
        if not blocked:
            console.print("[green]No blocked URLs![/green]")
            return
        
        # Display blocked URLs
        table = Table(title=f"Blocked URLs ({len(blocked)} total)")
        table.add_column("URL", style="white")
        table.add_column("Failures", style="red")
        table.add_column("Last Failure", style="yellow")
        table.add_column("Blocked Until", style="cyan")
        
        for failed in blocked[:20]:
            blocked_until = "Permanently" if not failed.blocked_until else failed.blocked_until.strftime('%Y-%m-%d')
            
            table.add_row(
                failed.url[:50],
                str(failed.failure_count),
                failed.last_failed_at.strftime('%Y-%m-%d %H:%M') if failed.last_failed_at else "Unknown",
                blocked_until
            )
        
        console.print(table)
        
        if len(blocked) > 20:
            console.print(f"\n[italic]Showing first 20 of {len(blocked)} blocked URLs[/italic]")
        
        # Option to reset
        if click.confirm("\nReset all blocked URLs?"):
            for failed in blocked:
                failed_crud.reset_url(failed.url)
            console.print("\n[green]✓ All blocked URLs have been reset[/green]")


@cli.command()
@click.option('--older-than', type=int, default=90, help='Delete data older than X days')
@click.option('--confirm', is_flag=True, help='Skip confirmation')
@click.pass_context
def cleanup(ctx, older_than, confirm):
    """Clean up old data from database"""
    
    console.print(f"[bold cyan]Database Cleanup[/bold cyan]\n")
    console.print(f"[yellow]This will delete data older than {older_than} days[/yellow]\n")
    
    if not confirm:
        if not click.confirm("Are you sure you want to proceed?"):
            console.print("[red]Cleanup cancelled[/red]")
            return
    
    db = ctx.obj['db']
    
    # Perform cleanup
    cutoff_date = datetime.utcnow() - timedelta(days=older_than)
    
    with db.get_session() as session:
        # Clean up old scrape results
        from src.database.models import ScrapeResult
        
        old_results = session.query(ScrapeResult).filter(
            ScrapeResult.scraped_at < cutoff_date
        ).count()
        
        if old_results > 0:
            session.query(ScrapeResult).filter(
                ScrapeResult.scraped_at < cutoff_date
            ).delete()
            
            console.print(f"[green]✓ Deleted {old_results} old scrape results[/green]")
        
        # Reset old failed URLs
        from src.database.models import FailedUrl
        
        old_failed = session.query(FailedUrl).filter(
            FailedUrl.last_failed_at < cutoff_date
        ).count()
        
        if old_failed > 0:
            session.query(FailedUrl).filter(
                FailedUrl.last_failed_at < cutoff_date
            ).delete()
            
            console.print(f"[green]✓ Reset {old_failed} old failed URLs[/green]")
    
    # Vacuum database if SQLite
    if db.db_type == 'sqlite':
        console.print("\n[cyan]Optimizing database...[/cyan]")
        db.vacuum_database()
        console.print("[green]✓ Database optimized[/green]")
    
    console.print("\n[bold green]Cleanup complete![/bold green]")


def export_data(data, filename, format_type, compress=False):
    """Helper function to export data"""
    
    exporter = ExporterFactory.create(
        format_type=format_type,
        compress=compress
    )
    
    if not exporter:
        console.print(f"[red]Unsupported format: {format_type}[/red]")
        return None
    
    # Convert SQLAlchemy objects to dictionaries if needed
    if data and hasattr(data[0], '__dict__'):
        dict_data = []
        for item in data:
            item_dict = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
            dict_data.append(item_dict)
        data = dict_data
    
    return exporter.export(data, filename)


if __name__ == '__main__':
    cli()
