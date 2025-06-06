import mysql.connector
from mysql.connector import pooling
from contextlib import contextmanager
import json
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'monitoring_system',
    'pool_name': 'monitoring_pool',
    'pool_size': 5
}

# Create connection pool
connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn = connection_pool.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
        # Add debug logging for successful transactions
        print("[DB] Transaction committed successfully")
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] Transaction rolled back: {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()

def log_system_event(source, severity, host_name, message):
    """Log system events to database"""
    try:
        with get_db_cursor() as cursor:
            # Ensure severity is one of the allowed ENUM values
            allowed_severities = ['emergency', 'alert', 'critical', 'error', 
                                'warning', 'notice', 'info', 'debug']
            normalized_severity = severity.lower()
            if (normalized_severity not in allowed_severities):
                normalized_severity = 'info'

            cursor.execute("""
                INSERT INTO system_logs 
                (source, severity, host_name, message)
                VALUES (%s, %s, %s, %s)
            """, (
                source[:255] if source else 'unknown',
                normalized_severity,
                host_name[:255] if host_name else 'unknown',
                message[:65535] if message else 'No message'
            ))
            print(f"Logged event: {source} - {severity} - {host_name} - {message[:100]}...")
    except Exception as e:
        print(f"Error logging system event: {e}")

def update_host_status(host_id, host_name, status, response_time=None, details=None):
    """Record host status changes"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO host_status_history 
            (host_id, host_name, status, response_time, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (host_id, host_name, status, response_time, details))

def archive_metrics(host_id: str, metrics: dict, timestamp=None):
    """Archive host metrics to database"""
    with get_db_cursor() as cursor:
        for metric_type, value in metrics.items():
            cursor.execute("""
                INSERT INTO performance_metrics 
                (host_id, metric_type, value, timestamp, details)
                VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), %s)
            """, (host_id, metric_type, value, timestamp, None))

def archive_host_status(host_data: dict):
    """Archive host status and details"""
    with get_db_cursor() as cursor:
        status = host_data.get('availability', 'unknown')
        # Mapowanie statusów na dozwolone wartości ENUM
        status_mapping = {
            'Available': 'available',
            'Unavailable': 'unavailable',
            None: 'unknown',
            '': 'unknown'
        }
        normalized_status = status_mapping.get(status, 'unknown')

        cursor.execute("""
            INSERT INTO host_status_history 
            (host_id, host_name, status, response_time, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            host_data.get('hostid', '0'),
            host_data.get('name', 'Unknown'),
            normalized_status,
            None,  # response_time
            json.dumps(host_data.get('metrics', {}))
        ))

def archive_asset(asset_data: dict):
    """Archive asset information with proper update logic"""
    try:
        with get_db_cursor() as cursor:
            # Najpierw sprawdź czy urządzenie już istnieje
            cursor.execute("""
                SELECT asset_id FROM assets 
                WHERE name = %s
            """, (asset_data.get('name'),))
            
            existing_asset = cursor.fetchone()
            
            if existing_asset:
                # Update istniejącego rekordu
                cursor.execute("""
                    UPDATE assets 
                    SET 
                        type = %s,
                        serial_number = %s,
                        model = %s,
                        manufacturer = %s,
                        location = %s,
                        ip_address = %s,
                        mac_address = %s,
                        os_info = %s,
                        status = %s,
                        specifications = %s,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE asset_id = %s
                """, (
                    asset_data.get('type'),
                    asset_data.get('serial_number'),
                    asset_data.get('model'),
                    asset_data.get('manufacturer'),
                    asset_data.get('location'),
                    asset_data.get('ip_address'),
                    asset_data.get('mac_address'),
                    asset_data.get('os_info'),
                    asset_data.get('status', 'active'),
                    asset_data.get('specifications'),
                    existing_asset['asset_id']
                ))
                print(f"Updated asset: {asset_data.get('name')}")
            else:
                # Wstaw nowy rekord
                cursor.execute("""
                    INSERT INTO assets (
                        name, 
                        type, 
                        serial_number, 
                        model, 
                        manufacturer,
                        location,
                        ip_address,
                        mac_address,
                        os_info,
                        status,
                        specifications,
                        last_seen
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    asset_data.get('name'),
                    asset_data.get('type'),
                    asset_data.get('serial_number'),
                    asset_data.get('model'),
                    asset_data.get('manufacturer'),
                    asset_data.get('location'),
                    asset_data.get('ip_address'),
                    asset_data.get('mac_address'),
                    asset_data.get('os_info'),
                    asset_data.get('status', 'active'),
                    asset_data.get('specifications')
                 ))
                print(f"Inserted new asset: {asset_data.get('name')}")
            
            # Debug log
            print(f"Asset data: {json.dumps(asset_data, indent=2)}")
            
    except Exception as e:
        print(f"Error archiving asset {asset_data.get('name')}: {e}")
        # Print the full error traceback
        import traceback
        traceback.print_exc()

def get_historical_metrics(host_id: str, metric_type: str, start_time: datetime, end_time: datetime) -> list:
    """Get historical metrics for a host"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT metric_type, value, timestamp, details
            FROM performance_metrics
            WHERE host_id = %s 
            AND metric_type = %s
            AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """, (host_id, metric_type, start_time, end_time))
        return cursor.fetchall()

def get_host_status_history(host_id: str, limit: int = 100) -> list:
    """Get historical status changes for a host"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT host_name, status, timestamp, response_time, details
            FROM host_status_history
            WHERE host_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (host_id, limit))
        return cursor.fetchall()

def store_graylog_messages(messages: list):
    """Store Graylog messages in database"""
    with get_db_cursor() as cursor:
        for msg in messages:
            cursor.execute("""
                INSERT INTO graylog_messages 
                (timestamp, level, severity, category, message, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                level = VALUES(level),
                severity = VALUES(severity),
                category = VALUES(category)
            """, (
                msg['timestamp'],
                msg['level'],
                msg['severity'],
                msg['category'],
                msg['message'],
                json.dumps(msg['details'])
            ))

def get_messages_timeline(start_time: datetime, end_time: datetime, interval: str = '5 minutes') -> list:
    """Get message counts grouped by time intervals from graylog_messages table"""
    
    # Map interval strings to MySQL DATE_FORMAT patterns and INTERVAL values
    interval_config = {
        '1 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '1 MINUTE'},
        '2 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '2 MINUTE'},
        '5 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '5 MINUTE'},
        '10 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '10 MINUTE'},
        '15 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '15 MINUTE'},
        '30 minutes': {'format': '%Y-%m-%d %H:%i', 'interval': '30 MINUTE'},
        '60 minutes': {'format': '%Y-%m-%d %H:00', 'interval': '1 HOUR'},
        '1 day': {'format': '%Y-%m-%d', 'interval': '1 DAY'}
    }
    
    interval_settings = interval_config.get(interval, interval_config['5 minutes'])
    format_pattern = interval_settings['format']
    interval_value = interval_settings['interval']
    
    with get_db_cursor() as cursor:
        if (interval == '1 day'):
            # Dla dni używamy DATE() do grupowania
            query = """
                WITH RECURSIVE time_series AS (
                    SELECT DATE(%s) as time_point
                    UNION ALL
                    SELECT DATE_ADD(time_point, INTERVAL 1 DAY)
                    FROM time_series
                    WHERE time_point < DATE(%s)
                )
                SELECT 
                    DATE_FORMAT(ts.time_point, %s) as time_interval,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'high' THEN 1 END), 0) as high_count,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'medium' THEN 1 END), 0) as medium_count,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'low' THEN 1 END), 0) as low_count,
                    COALESCE(COUNT(*), 0) as total_count
                FROM time_series ts
                LEFT JOIN graylog_messages gm ON 
                    DATE(gm.timestamp) = ts.time_point
                GROUP BY ts.time_point
                ORDER BY ts.time_point
            """
        else:
            # Dla minut i godzin używamy standardowego zapytania
            query = f"""
                WITH RECURSIVE time_series AS (
                    SELECT %s as time_point
                    UNION ALL
                    SELECT time_point + INTERVAL {interval_value}
                    FROM time_series
                    WHERE time_point < %s
                )
                SELECT 
                    DATE_FORMAT(ts.time_point, %s) as time_interval,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'high' THEN 1 END), 0) as high_count,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'medium' THEN 1 END), 0) as medium_count,
                    COALESCE(COUNT(CASE WHEN gm.severity = 'low' THEN 1 END), 0) as low_count,
                    COALESCE(COUNT(*), 0) as total_count
                FROM time_series ts
                LEFT JOIN graylog_messages gm ON 
                    gm.timestamp >= ts.time_point 
                    AND gm.timestamp < ts.time_point + INTERVAL {interval_value}
                GROUP BY time_interval
                ORDER BY ts.time_point
            """
        
        cursor.execute(query, (start_time, end_time, format_pattern))
        return cursor.fetchall()

def get_detailed_messages(start_time: datetime, end_time: datetime, limit: int = 300) -> dict:
    """Get detailed message data from graylog_messages table with optimization"""
    try:
        with get_db_cursor() as cursor:
            # Najpierw pobierz ograniczoną liczbę wiadomości
            cursor.execute("""
                SELECT 
                    timestamp,
                    level,
                    severity,
                    category,
                    message,
                    details
                FROM graylog_messages
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp DESC, severity ASC
                LIMIT %s
            """, (start_time, end_time, limit))
            
            messages = cursor.fetchall()
            
            # Policz statystyki tylko dla pobranych wiadomości
            stats = {
                'error_count': sum(1 for msg in messages if msg['severity'] == 'high'),
                'warn_count': sum(1 for msg in messages if msg['severity'] == 'medium'),
                'info_count': sum(1 for msg in messages if msg['severity'] == 'low'),
                'total_count': len(messages)
            }
            
            # Pobierz całkowitą liczbę wiadomości w bazie dla tego okresu
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM graylog_messages
                WHERE timestamp BETWEEN %s AND %s
            """, (start_time, end_time))
            
            total_in_db = cursor.fetchone()['total']
            
            return {
                'messages': messages,
                'stats': stats,
                'total_in_db': total_in_db,
                'total_results': len(messages)
            }
    except Exception as e:
        print(f"Error getting detailed messages: {e}")
        return {
            'messages': [],
            'stats': {'error_count': 0, 'warn_count': 0, 'info_count': 0, 'total_count': 0},
            'total_in_db': 0,
            'total_results': 0
        }

def setup_departments_table():
    """Create departments table if not exists and migrate existing table structure if needed"""
    with get_db_cursor() as cursor:
        # First check if table exists
        cursor.execute("SHOW TABLES LIKE 'departments'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create new table with the correct structure
            cursor.execute("""
                CREATE TABLE departments (
                    name VARCHAR(255) PRIMARY KEY,
                    description_en TEXT,
                    description_pl TEXT,
                    location VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            print("Created departments table with new structure")
        else:
            # Table exists, check for columns
            cursor.execute("DESCRIBE departments")
            columns = {row['Field']: row for row in cursor.fetchall()}
            
            # Check if we need to modify the table
            modifications_needed = False
            
            # Check if description_en and description_pl columns exist
            if 'description_en' not in columns and 'description' in columns:
                # We have the old 'description' column but not the new columns
                # Need to rename existing description to description_en
                cursor.execute("""
                    ALTER TABLE departments 
                    CHANGE COLUMN description description_en TEXT
                """)
                print("Renamed description column to description_en")
                modifications_needed = True
                
            if 'description_pl' not in columns:
                # Add the Polish description column
                cursor.execute("""
                    ALTER TABLE departments
                    ADD COLUMN description_pl TEXT AFTER description_en
                """)
                print("Added description_pl column")
                modifications_needed = True
                
            if modifications_needed:
                print("Successfully migrated departments table structure")
            else:
                print("Departments table already has the correct structure")

def ensure_default_departments():
    """Ensure that default departments exist in the database with translations"""
    default_departments = [
        ('IT', 'Information Technology Department', 'Dział Technologii Informacyjnej', 'Floor 1'),
        ('HR', 'Human Resources', 'Zasoby Ludzkie', 'Floor 2'),
        ('Administration', 'Administration Department', 'Dział Administracji', 'Floor 1'),
        ('Research', 'Research and Development', 'Badania i Rozwój', 'Floor 3'),
        ('Operations', 'Operations Department', 'Dział Operacyjny', 'Floor 2'),
        ('Finance', 'Finance Department', 'Dział Finansowy', 'Floor 2'),
        ('Marketing', 'Marketing Department', 'Dział Marketingu', 'Floor 3'),
        ('Sales', 'Sales Department', 'Dział Sprzedaży', 'Floor 3'),
        ('Support', 'Technical Support', 'Wsparcie Techniczne', 'Floor 1'),
        ('Development', 'Software Development', 'Rozwój Oprogramowania', 'Floor 3')
    ]
    
    with get_db_cursor() as cursor:
        for dept in default_departments:
            cursor.execute("""
                INSERT INTO departments (name, description_en, description_pl, location)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                description_en = VALUES(description_en),
                description_pl = VALUES(description_pl),
                location = VALUES(location)
            """, dept)

def get_departments():
    """Get all departments with their equipment count"""
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT 
                d.name,
                d.description_en,
                d.description_pl,
                d.location,
                COUNT(e.id) as equipment_count
            FROM departments d
            LEFT JOIN equipment e ON e.assigned_to_department = d.name
            GROUP BY d.name, d.description_en, d.description_pl, d.location
            ORDER BY d.name
        ''')
        return cursor.fetchall()

def get_department_info(department_name):
    """Get specific department information"""
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT 
                d.*,
                COUNT(e.id) as equipment_count
            FROM departments d
            LEFT JOIN equipment e ON e.assigned_to_department = d.name
            WHERE d.name = %s
            GROUP BY d.name, d.description_en, d.description_pl, d.location
        ''', (department_name,))
        return cursor.fetchone()
