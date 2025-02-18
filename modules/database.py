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
    'password': '',
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
    except Exception as e:
        conn.rollback()
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
            if normalized_severity not in allowed_severities:
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
    """Archive asset information"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO assets 
            (name, type, serial_number, model, manufacturer, location, 
            ip_address, mac_address, os_info, status, specifications)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            last_seen = CURRENT_TIMESTAMP,
            status = VALUES(status),
            specifications = VALUES(specifications)
        """, (
            asset_data.get('name'),
            asset_data.get('type'),
            asset_data.get('serial'),
            asset_data.get('model'),
            asset_data.get('manufacturer'),
            asset_data.get('location'),
            asset_data.get('ip'),
            asset_data.get('mac'),
            json.dumps(asset_data.get('os_info', {})),
            asset_data.get('status', 'active'),
            json.dumps(asset_data.get('specs', {}))
        ))

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
        if interval == '1 day':
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

def get_detailed_messages(start_time: datetime, end_time: datetime, limit: int = 2000) -> dict:
    """Get detailed message data from graylog_messages table"""
    with get_db_cursor() as cursor:
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
            ORDER BY timestamp DESC
            LIMIT %s
        """, (start_time, end_time, limit))
        
        messages = cursor.fetchall()
        
        # Calculate statistics for all messages in the time range, not just limited ones
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN severity = 'high' THEN 1 END) as error_count,
                COUNT(CASE WHEN severity = 'medium' THEN 1 END) as warn_count,
                COUNT(CASE WHEN severity = 'low' THEN 1 END) as info_count,
                COUNT(*) as total_count
            FROM graylog_messages
            WHERE timestamp BETWEEN %s AND %s
        """, (start_time, end_time))
        
        stats = cursor.fetchone()
        
        return {
            'messages': messages,
            'stats': stats,
            'total_results': stats['total_count'] if stats else len(messages)  # Use total count from stats
        }
