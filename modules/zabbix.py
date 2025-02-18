import requests
from config import ZABBIX_URL, ZABBIX_TOKEN
from collections import defaultdict
from datetime import datetime
from modules.database import log_system_event, archive_metrics, archive_host_status

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
                        'cpu': 'N/A',
                        'memory': 'N/A',
                        'disk': 'N/A',
                        'network': 'N/A',
                        'ping': 'N/A',
                        'uptime': 'N/A',
                        'last_restart': 'N/A'
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
                            metrics['ping'] = 'OK' if value == '1' else 'Failed'
                        elif 'system.uptime' in key:
                            uptime_seconds = float(value)
                            metrics['uptime'] = f"{uptime_seconds/86400:.1f} days"
                    
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