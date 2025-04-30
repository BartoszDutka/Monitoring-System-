import os
import json
import datetime
import uuid
from functools import wraps
import pandas as pd
from flask import session, abort, render_template_string
from modules.database import get_db_cursor

# Directory for storing generated reports
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
# Create reports directory if it doesn't exist
os.makedirs(REPORTS_DIR, exist_ok=True)

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
    
    def _process_date_range(self):
        """Process date range selection into start and end dates."""
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Only process if custom dates aren't already provided
        if self.date_range != 'custom' or not (self.start_date and self.end_date):
            if self.date_range == 'today':
                self.start_date = today
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'yesterday':
                yesterday = today - datetime.timedelta(days=1)
                self.start_date = yesterday
                self.end_date = yesterday.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'thisWeek':
                # Start from Monday of the current week
                start = today - datetime.timedelta(days=today.weekday())
                self.start_date = start
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'lastWeek':
                # Start from Monday of the previous week
                start = today - datetime.timedelta(days=today.weekday() + 7)
                end = start + datetime.timedelta(days=6)
                self.start_date = start
                self.end_date = end.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'thisMonth':
                # Start from the 1st of the current month
                start = today.replace(day=1)
                self.start_date = start
                self.end_date = today.replace(hour=23, minute=59, second=59)
            elif self.date_range == 'lastMonth':
                # Calculate first day of previous month
                if today.month == 1:
                    start = today.replace(year=today.year-1, month=12, day=1)
                else:
                    start = today.replace(month=today.month-1, day=1)
                # Calculate last day of previous month
                if today.month == 1:
                    end = today.replace(year=today.year-1, month=12, day=31)
                else:
                    last_day = (today.replace(day=1) - datetime.timedelta(days=1)).day
                    end = today.replace(month=today.month-1, day=last_day)
                self.start_date = start
                self.end_date = end.replace(hour=23, minute=59, second=59)
    
    def get_data(self):
        """Fetch data for the report based on report_type."""
        method_name = f'_get_{self.report_type}_data'
        if hasattr(self, method_name):
            return getattr(self, method_name)()
        return []

    def _get_assets_data(self):
        """Get asset inventory data."""
        with get_db_cursor() as cursor:
            sql = """
                SELECT 
                    name, type, serial_number, model, manufacturer, 
                    location, ip_address, mac_address, os_info, 
                    last_seen, status, specifications
                FROM assets
            """
            params = []
            
            # Apply date range if applicable
            if self.start_date and self.end_date:
                sql += " WHERE last_seen BETWEEN %s AND %s"
                params.extend([self.start_date, self.end_date])
            
            # Apply limit
            if self.record_limit:
                sql += f" LIMIT %s"
                params.append(self.record_limit)
                
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def _get_hosts_data(self):
        """Get host status history data."""
        with get_db_cursor() as cursor:
            sql = """
                SELECT host_name, status, timestamp, response_time, details
                FROM host_status_history
                WHERE timestamp BETWEEN %s AND %s
            """
            params = [self.start_date, self.end_date]
            
            # Apply limit
            if self.record_limit:
                sql += f" LIMIT %s"
                params.append(self.record_limit)
                
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def _get_messages_data(self):
        """Get log messages data."""
        with get_db_cursor() as cursor:
            sql = """
                SELECT timestamp, level, severity, category, message, details
                FROM graylog_messages
                WHERE timestamp BETWEEN %s AND %s
            """
            params = [self.start_date, self.end_date]
            
            # Apply limit
            if self.record_limit:
                sql += f" LIMIT %s"
                params.append(self.record_limit)
                
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def _get_tasks_data(self):
        """Get task management data."""
        with get_db_cursor() as cursor:
            sql = """
                SELECT 
                    t.task_id, t.title, t.description, 
                    t.assignee, u.display_name as assignee_name,
                    t.creator, t.status, t.priority, t.due_date,
                    t.created_at, t.updated_at
                FROM tasks t
                LEFT JOIN users u ON t.assignee = u.username
                WHERE t.created_at BETWEEN %s AND %s
            """
            params = [self.start_date, self.end_date]
            
            # Apply limit
            if self.record_limit:
                sql += f" LIMIT %s"
                params.append(self.record_limit)
                
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    def _get_department_data(self):
        """Get department equipment data."""
        with get_db_cursor() as cursor:
            sql = """
                SELECT 
                    e.name, e.type, e.serial_number, e.status,
                    e.assigned_to_department as department,
                    COALESCE(u.display_name, u.username) as assigned_to,
                    e.assigned_date, e.model, e.manufacturer,
                    e.created_at, e.updated_at
                FROM equipment e
                LEFT JOIN users u ON e.assigned_to = u.user_id
                WHERE e.assigned_to_department IS NOT NULL
            """
            params = []
            
            # Apply date range if applicable
            if self.start_date and self.end_date:
                sql += " AND e.updated_at BETWEEN %s AND %s"
                params.extend([self.start_date, self.end_date])
            
            # Apply limit
            if self.record_limit:
                sql += f" LIMIT %s"
                params.append(self.record_limit)
                
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

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

    def generate_report(self):
        """Generate the full report in the specified format."""
        # Get data for the report
        data = self.get_data()
        
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
                'path': filepath,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating Excel report: {str(e)}")
            return {'success': False, 'error': f'Failed to generate Excel report: {str(e)}'}
    
    def _generate_html(self, data):
        """Generate HTML report."""
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
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                    }
                    th, td {
                        padding: 12px 15px;
                        border: 1px solid #ddd;
                        text-align: left;
                    }
                    th {
                        background-color: #f2f2f2;
                        color: #333;
                        font-weight: bold;
                    }
                    tr:nth-child(even) {
                        background-color: #f9f9f9;
                    }
                    tr:hover {
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
                
                {{ table_html }}
                
                <div class="footer">
                    <p>Generated by Monitoring System on {{ generated_date }}</p>
                </div>
            </body>
            </html>
            """
            
            # Generate table HTML
            table_html = df.to_html(classes="data-table", index=False)
            
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
                'path': filepath,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating HTML report: {str(e)}")
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
                'path': filepath,
                'record_count': len(data)
            }
        except Exception as e:
            print(f"Error generating CSV report: {str(e)}")
            return {'success': False, 'error': f'Failed to generate CSV report: {str(e)}'}
    
    def _generate_pdf(self, data):
        """Generate PDF report."""
        # This is a placeholder. For actual PDF generation, you'd need to 
        # install and use a PDF library like ReportLab, WeasyPrint, or xhtml2pdf
        # For now, we'll return an error that PDF generation is not yet supported
        return {
            'success': False,
            'error': 'PDF generation is not yet supported. Please choose a different output format.'
        }
    
    def _save_report_metadata(self, report_id, filename, record_count):
        """Save report metadata to database."""
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
                    'start_date': self.start_date.isoformat() if self.start_date else None,
                    'end_date': self.end_date.isoformat() if self.end_date else None,
                    'fields': self.fields,
                    'record_limit': self.record_limit
                })
            ))


def get_recent_reports(limit=10):
    """Get list of recently generated reports."""
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

def get_report_by_id(report_id):
    """Get report details by ID."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, name, type, format, record_count, 
                generated_by, generated_at, path
            FROM reports
            WHERE id = %s
        """, (report_id,))
        
        return cursor.fetchone()

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
        return False
