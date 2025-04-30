import os
import json
import datetime
import uuid
import traceback
from functools import wraps
import pandas as pd
from flask import session, abort, render_template_string

# Add missing imports for PDF generation with improved error handling
PDF_BACKEND = None
WEASYPRINT_AVAILABLE = False
PDFKIT_AVAILABLE = False  # Define PDFKIT_AVAILABLE at the top level

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    PDF_BACKEND = 'weasyprint'
    print("Using WeasyPrint for PDF generation")
except ImportError:
    WEASYPRINT_AVAILABLE = False
    try:
        import pdfkit
        PDFKIT_AVAILABLE = True
        PDF_BACKEND = 'pdfkit'
        print("Using PDFKit for PDF generation")
    except ImportError:
        PDFKIT_AVAILABLE = False
        print("No PDF generation backend available")

from modules.database import get_db_cursor

# Directory for storing generated reports
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
# Create reports directory if it doesn't exist
os.makedirs(REPORTS_DIR, exist_ok=True)

# Display PDF generation capability
print(f"PDF Generation Capability: WeasyPrint={WEASYPRINT_AVAILABLE}, PDFKit={PDFKIT_AVAILABLE}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

class ReportGenerator:
    """Class for generating various types of reports."""
    
    def __init__(self, report_type, output_format, date_range, fields=None, 
                 start_date=None, end_date=None, record_limit=500, preview=False):
        """Initialize report generator with parameters."""
        self.report_type = report_type
        self.output_format = output_format
        self.date_range = date_range
        self.fields = fields or []
        self.start_date = start_date
        self.end_date = end_date
        self.record_limit = int(record_limit) if record_limit != 'all' else None
        self.preview = preview
        self._process_date_range()
        
        # Debug information
        print(f"ReportGenerator initialized:")
        print(f" - Type: {report_type}")
        print(f" - Format: {output_format}")
        print(f" - Date Range: {date_range}")
        print(f" - Start Date: {start_date}")
        print(f" - End Date: {end_date}")
        print(f" - Fields: {fields}")
        print(f" - Record Limit: {record_limit}")
    
    def _process_date_range(self):
        """Process date range selection into start and end dates."""
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Only process if custom dates aren't already provided
        if self.date_range != 'custom' or not (self.start_date and self.end_date):
            if self.date_range == 'today':
                self.start_date = today
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'week':
                # Last 7 days
                self.start_date = today - datetime.timedelta(days=7)
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'month':
                # Last 30 days
                self.start_date = today - datetime.timedelta(days=30)
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'custom':
                # Custom range is handled by the form inputs
                pass
            else:
                # Default to last 7 days
                self.start_date = today - datetime.timedelta(days=7)
                self.end_date = today.replace(hour=23, minute=59, second=59)
        
        print(f"Date range processed: {self.start_date} to {self.end_date}")
    
    def get_data(self):
        """Fetch data for the report based on report_type."""
        try:
            print(f"Getting data for report type: {self.report_type}")
            method_name = f'_get_{self.report_type}_data'
            
            if hasattr(self, method_name):
                data = getattr(self, method_name)()
                print(f"Retrieved {len(data)} records")
                return data
            else:
                print(f"No method found for report type: {self.report_type}")
                return []
        except Exception as e:
            print(f"Error getting data: {str(e)}")
            traceback.print_exc()
            return []

    def _get_messages_data(self):
        """Get log messages data from graylog_messages table."""
        with get_db_cursor() as cursor:
            try:
                sql = """
                    SELECT 
                        timestamp, 
                        level, 
                        severity, 
                        category, 
                        message, 
                        details
                    FROM graylog_messages
                    WHERE timestamp BETWEEN %s AND %s
                """
                params = [self.start_date, self.end_date]
                
                # Apply limit if specified
                if self.record_limit:
                    sql += " LIMIT %s"
                    params.append(self.record_limit)
                
                print(f"Executing SQL: {sql}")
                print(f"With params: {params}")
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                print(f"Retrieved {len(results)} messages")
                return results
            except Exception as e:
                print(f"Database error in _get_messages_data: {str(e)}")
                traceback.print_exc()
                return []

    def _get_performance_data(self):
        """Get performance metrics data from performance_metrics table."""
        with get_db_cursor() as cursor:
            try:
                sql = """
                    SELECT 
                        metric_id,
                        host_id,
                        metric_type,
                        value,
                        timestamp,
                        details
                    FROM performance_metrics
                    WHERE timestamp BETWEEN %s AND %s
                """
                params = [self.start_date, self.end_date]
                
                # Apply limit if specified
                if self.record_limit:
                    sql += " LIMIT %s"
                    params.append(self.record_limit)
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                print(f"Retrieved {len(results)} performance metrics")
                return results
            except Exception as e:
                print(f"Database error in _get_performance_data: {str(e)}")
                traceback.print_exc()
                return []

    def _get_errors_data(self):
        """Get error logs from system_logs and graylog_messages tables."""
        with get_db_cursor() as cursor:
            try:
                # First try system_logs
                sql = """
                    SELECT 
                        log_id,
                        source,
                        severity,
                        host_name,
                        message,
                        timestamp
                    FROM system_logs
                    WHERE timestamp BETWEEN %s AND %s
                    AND severity IN ('emergency', 'alert', 'critical', 'error')
                """
                params = [self.start_date, self.end_date]
                
                # Apply limit if specified
                if self.record_limit:
                    sql += " LIMIT %s"
                    params.append(self.record_limit)
                
                cursor.execute(sql, tuple(params))
                results = cursor.fetchall()
                
                # If no results from system_logs, try graylog_messages
                if not results:
                    sql = """
                        SELECT 
                            id as log_id,
                            'graylog' as source,
                            severity,
                            category as host_name,
                            message,
                            timestamp
                        FROM graylog_messages
                        WHERE timestamp BETWEEN %s AND %s
                        AND (severity = 'high' OR level IN ('ERROR', 'CRITICAL', 'FATAL'))
                    """
                    params = [self.start_date, self.end_date]
                    
                    # Apply limit if specified
                    if self.record_limit:
                        sql += " LIMIT %s"
                        params.append(self.record_limit)
                    
                    cursor.execute(sql, tuple(params))
                    results = cursor.fetchall()
                
                print(f"Retrieved {len(results)} error records")
                return results
            except Exception as e:
                print(f"Database error in _get_errors_data: {str(e)}")
                traceback.print_exc()
                return []

    def _get_summary_data(self):
        """Generate a summary report combining data from multiple tables."""
        try:
            summary_data = []
            
            # Get system stats - distinct host count
            with get_db_cursor() as cursor:
                try:
                    # Count of unique hosts from host_status_history
                    cursor.execute("""
                        SELECT COUNT(DISTINCT host_id) as host_count
                        FROM host_status_history
                        WHERE timestamp BETWEEN %s AND %s
                    """, (self.start_date, self.end_date))
                    host_count = cursor.fetchone()
                    
                    # Status counts
                    cursor.execute("""
                        SELECT 
                            status, 
                            COUNT(*) as count
                        FROM host_status_history
                        WHERE timestamp BETWEEN %s AND %s
                        GROUP BY status
                    """, (self.start_date, self.end_date))
                    status_counts = cursor.fetchall()
                    
                    # Log counts by severity
                    cursor.execute("""
                        SELECT 
                            severity,
                            COUNT(*) as count
                        FROM system_logs
                        WHERE timestamp BETWEEN %s AND %s
                        GROUP BY severity
                    """, (self.start_date, self.end_date))
                    severity_counts = cursor.fetchall()
                    
                    # Asset counts by type 
                    cursor.execute("""
                        SELECT 
                            type,
                            COUNT(*) as count
                        FROM assets
                        WHERE last_seen BETWEEN %s AND %s
                        GROUP BY type
                    """, (self.start_date, self.end_date))
                    asset_counts = cursor.fetchall()
                    
                    # Add to summary data
                    summary_data.append({
                        'category': 'System Overview',
                        'metric': 'Monitored Hosts',
                        'value': host_count['host_count'] if host_count else 0,
                        'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                    })
                    
                    for status in status_counts:
                        summary_data.append({
                            'category': 'Host Status',
                            'metric': f"{status['status'].capitalize()} Hosts",
                            'value': status['count'],
                            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                        })
                    
                    for severity in severity_counts:
                        summary_data.append({
                            'category': 'System Logs',
                            'metric': f"{severity['severity'].capitalize()} Logs",
                            'value': severity['count'],
                            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                        })
                    
                    for asset in asset_counts:
                        summary_data.append({
                            'category': 'Assets',
                            'metric': f"{asset['type'].capitalize()} Devices",
                            'value': asset['count'],
                            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                        })
                    
                    # If still no data, add a placeholder
                    if not summary_data:
                        summary_data.append({
                            'category': 'System Overview',
                            'metric': 'No Data',
                            'value': 'No records found for the selected period',
                            'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                        })
                    
                    return summary_data
                
                except Exception as e:
                    print(f"Error generating summary data: {str(e)}")
                    traceback.print_exc()
                    
                    # Return a placeholder if there's an error
                    return [{
                        'category': 'Error',
                        'metric': 'Database Error',
                        'value': str(e),
                        'period': f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
                    }]
        except Exception as e:
            print(f"General error in summary report: {str(e)}")
            traceback.print_exc()
            return []

    def filter_fields(self, data):
        """Filter data to include only selected fields."""
        if not self.fields or not data:
            return data
        
        filtered_data = []
        for item in data:
            filtered_item = {}
            for field in self.fields:
                if field in item:
                    filtered_item[field] = item[field]
            filtered_data.append(filtered_item)
        return filtered_data
    
    def generate_html_preview(self, data):
        """Generate HTML preview of the report."""
        if not data:
            return "<p>No data available for the selected criteria.</p>"
        
        try:
            # Convert to pandas DataFrame for easy HTML table generation
            df = pd.DataFrame(data)
            
            # Limit preview to a small number of records
            preview_count = min(10, len(df))
            preview_df = df.head(preview_count)
            
            # Generate nice HTML table
            table_html = preview_df.to_html(classes="preview-table", index=False)
            
            preview_html = f"""
            <div class="preview-stats">
                <div class="preview-stat">
                    <span class="stat-label">Total Records:</span>
                    <span class="stat-value">{len(df)}</span>
                </div>
                <div class="preview-stat">
                    <span class="stat-label">Showing:</span>
                    <span class="stat-value">{preview_count} records</span>
                </div>
                <div class="preview-stat">
                    <span class="stat-label">Report Type:</span>
                    <span class="stat-value">{self.report_type.capitalize()}</span>
                </div>
                <div class="preview-stat">
                    <span class="stat-label">Date Range:</span>
                    <span class="stat-value">{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}</span>
                </div>
            </div>
            <div class="preview-table-container">
                {table_html}
            </div>
            <p class="preview-note">This is a preview of your report. The actual report may contain more records.</p>
            <style>
                .preview-stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
                    gap: 10px;
                    margin-bottom: 15px;
                }}
                .preview-stat {{
                    background-color: #f5f5f5;
                    padding: 8px 12px;
                    border-radius: 6px;
                }}
                .stat-label {{
                    display: block;
                    font-size: 0.8rem;
                    color: #666;
                }}
                .stat-value {{
                    font-weight: 500;
                    color: #333;
                }}
                .preview-table-container {{
                    max-height: 250px;
                    overflow-y: auto;
                    margin-bottom: 15px;
                }}
                .preview-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.9rem;
                }}
                .preview-table thead {{
                    position: sticky;
                    top: 0;
                    background-color: #f0f0f0;
                    z-index: 10;
                }}
                .preview-table th, 
                .preview-table td {{
                    padding: 8px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                .preview-note {{
                    font-style: italic;
                    color: #666;
                    font-size: 0.85rem;
                }}
            </style>
            """
            return preview_html
        except Exception as e:
            print(f"Error generating HTML preview: {str(e)}")
            traceback.print_exc()
            return f"<p>Error generating preview: {str(e)}</p>"

    def generate_report(self):
        """Generate the full report in the specified format."""
        try:
            # Get data for the report
            data = self.get_data()
            
            if not data:
                print("No data returned from get_data()")
                return {
                    'success': False,
                    'error': 'No data available for the report'
                }
            
            # Filter fields if needed
            if self.fields:
                data = self.filter_fields(data)
            
            # If this is just a preview request, return HTML preview
            if self.preview:
                preview_html = self.generate_html_preview(data)
                return {
                    'success': True,
                    'preview_html': preview_html
                }
            
            # Generate report based on the specified format
            if self.output_format == 'excel':
                return self._generate_excel(data)
            elif self.output_format == 'html':
                return self._generate_html(data)
            elif self.output_format == 'csv':
                return self._generate_csv(data)
            elif self.output_format == 'pdf':
                return self._generate_pdf(data)
            else:
                return {
                    'success': False,
                    'error': 'Unsupported output format'
                }
        except Exception as e:
            print(f"Error in generate_report: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': f'Report generation failed: {str(e)}'}
    
    def _generate_excel(self, data):
        """Generate Excel report."""
        if not data:
            return {'success': False, 'error': 'No data available for the report'}
        
        try:
            # Create a DataFrame and export to Excel
            df = pd.DataFrame(data)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.report_type}_report_{timestamp}.xlsx"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            # Create Excel writer
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=self.report_type.capitalize())
                
                # Auto-adjust column widths
                for column in df:
                    column_width = max(df[column].astype(str).map(len).max(), len(column)) + 2
                    col_idx = df.columns.get_loc(column) + 1
                    writer.sheets[self.report_type.capitalize()].column_dimensions[chr(64 + col_idx)].width = column_width
            
            # Store report metadata
            report_id = str(uuid.uuid4())
            self._save_report_metadata(report_id, filename, len(data))
            
            return {
                'success': True,
                'report_id': report_id,
                'filename': filename,
                'path': filename,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating Excel report: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': f'Failed to generate Excel report: {str(e)}'}
    
    def _generate_html(self, data):
        """Generate HTML report with improved table formatting."""
        if not data:
            return {'success': False, 'error': 'No data available for the report'}
        
        try:
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.report_type}_report_{timestamp}.html"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            # Create HTML template
            html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{{ report_title }} | Monitoring System</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 20px;
                        color: #333;
                    }
                    h1 {
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }
                    .report-header {
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    .report-metadata {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin-bottom: 15px;
                    }
                    .metadata-item {
                        flex: 1 0 200px;
                    }
                    .metadata-item h3 {
                        margin: 0 0 5px 0;
                        font-size: 14px;
                        color: #666;
                    }
                    .metadata-item p {
                        margin: 0;
                        font-weight: bold;
                        color: #333;
                    }
                    table.data-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        font-size: 14px;
                    }
                    .data-table th, 
                    .data-table td {
                        padding: 10px;
                        border: 1px solid #ddd;
                        text-align: left;
                    }
                    .data-table th {
                        background-color: #f2f2f2;
                        color: #333;
                        font-weight: bold;
                        position: sticky;
                        top: 0;
                    }
                    .data-table tr:nth-child(even) {
                        background-color: #f9f9f9;
                    }
                    .data-table tr:hover {
                        background-color: #f1f1f1;
                    }
                    .footer {
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 10px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                    }
                    
                    /* Responsive design */
                    @media (max-width: 768px) {
                        .report-metadata {
                            flex-direction: column;
                            gap: 10px;
                        }
                        .data-table {
                            font-size: 12px;
                        }
                        .data-table th, 
                        .data-table td {
                            padding: 6px;
                        }
                        
                        /* Enable horizontal scrolling for tables on small screens */
                        .table-container {
                            width: 100%;
                            overflow-x: auto;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="report-header">
                    <h1>{{ report_title }}</h1>
                    <div class="report-metadata">
                        <div class="metadata-item">
                            <h3>Report Type:</h3>
                            <p>{{ report_type }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Date Range:</h3>
                            <p>{{ date_range }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Generated On:</h3>
                            <p>{{ generated_date }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Total Records:</h3>
                            <p>{{ record_count }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="table-container">
                    {{ table_html }}
                </div>
                
                <div class="footer">
                    <p>Generated by Monitoring System on {{ generated_date }}</p>
                </div>
            </body>
            </html>
            """
            
            # Generate table HTML with better styling
            table_html = df.to_html(classes="data-table", index=False, border=1)
            
            # Fix styling issue with table attributes
            table_html = table_html.replace('<table border="1" class="dataframe data-table">', 
                                          '<table class="data-table" cellspacing="0" cellpadding="5">')
            
            # Prepare context for rendering
            report_title = f"{self.report_type.capitalize()} Report"
            date_range_text = f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
            generated_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Render HTML template
            html_content = render_template_string(
                html_template,
                report_title=report_title,
                report_type=self.report_type.capitalize(),
                date_range=date_range_text,
                generated_date=generated_date,
                record_count=len(data),
                table_html=table_html
            )
            
            # Write HTML to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Store report metadata
            report_id = str(uuid.uuid4())
            self._save_report_metadata(report_id, filename, len(data))
            
            return {
                'success': True,
                'report_id': report_id,
                'filename': filename,
                'path': filename,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating HTML report: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': f'Failed to generate HTML report: {str(e)}'}
    
    def _generate_csv(self, data):
        """Generate CSV report."""
        if not data:
            return {'success': False, 'error': 'No data available for the report'}
        
        try:
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            
            # Generate filename
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.report_type}_report_{timestamp}.csv"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            # Write CSV file
            df.to_csv(filepath, index=False)
            
            # Store report metadata
            report_id = str(uuid.uuid4())
            self._save_report_metadata(report_id, filename, len(data))
            
            return {
                'success': True,
                'report_id': report_id,
                'filename': filename,
                'path': filename,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating CSV report: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': f'Failed to generate CSV report: {str(e)}'}
    
    def _generate_pdf(self, data):
        """Generate PDF report using available PDF backend."""
        if not data:
            return {'success': False, 'error': 'No data available for the report'}
        
        if not WEASYPRINT_AVAILABLE and not PDFKIT_AVAILABLE:
            return {'success': False, 'error': 'No PDF generation backend available. Please run install_pdf_deps.py to install necessary dependencies.'}
        
        try:
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            
            # Generate filenames
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            html_filename = f"{self.report_type}_report_{timestamp}.html"
            pdf_filename = f"{self.report_type}_report_{timestamp}.pdf"
            html_path = os.path.join(REPORTS_DIR, html_filename)
            pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
            
            # Create HTML template directly (don't rely on previous HTML generation)
            html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>{{ report_title }} | Monitoring System</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 20px;
                        color: #333;
                    }
                    h1 {
                        color: #2c3e50;
                        border-bottom: 2px solid #3498db;
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }
                    .report-header {
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                    }
                    .report-metadata {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 20px;
                        margin-bottom: 15px;
                    }
                    .metadata-item {
                        flex: 1 0 200px;
                    }
                    .metadata-item h3 {
                        margin: 0 0 5px 0;
                        font-size: 14px;
                        color: #666;
                    }
                    .metadata-item p {
                        margin: 0;
                        font-weight: bold;
                        color: #333;
                    }
                    table.data-table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                        font-size: 14px;
                    }
                    .data-table th, 
                    .data-table td {
                        padding: 10px;
                        border: 1px solid #ddd;
                        text-align: left;
                    }
                    .data-table th {
                        background-color: #f2f2f2;
                        color: #333;
                        font-weight: bold;
                    }
                    .data-table tr:nth-child(even) {
                        background-color: #f9f9f9;
                    }
                    .footer {
                        text-align: center;
                        margin-top: 30px;
                        padding-top: 10px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                    }
                </style>
            </head>
            <body>
                <div class="report-header">
                    <h1>{{ report_title }}</h1>
                    <div class="report-metadata">
                        <div class="metadata-item">
                            <h3>Report Type:</h3>
                            <p>{{ report_type }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Date Range:</h3>
                            <p>{{ date_range }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Generated On:</h3>
                            <p>{{ generated_date }}</p>
                        </div>
                        <div class="metadata-item">
                            <h3>Total Records:</h3>
                            <p>{{ record_count }}</p>
                        </div>
                    </div>
                </div>
                
                <div class="table-container">
                    {{ table_html|safe }}
                </div>
                
                <div class="footer">
                    <p>Generated by Monitoring System on {{ generated_date }}</p>
                </div>
            </body>
            </html>
            """
            
            # Fix table HTML to ensure proper rendering in PDF
            # Generate table HTML with better styling for PDF
            table_html = df.to_html(classes="data-table", index=False)
            
            # Ensure there are no malformed tags or attributes in table
            table_html = table_html.replace('<table border="1" class="dataframe data-table">', 
                                          '<table class="data-table">')
            
            # Prepare context for rendering
            report_title = f"{self.report_type.capitalize()} Report"
            date_range_text = f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
            generated_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Render HTML template
            html_content = render_template_string(
                html_template,
                report_title=report_title,
                report_type=self.report_type.capitalize(),
                date_range=date_range_text,
                generated_date=generated_date,
                record_count=len(data),
                table_html=table_html
            )
            
            # Write HTML to file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML file created: {html_path}")
            
            # Convert HTML to PDF using available backend
            if WEASYPRINT_AVAILABLE:
                try:
                    # Use HTML string directly rather than file to avoid encoding issues
                    HTML(string=html_content, base_url=REPORTS_DIR).write_pdf(pdf_path)
                    print(f"PDF generated successfully using WeasyPrint: {pdf_path}")
                except Exception as weasy_error:
                    print(f"WeasyPrint error: {str(weasy_error)}")
                    if PDFKIT_AVAILABLE:
                        print("Falling back to PDFKit")
                        pdfkit.from_string(html_content, pdf_path)
                    else:
                        raise weasy_error
            elif PDFKIT_AVAILABLE:
                try:
                    # Use string-based conversion rather than file-based
                    pdfkit.from_string(html_content, pdf_path)
                    print(f"PDF generated successfully using PDFKit: {pdf_path}")
                except Exception as pdfkit_error:
                    print(f"PDFKit error: {str(pdfkit_error)}")
                    raise pdfkit_error
            else:
                # This should not happen due to the check at the top, but just in case
                return {'success': False, 'error': 'No PDF generation backend available'}
            
            # Store report metadata
            report_id = str(uuid.uuid4())
            self._save_report_metadata(report_id, pdf_filename, len(data))
            
            return {
                'success': True,
                'report_id': report_id,
                'filename': pdf_filename,
                'path': pdf_filename,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating PDF report: {str(e)}")
            traceback.print_exc()
            
            # Create a fallback simple text file with installation instructions
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.report_type}_report_{timestamp}.txt"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Report Type: {self.report_type.capitalize()}\n")
                f.write(f"Date Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Records: {len(data)}\n\n")
                f.write("PDF generation failed. Please use Excel or HTML format.\n\n")
                f.write("To enable PDF generation, please run:\n")
                f.write("python install_pdf_deps.py\n\n")
                f.write(f"Error: {str(e)}")
            
            # Store report metadata
            report_id = str(uuid.uuid4())
            self._save_report_metadata(report_id, filename, len(data))
            
            return {
                'success': False,
                'error': 'PDF generation failed. Please run install_pdf_deps.py to install necessary dependencies.',
                'report_id': report_id,
                'filename': filename,
                'path': filename
            }
    
    def _save_report_metadata(self, report_id, filename, record_count):
        """Save report metadata to database with improved error handling."""
        try:
            with get_db_cursor() as cursor:
                # First, check if reports table exists; if not, create it
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        type VARCHAR(50) NOT NULL,
                        format VARCHAR(10) NOT NULL,
                        record_count INT NOT NULL,
                        generated_by VARCHAR(50) NOT NULL,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        path VARCHAR(255) NOT NULL,
                        report_params JSON DEFAULT NULL
                    )
                """)
                
                # Convert dates to strings if they exist
                start_date_str = self.start_date.isoformat() if hasattr(self.start_date, 'isoformat') else str(self.start_date) if self.start_date else None
                end_date_str = self.end_date.isoformat() if hasattr(self.end_date, 'isoformat') else str(self.end_date) if self.end_date else None
                
                # Save report metadata
                cursor.execute("""
                    INSERT INTO reports 
                    (id, name, type, format, record_count, generated_by, path, report_params)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    report_id, 
                    filename, 
                    self.report_type, 
                    self.output_format,
                    record_count,
                    session.get('username', 'system'),
                    filename,  # Store just the filename, not full path
                    json.dumps({
                        'date_range': self.date_range,
                        'start_date': start_date_str,
                        'end_date': end_date_str,
                        'fields': self.fields,
                        'record_limit': self.record_limit
                    })
                ))
        except Exception as e:
            print(f"Error saving report metadata: {str(e)}")
            traceback.print_exc()

# Functions for getting and managing reports
def get_recent_reports(limit=10):
    """Get list of recently generated reports."""
    try:
        with get_db_cursor() as cursor:
            # First check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'reports'
                ) as table_exists
            """)
            
            result = cursor.fetchone()
            if not result or not result.get('table_exists'):
                return []
            
            # Get recent reports
            cursor.execute("""
                SELECT 
                    id, name, type, format, record_count, 
                    generated_by, generated_at, path
                FROM reports
                ORDER BY generated_at DESC
                LIMIT %s
            """, (limit,))
            
            return cursor.fetchall()
    except Exception as e:
        print(f"Error getting recent reports: {str(e)}")
        traceback.print_exc()
        return []

def get_report_by_id(report_id):
    """Get report details by ID."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, name, type, format, record_count, 
                    generated_by, generated_at, path
                FROM reports
                WHERE id = %s
            """, (report_id,))
            
            return cursor.fetchone()
    except Exception as e:
        print(f"Error getting report by ID: {str(e)}")
        traceback.print_exc()
        return None

def delete_report(report_id):
    """Delete a report by ID."""
    try:
        # Get report info first
        report = get_report_by_id(report_id)
        if not report:
            return False
        
        # Delete file
        filepath = os.path.join(REPORTS_DIR, report['path'])
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Delete from database
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM reports WHERE id = %s", (report_id,))
        
        return True
    except Exception as e:
        print(f"Error deleting report: {str(e)}")
        traceback.print_exc()
        return False
