import requests
from requests.exceptions import RequestException, Timeout
import time
from config import GLPI_URL, GLPI_USER_TOKEN, GLPI_APP_TOKEN
from flask import session
from modules.database import archive_asset, get_db_cursor
import json
from datetime import datetime

class GLPIClient:
    def __init__(self):
        self.base_url = GLPI_URL
        self.user_token = GLPI_USER_TOKEN
        self.app_token = GLPI_APP_TOKEN
        self.session_token = None
        self.timeout = 10

    def init_session(self):
        try:
            headers = {
                'Authorization': f'user_token {self.user_token}',
                'App-Token': self.app_token
            }
            
            response = requests.get(
                f'{self.base_url}/apirest.php/initSession',
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.session_token = response.json().get('session_token')
                return True
        except (RequestException, Timeout) as e:
            print(f"Error initializing GLPI session: {e}")
        return False

    def get_device_networkports(self, device_id, headers):
        """Pobiera porty sieciowe dla urządzenia"""
        try:
            url = f'{self.base_url}/apirest.php/NetworkPort?criteria[0][field]=items_id&criteria[0][value]={device_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching network ports for device {device_id}: {e}")
            return []

    def enrich_device_with_network_info(self, device, headers):
        """Dodaje informacje o sieci do urządzenia"""
        if 'id' in device:
            networkports = self.get_device_networkports(device['id'], headers)
            device['networkports'] = []
            
            for port in networkports:
                # Pobierz adres IP dla portu sieciowego
                try:
                    ip_url = f'{self.base_url}/apirest.php/IPAddress?criteria[0][field]=items_id&criteria[0][value]={port["id"]}'
                    ip_response = requests.get(
                        ip_url,
                        headers=headers,
                        verify=False,
                        timeout=self.timeout
                    )
                    
                    if ip_response.status_code == 200:
                        ip_data = ip_response.json()
                        if ip_data:
                            port['ipaddress'] = ip_data[0].get('name', '')
                            device['networkports'].append({
                                'name': port.get('name', ''),
                                'ipaddress': ip_data[0].get('name', '')
                            })
                except Exception as e:
                    print(f"Error fetching IP for port {port['id']}: {e}")

        return device

    def get_location_name(self, location_id, headers):
        """Pobiera nazwę lokalizacji na podstawie ID"""
        try:
            url = f'{self.base_url}/apirest.php/Location/{location_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                location_data = response.json()
                return location_data.get('name', 'Unknown Location')
            return 'Unknown Location'
        except Exception as e:
            print(f"Error fetching location name for ID {location_id}: {e}")
            return 'Unknown Location'

    def get_model_name(self, model_id, headers):
        """Pobiera nazwę modelu na podstawie ID"""
        try:
            url = f'{self.base_url}/apirest.php/ComputerModel/{model_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                model_data = response.json()
                return model_data.get('name', 'Unknown Model')
            return 'Unknown Model'
        except Exception as e:
            print(f"Error fetching model name for ID {model_id}: {e}")
            return 'Unknown Model'

    def should_refresh_cache(self, cache_key):
        """Sprawdza czy należy odświeżyć cache"""
        if cache_key not in session:
            return True
            
        cache_time = session.get(f'{cache_key}_time', 0)
        # Zwiększamy czas ważności cache do 15 minut
        return (time.time() - cache_time) > 900  # 15 minut

    def get_device_ip(self, device_id, headers):
        """Pobiera adres IP dla urządzenia z portu zarządzania"""
        try:
            url = f'{self.base_url}/apirest.php/NetworkPort'
            params = {
                'criteria[0][field]': 'items_id',
                'criteria[0][value]': device_id,
                'criteria[1][field]': 'itemtype',
                'criteria[1][value]': 'Computer',
                'criteria[2][field]': 'name',
                'criteria[2][value]': 'Zarządzanie'  # Szukamy portu o nazwie "Zarządzanie"
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                ports = response.json()
                if ports and len(ports) > 0:
                    port = ports[0]  # Bierzemy pierwszy znaleziony port zarządzania
                    # Adres IP powinien być bezpośrednio w porcie w polu 'NetworkName'
                    if 'ip' in port:
                        return port['ip']
                    if '_ipaddresses' in port:
                        return port['_ipaddresses'][0] if port['_ipaddresses'] else ''
            return ''
            
        except Exception as e:
            print(f"Error fetching IP for device {device_id}: {e}")
            return ''

    def get_all_items(self, endpoint, headers):
        """Pobiera wszystkie elementy z danego endpointu"""
        cache_key = f'glpi_{endpoint}_cache'
        
        if not self.should_refresh_cache(cache_key):
            print(f"Using cached data for {endpoint}")
            return session.get(cache_key, [])

        try:
            all_items = []
            start = 0
            limit = 999

            while True:
                url = f'{self.base_url}/apirest.php/{endpoint}?range={start}-{start + limit}'
                print(f"Fetching {url}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    verify=False,
                    timeout=self.timeout
                )
                
                if response.status_code in [200, 206]:
                    items = response.json()
                    if not items or not isinstance(items, list):
                        break
                        
                    if items and isinstance(items, list):
                        for item in items:
                            if item.get('locations_id'):
                                item['location_name'] = self.get_location_name(
                                    item['locations_id'], 
                                    headers
                                )
                            if endpoint == 'Computer' and item.get('computermodels_id'):
                                item['computermodels_id'] = self.get_model_name(
                                    item['computermodels_id'],
                                    headers
                                )
                    
                    all_items.extend(items)
                    print(f"Fetched {len(items)} items from {endpoint}, total: {len(all_items)}")
                    
                    if len(items) < limit:
                        break
                    
                    start += len(items)
                    time.sleep(0.1)
                else:
                    break

            print(f"Final count for {endpoint}: {len(all_items)} items")
            
            if all_items:
                session[cache_key] = all_items
                session[f'{cache_key}_time'] = time.time()
                session.modified = True
            
            return all_items

        except Exception as e:
            print(f"Error in get_all_items for {endpoint}: {e}")
            return session.get(cache_key, [])

    def categorize_computers(self, computers):
        categories = {
            'workstations': [],  # KS
            'terminals': [],     # KT
            'servers': [],       # SRV
            'other': []
        }
        
        for computer in computers:
            name = computer.get('name', '').upper()
            if name.startswith('KS'):
                categories['workstations'].append(computer)
            elif name.startswith('KT'):
                categories['terminals'].append(computer)
            elif name.startswith('SRV'):
                categories['servers'].append(computer)
            else:
                categories['other'].append(computer)
        
        return categories

    def get_devices(self):
        try:
            if not self.session_token:
                if not self.init_session():
                    return self.get_empty_response()

            headers = {
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }

            # Pobieramy wszystkie urządzenia
            computers = self.get_all_items('Computer', headers)
            network_devices = self.get_all_items('NetworkEquipment', headers)
            printers = self.get_all_items('Printer', headers)
            monitors = self.get_all_items('Monitor', headers)
            racks = self.get_all_items('Rack', headers)

            # Kategoryzujemy komputery
            categorized_computers = self.categorize_computers(computers)

            # Archiwizuj dane o urządzeniach
            for computer in computers:
                # Mapowanie pól do struktury bazy danych
                asset_data = {
                    'name': computer.get('name'),
                    'type': 'workstation' if computer.get('name', '').upper().startswith('KS') else
                           'terminal' if computer.get('name', '').upper().startswith('KT') else
                           'server' if computer.get('name', '').upper().startswith('SRV') else
                           'other',
                    'serial_number': computer.get('serial'),
                    'model': computer.get('computermodels_id'),  # To już jest nazwa modelu dzięki get_model_name
                    'manufacturer': computer.get('manufacturers_id'),
                    'location': computer.get('location_name'),  # To już jest nazwa lokacji dzięki get_location_name
                    'ip_address': self.get_device_ip(computer['id'], headers),
                    'mac_address': computer.get('mac'),
                    'os_info': json.dumps({
                        'os': computer.get('operatingsystems_id'),
                        'version': computer.get('operatingsystemversions_id')
                    }),
                    'status': 'active',  # Domyślny status
                    'specifications': json.dumps(computer)  # Pełne dane jako JSON w specifications
                }
                print(f"Sending computer data to archive: {asset_data['name']}")
                archive_asset(asset_data)

            # Podobnie dla urządzeń sieciowych
            for device in network_devices:
                asset_data = {
                    'name': device.get('name'),
                    'type': 'network',
                    'serial_number': device.get('serial'),
                    'model': device.get('networkequipmentmodels_id'),
                    'manufacturer': device.get('manufacturers_id'),
                    'location': device.get('location_name'),
                    'ip_address': device.get('ip'),
                    'mac_address': device.get('mac'),
                    'os_info': json.dumps({}),
                    'status': 'active',
                    'specifications': json.dumps(device)
                }
                archive_asset(asset_data)

            # I dla drukarek
            for printer in printers:
                asset_data = {
                    'name': printer.get('name'),
                    'type': 'printer',
                    'serial_number': printer.get('serial'),
                    'model': printer.get('printermodels_id'),
                    'manufacturer': printer.get('manufacturers_id'),
                    'location': printer.get('location_name'),
                    'ip_address': printer.get('ip'),
                    'mac_address': printer.get('mac'),
                    'os_info': json.dumps({}),
                    'status': 'active',
                    'specifications': json.dumps(printer)
                }
                archive_asset(asset_data)

            return {
                'computers': computers,
                'categorized': categorized_computers,
                'network_devices': network_devices,
                'printers': printers,
                'monitors': monitors,
                'racks': racks,
                'total_count': len(computers) + len(network_devices) + len(printers) + len(monitors) + len(racks),
                'category_counts': {
                    'workstations': len(categorized_computers['workstations']),
                    'terminals': len(categorized_computers['terminals']),
                    'servers': len(categorized_computers['servers']),
                    'other': len(categorized_computers['other']),  # Licznik dla innych urządzeń
                    'network': len(network_devices),
                    'printers': len(printers),
                    'monitors': len(monitors),
                    'racks': len(racks)
                }
            }
        except Exception as e:
            print(f"Error in get_devices: {e}")
            return self.get_empty_response()

    def get_empty_response(self):
        """Zwraca pustą strukturę danych w przypadku błędu"""
        empty_categories = {
            'workstations': [],
            'terminals': [],
            'servers': [],
            'other': []
        }
        return {
            'computers': [],
            'categorized': empty_categories,
            'network_devices': [],
            'printers': [],
            'monitors': [],
            'racks': [],
            'total_count': 0,
            'category_counts': {
                'workstations': 0,
                'terminals': 0,
                'servers': 0,
                'other': 0,
                'network': 0,
                'printers': 0,
                'monitors': 0,
                'racks': 0
            }
        }

    def get_devices_from_db(self):
        """Get devices from local database"""
        try:
            with get_db_cursor() as cursor:
                # Pobierz wszystkie aktywa z bazy danych
                cursor.execute("""
                    SELECT 
                        name,
                        type,
                        serial_number,
                        model,
                        location,
                        status,
                        specifications
                    FROM assets 
                    WHERE last_seen >= NOW() - INTERVAL 24 HOUR
                    OR last_seen IS NULL
                """)
                assets = cursor.fetchall()

                if not assets:
                    print("No assets found in database")
                    return self.get_empty_response()

                # Kategoryzuj aktywa
                categorized = {
                    'workstations': [],
                    'terminals': [],
                    'servers': [],
                    'other': []
                }
                network_devices = []
                printers = []
                monitors = []
                racks = []

                for asset in assets:
                    # Konwertuj specifications z JSON na słownik jeśli istnieje
                    if asset['specifications']:
                        try:
                            asset['specifications'] = json.loads(asset['specifications'])
                        except:
                            asset['specifications'] = {}

                    name = asset['name'].upper() if asset['name'] else ''
                    asset_type = asset['type'].lower() if asset['type'] else ''
                    
                    # Mapuj urządzenia do odpowiednich kategorii
                    device_data = {
                        'name': asset['name'],
                        'serial_number': asset['serial_number'],
                        'model': asset['model'],
                        'location': asset['location'],
                        'type': asset['type'],
                        'status': asset['status'],
                        'specifications': asset['specifications']
                    }

                    if name.startswith('KS'):
                        categorized['workstations'].append(device_data)
                    elif name.startswith('KT'):
                        categorized['terminals'].append(device_data)
                    elif name.startswith('SRV'):
                        categorized['servers'].append(device_data)
                    elif asset_type == 'network':
                        network_devices.append(device_data)
                    elif asset_type == 'printer':
                        printers.append(device_data)
                    elif asset_type == 'monitor':
                        monitors.append(device_data)
                    elif asset_type == 'rack':
                        racks.append(device_data)
                    else:
                        categorized['other'].append(device_data)

                response = {
                    'computers': [*categorized['workstations'], *categorized['terminals'], 
                                *categorized['servers'], *categorized['other']],
                    'categorized': categorized,
                    'network_devices': network_devices,
                    'printers': printers,
                    'monitors': monitors,
                    'racks': racks,
                    'total_count': len(assets),
                    'category_counts': {
                        'workstations': len(categorized['workstations']),
                        'terminals': len(categorized['terminals']),
                        'servers': len(categorized['servers']),
                        'other': len(categorized['other']),
                        'network': len(network_devices),
                        'printers': len(printers),
                        'monitors': len(monitors),
                        'racks': len(racks)
                    }
                }

                return response

        except Exception as e:
            print(f"Error getting devices from database: {e}")
            return self.get_empty_response()

    def get_last_refresh_time(self):
        """Get the last time data was refreshed from GLPI"""
        try:
            with get_db_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(last_seen) as last_refresh
                    FROM assets
                """)
                result = cursor.fetchone()
                return result['last_refresh'] if result and result['last_refresh'] else None
        except Exception as e:
            print(f"Error getting last refresh time: {e}")
            return None

    def refresh_from_api(self):
        """Refresh data from GLPI API"""
        try:
            if not self.session_token:
                if not self.init_session():
                    return self.get_empty_response()

            headers = {
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }

            # Pobierz świeże dane z API
            computers = self.get_all_items('Computer', headers)
            network_devices = self.get_all_items('NetworkEquipment', headers)
            printers = self.get_all_items('Printer', headers)
            monitors = self.get_all_items('Monitor', headers)
            racks = self.get_all_items('Rack', headers)

            # Kategoryzuj komputery
            categorized_computers = self.categorize_computers(computers)

            # Archiwizuj dane o urządzeniach
            print("Rozpoczynam archiwizację urządzeń...")

            # Archiwizuj komputery
            for computer in computers:
                asset_data = {
                    'name': computer.get('name'),
                    'type': 'computer',
                    'serial_number': computer.get('serial'),
                    'model': computer.get('computermodels_id'),
                    'manufacturer': computer.get('manufacturers_id'),
                    'location': computer.get('location_name'),
                    'ip_address': self.get_device_ip(computer['id'], headers),
                    'mac_address': computer.get('mac'),
                    'os_info': json.dumps({
                        'os': computer.get('operatingsystems_id'),
                        'version': computer.get('operatingsystemversions_id')
                    }),
                    'status': 'active',
                    'specifications': json.dumps(computer)
                }
                print(f"Archiwizuję komputer: {asset_data['name']}")
                archive_asset(asset_data)

            # Archiwizuj urządzenia sieciowe
            for device in network_devices:
                asset_data = {
                    'name': device.get('name'),
                    'type': 'network',
                    'serial_number': device.get('serial'),
                    'model': device.get('networkequipmentmodels_id'),
                    'manufacturer': device.get('manufacturers_id'),
                    'location': device.get('location_name'),
                    'ip_address': device.get('ip'),
                    'mac_address': device.get('mac'),
                    'os_info': json.dumps({}),
                    'status': 'active',
                    'specifications': json.dumps(device)
                }
                print(f"Archiwizuję urządzenie sieciowe: {asset_data['name']}")
                archive_asset(asset_data)

            # Archiwizuj drukarki
            for printer in printers:
                asset_data = {
                    'name': printer.get('name'),
                    'type': 'printer',
                    'serial_number': printer.get('serial'),
                    'model': printer.get('printermodels_id'),
                    'manufacturer': printer.get('manufacturers_id'),
                    'location': printer.get('location_name'),
                    'ip_address': printer.get('ip'),
                    'mac_address': printer.get('mac'),
                    'os_info': json.dumps({}),
                    'status': 'active',
                    'specifications': json.dumps(printer)
                }
                print(f"Archiwizuję drukarkę: {asset_data['name']}")
                archive_asset(asset_data)

            print("Zakończono archiwizację urządzeń")

            # Log success
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_logs (source, severity, host_name, message)
                    VALUES ('glpi', 'info', 'system', 'GLPI data refresh completed successfully')
                """)

            return {
                'computers': computers,
                'categorized': categorized_computers,
                'network_devices': network_devices,
                'printers': printers,
                'monitors': monitors,
                'racks': racks,
                'total_count': len(computers) + len(network_devices) + len(printers) + len(monitors) + len(racks),
                'category_counts': {
                    'workstations': len(categorized_computers['workstations']),
                    'terminals': len(categorized_computers['terminals']),
                    'servers': len(categorized_computers['servers']),
                    'other': len(categorized_computers['other']),
                    'network': len(network_devices),
                    'printers': len(printers),
                    'monitors': len(monitors),
                    'racks': len(racks)
                }
            }
        except Exception as e:
            print(f"Error refreshing GLPI data: {e}")
            # Log error
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_logs (source, severity, host_name, message)
                    VALUES ('glpi', 'error', 'system', %s)
                """, (str(e),))
            return self.get_empty_response()

def get_glpi_data(refresh=False):
    """Get GLPI data - from database or API if refresh requested"""
    try:
        client = GLPIClient()
        if refresh:
            return client.refresh_from_api()
        return client.get_devices_from_db()
    except Exception as e:
        print(f"Error in get_glpi_data: {e}")
        return GLPIClient().get_empty_response()
