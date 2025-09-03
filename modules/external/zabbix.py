import requests
from config import ZABBIX_URL, ZABBIX_TOKEN
from collections import defaultdict
from datetime import datetime
from ..core.database import log_system_event, archive_metrics, archive_host_status

def get_hosts():
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Pobieramy hosty wraz z ich metrykami
        response = requests.post(
            ZABBIX_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {
                    "output": ["hostid", "name", "status"],
                    "selectInterfaces": ["ip", "type", "available"],
                    "selectItems": ["name", "key_", "lastvalue", "units"],
                    "filter": {
                        "status": 0
                    },
                    "selectTriggers": ["description", "status", "state", "lastchange"],
                },
                "auth": ZABBIX_TOKEN,
                "id": 1
            },
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                # Przetwarzamy dane dla każdego hosta
                for host in data['result']:
                    metrics = {
                        'cpu': 'Brak danych',
                        'memory': 'Brak danych',
                        'disk': 'Brak danych',
                        'network': 'Brak danych',
                        'ping': 'Brak danych',
                        'uptime': 'Brak danych',
                        'last_restart': 'Brak danych'
                    }
                    
                    # Status dostępności
                    interface = next((i for i in host.get('interfaces', []) if i['type'] == '1'), None)
                    if interface:
                        host['availability'] = 'Available' if interface['available'] == '1' else 'Unavailable'
                    else:
                        host['availability'] = 'unknown'
                    
                    # Przetwarzanie itemów
                    for item in host.get('items', []):
                        key = item.get('key_', '')
                        value = item.get('lastvalue', '')
                        
                        if 'system.cpu.util' in key:
                            metrics['cpu'] = f"{float(value):.2f}%"
                        elif 'vm.memory.size[total]' in key:
                            metrics['memory'] = f"{float(value)/1024/1024/1024:.2f} GB"
                        elif 'vfs.fs.size' in key and 'total' in key:
                            metrics['disk'] = f"{float(value)/1024/1024/1024:.2f} GB"
                        elif 'net.if.in' in key or 'net.if.out' in key:
                            metrics['network'] = f"{float(value)/1024/1024:.2f} MB/s"
                        elif 'icmpping' in key:
                            # Dodano obsługę polskiej wersji
                            metrics['ping'] = 'OK' if value == '1' else 'Failed'
                        elif 'system.uptime' in key:
                            uptime_seconds = float(value)
                            # Format liczby z przecinkiem zamiast kropki dla Polski i "dni" zamiast "days"
                            uptime_days = uptime_seconds/86400
                            metrics['uptime'] = f"{uptime_days:.1f}".replace('.', ',') + " dni"
                    
                    # Dodanie metryk do hosta
                    host['metrics'] = metrics
                    
                    # Sprawdzanie triggerów (alertów)
                    active_triggers = [t for t in host.get('triggers', []) 
                                    if t['status'] == '0' and t['state'] == '1']
                    
                    # Grupowanie alertów
                    alert_groups = defaultdict(list)
                    for trigger in active_triggers:
                        alert_groups[trigger['description']].append(int(trigger['lastchange']))
                    
                    # Formatowanie zgrupowanych alertów
                    host['alerts'] = [{
                        'description': desc,
                        'count': len(timestamps),
                        'last_occurrence': datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M:%S')
                    } for desc, timestamps in alert_groups.items()]
                    
                    # Log alerts to system_logs
                    if 'alerts' in host:
                        for alert in host['alerts']:
                            severity = 'critical' if 'critical' in alert['description'].lower() else 'warning'
                            log_system_event(
                                source='zabbix',
                                severity=severity,
                                host_name=host['name'],
                                message=alert['description']
                            )
                    
                    # Log status changes
                    if host.get('availability') == 'Unavailable':
                        log_system_event(
                            source='zabbix',
                            severity='error',
                            host_name=host['name'],
                            message=f"Host became unavailable"
                        )
                    
                    # Archiwizuj tylko jeśli mamy podstawowe dane
                    if 'hostid' in host and 'name' in host:
                        if 'metrics' in host:
                            archive_metrics(host['hostid'], host['metrics'])
                        archive_host_status(host)
                    
                return data
            
        return {"result": [], "error": "No data received"}
        
    except Exception as e:
        print(f"Request error: {e}")
        log_system_event('zabbix', 'error', 'system', f"Error fetching hosts: {str(e)}")
        return {"error": str(e)}

def get_unknown_hosts():
    """Get list of hosts with unknown status"""
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            ZABBIX_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {
                    "output": ["hostid", "name", "status"],
                    "selectInterfaces": ["ip", "type", "available"],
                    "filter": {
                        "status": 0
                    }
                },
                "auth": ZABBIX_TOKEN,
                "id": 1
            },
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                unknown_hosts = []
                for host in data['result']:
                    interface = next((i for i in host.get('interfaces', []) if i['type'] == '1'), None)
                    if interface and interface['available'] == '2':  # '2' usually means unknown status
                        unknown_hosts.append({
                            'hostid': host['hostid'],
                            'name': host['name']
                        })
                return unknown_hosts
                
        return []
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting unknown hosts: {e}")
        return []

def get_zabbix_alerts():
    """Get active alerts/triggers from Zabbix"""
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            ZABBIX_URL,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "trigger.get",
                "params": {
                    "output": [
                        "triggerid", "description", "status", "state", 
                        "lastchange", "priority", "value"
                    ],
                    "selectHosts": ["hostid", "name"],
                    "filter": {
                        "status": 0,  # Enabled triggers
                        "state": 1    # Problem state
                    },
                    "sortfield": ["lastchange"],
                    "sortorder": "DESC",
                    "limit": 100
                },
                "auth": ZABBIX_TOKEN,
                "id": 1
            },
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                alerts = []
                for trigger in data['result']:
                    # Get priority level
                    priority_map = {
                        '0': 'not_classified',
                        '1': 'information',
                        '2': 'warning',
                        '3': 'average',
                        '4': 'high',
                        '5': 'disaster'
                    }
                    
                    priority_level = priority_map.get(trigger.get('priority', '0'), 'not_classified')
                    
                    # Format last change time
                    last_change = trigger.get('lastchange', '0')
                    if last_change != '0':
                        last_change_dt = datetime.fromtimestamp(int(last_change))
                        formatted_time = last_change_dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        formatted_time = 'Unknown'
                    
                    # Get host information
                    host_name = 'Unknown Host'
                    if trigger.get('hosts') and len(trigger['hosts']) > 0:
                        host_name = trigger['hosts'][0]['name']
                    
                    alert = {
                        'triggerid': trigger['triggerid'],
                        'description': trigger['description'],
                        'priority': priority_level,
                        'priority_num': trigger.get('priority', '0'),
                        'host_name': host_name,
                        'last_change': formatted_time,
                        'last_change_timestamp': last_change,
                        'status': trigger.get('status', '0'),
                        'state': trigger.get('state', '0'),
                        'value': trigger.get('value', '0')
                    }
                    
                    alerts.append(alert)
                
                return alerts
            
        return []
        
    except Exception as e:
        print(f"Error getting Zabbix alerts: {e}")
        log_system_event('zabbix', 'error', 'system', f"Error fetching alerts: {str(e)}")
        return []