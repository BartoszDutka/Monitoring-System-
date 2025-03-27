import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.database import get_db_cursor

def update_tasks_table():
    """Add attachment_path column to tasks table if it doesn't exist"""
    with get_db_cursor() as cursor:
        # Check if attachment_path column exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE 
                TABLE_SCHEMA = DATABASE() AND
                TABLE_NAME = 'tasks' AND
                COLUMN_NAME = 'attachment_path'
        """)
        
        result = cursor.fetchone()
        if result['count'] == 0:
            print("Adding attachment_path column to tasks table...")
            cursor.execute("""
                ALTER TABLE tasks
                ADD COLUMN attachment_path VARCHAR(255) AFTER related_data
            """)
            print("Column added successfully.")
        else:
            print("attachment_path column already exists.")

if __name__ == "__main__":
    update_tasks_table()
    print("Database update completed.")
