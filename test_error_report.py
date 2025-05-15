import sys
import os
import datetime

# Add the parent directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import the ReportGenerator class
from modules.reports import ReportGenerator

def test_error_report():
    print("Testing error report generation...")
    
    # Create a report generator for errors
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - datetime.timedelta(days=7)
    end_date = today.replace(hour=23, minute=59, second=59)
    
    report_generator = ReportGenerator(
        report_type='errors',
        output_format='html',
        date_range='week',
        start_date=start_date,
        end_date=end_date,
        record_limit=100
    )
    
    # Generate the report
    result = report_generator.generate_report()
    
    # Print the result
    print(f"Report generation result: {result}")
    
    if result.get('success'):
        print(f"Report successfully generated: {result.get('filename')}")
        print(f"Records found: {result.get('record_count')}")
    else:
        print(f"Report generation failed: {result.get('error')}")

if __name__ == "__main__":
    test_error_report()
