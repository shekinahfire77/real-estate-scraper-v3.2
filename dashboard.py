#!/usr/bin/env python3
"""
Web dashboard for real estate scraper monitoring
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import logging

from src.database.connection import DatabaseConnection
from src.database.crud import PropertyCRUD, ScrapeJobCRUD
from src.config_manager import ConfigManager

# Load configuration
config_manager = ConfigManager()

# Initialize database
db_config = config_manager.get('database', {})
db = DatabaseConnection(
    db_type=db_config.get('type', 'sqlite'),
    db_path=db_config.get('sqlite', {}).get('path')
)

# Initialize Dash app
app = dash.Dash(__name__, title="Real Estate Scraper Dashboard")

# Define app layout
app.layout = html.Div([
    html.Div([
        html.H1("🏠 Real Estate Scraper Dashboard", className="header-title"),
        html.P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", id="last-updated")
    ], className="header"),
    
    # Summary cards
    html.Div([
        html.Div([
            html.H3("Total Properties"),
            html.H2(id="total-properties", children="0")
        ], className="card"),
        
        html.Div([
            html.H3("Average Price"),
            html.H2(id="avg-price", children="$0")
        ], className="card"),
        
        html.Div([
            html.H3("Avg Quality Score"),
            html.H2(id="avg-quality", children="0")
        ], className="card"),
        
        html.Div([
            html.H3("Success Rate"),
            html.H2(id="success-rate", children="0%")
        ], className="card")
    ], className="summary-cards"),
    
    # Charts row 1
    html.Div([
        html.Div([
            html.H3("Price Distribution"),
            dcc.Graph(id="price-distribution")
        ], className="chart-container"),
        
        html.Div([
            html.H3("Properties by Bedrooms"),
            dcc.Graph(id="bedroom-distribution")
        ], className="chart-container")
    ], className="chart-row"),
    
    # Charts row 2
    html.Div([
        html.Div([
            html.H3("Quality Score Distribution"),
            dcc.Graph(id="quality-distribution")
        ], className="chart-container"),
        
        html.Div([
            html.H3("Scraping Performance Over Time"),
            dcc.Graph(id="performance-timeline")
        ], className="chart-container")
    ], className="chart-row"),
    
    # Recent properties table
    html.Div([
        html.H3("Recent High-Quality Properties"),
        html.Div(id="recent-properties-table")
    ], className="table-container"),
    
    # Recent jobs table
    html.Div([
        html.H3("Recent Scraping Jobs"),
        html.Div(id="recent-jobs-table")
    ], className="table-container"),
    
    # Auto-refresh interval
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # Refresh every 30 seconds
        n_intervals=0
    )
], className="dashboard")


# Callback for updating summary cards
@app.callback(
    [Output('total-properties', 'children'),
     Output('avg-price', 'children'),
     Output('avg-quality', 'children'),
     Output('success-rate', 'children'),
     Output('last-updated', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_summary_cards(n):
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        stats = crud.get_statistics()
        
        job_crud = ScrapeJobCRUD(session)
        recent_jobs = job_crud.get_recent_jobs(limit=10)
        
        # Calculate success rate from recent jobs
        if recent_jobs:
            total_success = sum(j.successful_scrapes or 0 for j in recent_jobs)
            total_failed = sum(j.failed_scrapes or 0 for j in recent_jobs)
            total = total_success + total_failed
            success_rate = (total_success / total * 100) if total > 0 else 0
        else:
            success_rate = 0
        
        return (
            f"{stats['total_properties']:,}",
            f"${stats['avg_price']:,.0f}" if stats['avg_price'] else "$0",
            f"{stats['avg_quality_score']:.1f}" if stats['avg_quality_score'] else "0",
            f"{success_rate:.1f}%",
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )


# Callback for price distribution chart
@app.callback(
    Output('price-distribution', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_price_distribution(n):
    with db.get_session() as session:
        from src.database.models import Property
        
        properties = session.query(Property.price).filter(
            Property.price.isnot(None),
            Property.price > 0
        ).all()
        
        prices = [p[0] for p in properties]
        
        if prices:
            fig = go.Figure(data=[go.Histogram(
                x=prices,
                nbinsx=30,
                marker_color='#3498db'
            )])
            
            fig.update_layout(
                xaxis_title="Price ($)",
                yaxis_title="Count",
                showlegend=False,
                height=300
            )
        else:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
        
        return fig


# Callback for bedroom distribution chart
@app.callback(
    Output('bedroom-distribution', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_bedroom_distribution(n):
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        stats = crud.get_statistics()
        
        bedroom_data = stats.get('properties_by_bedrooms', {})
        
        if bedroom_data:
            df = pd.DataFrame(
                list(bedroom_data.items()),
                columns=['Bedrooms', 'Count']
            )
            
            fig = px.bar(
                df,
                x='Bedrooms',
                y='Count',
                color_discrete_sequence=['#2ecc71']
            )
            
            fig.update_layout(
                xaxis_title="Number of Bedrooms",
                yaxis_title="Count",
                showlegend=False,
                height=300
            )
        else:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
        
        return fig


# Callback for quality distribution chart
@app.callback(
    Output('quality-distribution', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_quality_distribution(n):
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        stats = crud.get_statistics()
        
        quality_data = stats.get('properties_by_quality', {})
        
        if quality_data:
            labels = list(quality_data.keys())
            values = list(quality_data.values())
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                marker_colors=['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71']
            )])
            
            fig.update_layout(
                showlegend=True,
                height=300
            )
        else:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
        
        return fig


# Callback for performance timeline
@app.callback(
    Output('performance-timeline', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_performance_timeline(n):
    with db.get_session() as session:
        from src.database.models import ScrapeJob
        
        jobs = session.query(ScrapeJob).filter(
            ScrapeJob.completed_at.isnot(None)
        ).order_by(ScrapeJob.completed_at.desc()).limit(20).all()
        
        if jobs:
            dates = [j.completed_at for j in jobs]
            success_rates = [
                (j.successful_scrapes / (j.successful_scrapes + j.failed_scrapes) * 100)
                if (j.successful_scrapes + j.failed_scrapes) > 0 else 0
                for j in jobs
            ]
            
            fig = go.Figure(data=[go.Scatter(
                x=dates,
                y=success_rates,
                mode='lines+markers',
                marker_color='#9b59b6',
                line_shape='spline'
            )])
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Success Rate (%)",
                showlegend=False,
                height=300
            )
        else:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
        
        return fig


# Callback for recent properties table
@app.callback(
    Output('recent-properties-table', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_recent_properties(n):
    with db.get_session() as session:
        crud = PropertyCRUD(session)
        properties = crud.search_properties(
            min_quality_score=70,
            limit=10
        )
        
        if properties:
            data = []
            for prop in properties:
                data.append({
                    'ID': prop.id,
                    'Address': prop.address[:50] if prop.address else 'N/A',
                    'Price': f"${prop.price:,.0f}" if prop.price else 'N/A',
                    'Beds': prop.bedrooms,
                    'Baths': f"{prop.bathrooms:.1f}" if prop.bathrooms else 'N/A',
                    'Sqft': prop.square_footage,
                    'Quality': prop.quality_score
                })
            
            return dash_table.DataTable(
                data=data,
                columns=[{"name": i, "id": i} for i in data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Quality'},
                        'backgroundColor': '#2ecc71',
                        'color': 'white',
                    }
                ]
            )
        else:
            return html.P("No properties found")


# Callback for recent jobs table
@app.callback(
    Output('recent-jobs-table', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_recent_jobs(n):
    with db.get_session() as session:
        job_crud = ScrapeJobCRUD(session)
        jobs = job_crud.get_recent_jobs(limit=5)
        
        if jobs:
            data = []
            for job in jobs:
                data.append({
                    'Job ID': job.job_id[:8],
                    'Status': job.status,
                    'URLs': job.total_urls or 0,
                    'Success': job.successful_scrapes or 0,
                    'Failed': job.failed_scrapes or 0,
                    'Started': job.started_at.strftime('%Y-%m-%d %H:%M') if job.started_at else 'Not started'
                })
            
            return dash_table.DataTable(
                data=data,
                columns=[{"name": i, "id": i} for i in data[0].keys()],
                style_cell={'textAlign': 'left'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Status', 'filter_query': '{Status} = completed'},
                        'backgroundColor': '#2ecc71',
                        'color': 'white',
                    },
                    {
                        'if': {'column_id': 'Status', 'filter_query': '{Status} = running'},
                        'backgroundColor': '#f39c12',
                        'color': 'white',
                    },
                    {
                        'if': {'column_id': 'Status', 'filter_query': '{Status} = failed'},
                        'backgroundColor': '#e74c3c',
                        'color': 'white',
                    }
                ]
            )
        else:
            return html.P("No jobs found")


# CSS styling
app.index_string = '''<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }
            .dashboard {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }
            .header-title {
                margin: 0;
                font-size: 2.5em;
            }
            .summary-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            .card h3 {
                margin: 0 0 10px 0;
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
            }
            .card h2 {
                margin: 0;
                color: #333;
                font-size: 2em;
            }
            .chart-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .chart-container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .chart-container h3 {
                margin: 0 0 20px 0;
                color: #333;
            }
            .table-container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .table-container h3 {
                margin: 0 0 20px 0;
                color: #333;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>'''


if __name__ == '__main__':
    dashboard_config = config_manager.get('monitoring.dashboard', {})
    
    if dashboard_config.get('enabled', False):
        app.run_server(
            debug=True,
            host=dashboard_config.get('host', 'localhost'),
            port=dashboard_config.get('port', 8050)
        )
    else:
        print("Dashboard is disabled in configuration")
        print("Set monitoring.dashboard.enabled to true in config.yaml to enable")
