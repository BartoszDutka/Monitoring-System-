import requests
import base64
import json
from datetime import datetime, timedelta
import threading
import time
from config import GRAYLOG_URL, GRAYLOG_USERNAME, GRAYLOG_PASSWORD
from ..core.database import log_system_event

# Dictionary for message translations
MESSAGES = {
    'en': {
        'fetched_batch': "Fetched batch {}, total messages: {}",
        'request_error': "Request error: {}",
        'error_fetching': "Error fetching logs: {}",
        'parsing_error': "Error parsing message: {}"
    },
    'pl': {
        'fetched_batch': "Pobrano partię {}, łączna liczba wiadomości: {}",
        'request_error': "Błąd zapytania: {}",
        'error_fetching': "Błąd podczas pobierania logów: {}",
        'parsing_error': "Błąd podczas przetwarzania wiadomości: {}"
    }
}

# Get translation based on language code
def get_message(key, lang='pl', *args):
    """Get translated message with format arguments"""
    message = MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, ''))
    if args:
        return message.format(*args)
    return message

def extract_nested_json(message_str: str) -> dict:
    try:
        dash_pos = message_str.find('-')
        if dash_pos == -1:
            return None
            
        # Extract process ID and find JSON
        process_id = message_str[:dash_pos].strip()
        json_start = message_str.find('{', dash_pos)
        
        if json_start != -1:
            json_str = message_str[json_start:]
            data = json.loads(json_str)
            data['process_id'] = process_id
            return data
            
        return None
    except json.JSONDecodeError:
        return None

def parse_log_message(raw_message) -> dict:
    try:
        # Parse outer JSON if needed
        message_data = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
        inner_message = message_data.get('message', '')
        nested_data = extract_nested_json(str(inner_message))
        
        if nested_data:            return {
                'process_id': nested_data.get('process_id'),
                'formssessionname': nested_data.get('formsSessionName'),
                'formsformname': nested_data.get('formsFormName'),
                'formsdbsessionid': nested_data.get('formsDbSessionId'),
                'formsusername': nested_data.get('formsUsername'),
                'callsite': nested_data.get('callSite'),
                'thread': nested_data.get('thread'),
                'type': nested_data.get('type', 'INFO'),
                'message': nested_data.get('message', '').strip()
            }
        
        return {'message': inner_message}
    except (json.JSONDecodeError, AttributeError) as e:
        from flask import session, g
        lang = getattr(g, 'language', session.get('language', 'en'))
        print(get_message('parsing_error', lang, str(e)))
        return {'message': str(raw_message)}

class GraylogBuffer:
    def __init__(self):
        self.buffer = {}
        self.lock = threading.Lock()
        self.MAX_BUFFER_AGE = 24 * 60 * 60  # 24 godziny w sekundach
        self.last_refresh_time = None
        self.latest_data = None
        
        # Uruchom wątek czyszczący stare dane
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
    
    def add_logs(self, time_range, logs_data):
        with self.lock:
            self.buffer[time_range] = {
                'data': logs_data,
                'timestamp': datetime.now(),
                'expires': datetime.now() + timedelta(hours=24)
            }
            self.last_refresh_time = time.time()
            self.latest_data = logs_data
    
    def get_logs(self, time_range):
        with self.lock:
            if time_range in self.buffer:
                buffer_data = self.buffer[time_range]
                if datetime.now() < buffer_data['expires']:
                    return buffer_data['data']
                else:
                    del self.buffer[time_range]
            return None
    
    def get_last_refresh(self):
        """Return the timestamp of the last data refresh"""
        with self.lock:
            return self.last_refresh_time
    
    def get_latest_data(self):
        """Return the most recently fetched data"""
        with self.lock:
            return self.latest_data
    
    def _cleanup_old_data(self):
        while True:
            time.sleep(300)  # Sprawdzaj co 5 minut
            with self.lock:
                current_time = datetime.now()
                expired_ranges = [
                    tr for tr, data in self.buffer.items() 
                    if current_time >= data['expires']
                ]
                for tr in expired_ranges:
                    del self.buffer[tr]

# Utworzenie globalnego bufora
graylog_buffer = GraylogBuffer()

def get_logs(time_range_minutes: int = 5, force_refresh: bool = False, lang: str = 'pl') -> dict:
    """
    Fetch and process logs from Graylog with smart caching
    """
    # Sprawdź bufor tylko jeśli nie wymuszono odświeżenia
    if not force_refresh:
        buffered_data = graylog_buffer.get_logs(time_range_minutes)
        if buffered_data:
            return buffered_data

    # Określ minimalny interwał odświeżania (np. 5 minut)
    MIN_REFRESH_INTERVAL = 300  # 5 minut w sekundach
    
    current_time = time.time()
    last_refresh = graylog_buffer.get_last_refresh()
    
    # Jeśli nie minął minimalny interwał, zwróć dane z bufora
    if not force_refresh and last_refresh and (current_time - last_refresh) < MIN_REFRESH_INTERVAL:
        return graylog_buffer.get_latest_data()

    credentials = f"{GRAYLOG_USERNAME}:{GRAYLOG_PASSWORD}"
    headers = {
        "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        all_messages = []
        page = 0
        page_size = 150
        total_desired = 300  # Zmniejszamy limit z 2000 na 300
        
        while len(all_messages) < total_desired:
            # Dodaj parametry paginacji do zapytania
            response = requests.get(
                f"{GRAYLOG_URL}/api/search/universal/relative",
                headers=headers,
                params={
                    "query": "*",
                    "range": time_range_minutes * 60,
                    "limit": page_size,
                    "offset": page * page_size
                },
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("messages", [])
            
            if not messages:  # Jeśli nie ma więcej wiadomości, przerwij
                break
                
            processed_batch = []
            for msg in messages:
                # Parse message content
                parsed_data = parse_log_message(msg.get("message", {}))
                
                # Log to database
                severity_mapping = {
                    "high": "critical",
                    "medium": "warning",
                    "low": "info"
                }
                
                log_system_event(
                    source='graylog',
                    severity=severity_mapping.get(parsed_data.get('severity', 'low'), 'info'),
                    host_name=parsed_data.get('formsdbsessionid', 'unknown'),
                    message=parsed_data.get('message', '')
                )

                # Format timestamp
                timestamp = msg.get("timestamp")
                formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    except (ValueError, AttributeError):
                        pass

                # Determine severity and category
                actual_message = parsed_data.get('message', '').lower()
                level = parsed_data.get('type', 'INFO').upper()
                
                severity = ("high" if level == "ERROR" or "error" in actual_message else
                           "medium" if level == "WARN" or "warning" in actual_message else
                           "low")

                category = ("System Error" if "error" in actual_message else
                           "Security Alert" if any(k in actual_message for k in ["unauthorized", "forbidden", "denied"]) else
                           "Performance Issue" if any(k in actual_message for k in ["timeout", "slow", "performance"]) else
                           "Service Status" if any(k in actual_message for k in ["service", "started", "stopped"]) else
                           "General Warning")

                processed_batch.append({
                    "timestamp": formatted_time,
                    "level": level,
                    "severity": severity,
                    "category": category,
                    "details": {k: v for k, v in parsed_data.items() if k != 'message' and v is noseverity_mappingt None},
                    "message": parsed_data.get('message', '').strip()
                })

            all_messages.extend(processed_batch)
            print(get_message('fetched_batch', lang, page + 1, len(all_messages)))
            
            page += 1
            if len(messages) < page_size:  # Jeśli otrzymaliśmy mniej wiadomości niż rozmiar strony
                break

        # Sort messages and calculate stats
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_messages.sort(key=lambda x: (x["timestamp"], severity_order[x["severity"]]))
        
        stats = {
            "error_count": sum(1 for msg in all_messages if msg["severity"] == "high"),
            "warn_count": sum(1 for msg in all_messages if msg["severity"] == "medium"),
            "info_count": sum(1 for msg in all_messages if msg["severity"] == "low"),
        }

        # Translations for time range
        time_range_msg = {
            'en': f"Last {time_range_minutes} minutes",
            'pl': f"Ostatnie {time_range_minutes} minut"
        }

        result = {
            "logs": all_messages,
            "total_results": len(all_messages),
            "time_range": time_range_msg.get(lang, time_range_msg['en']),
            "query_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "stats": stats,
            "language": lang
        }
          # Store messages in database
        from ..core.database import store_graylog_messages
        store_graylog_messages(all_messages)
        
        graylog_buffer.add_logs(time_range_minutes, result)
        return result

    except requests.exceptions.RequestException as e:
        error_msg = get_message('request_error', lang, str(e))
        print(error_msg)
        log_system_event('graylog', 'error', 'system', get_message('error_fetching', lang, str(e)))
        return {"error": str(e)}