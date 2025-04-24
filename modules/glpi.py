import requests
from requests.exceptions import RequestException, Timeout
import time
from config import GLPI_URL, GLPI_USER_TOKEN, GLPI_APP_TOKEN
from flask import session
from modules.database import archive_asset, get_db_cursor
import json
from datetime import datetime
from flask_caching import Cache
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Configure caching
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

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
                    # First try to find a port named "Zarządzanie"
                    for port in ports:
                        if port.get('name') == 'Zarządzanie':
                            if 'ip' in port:
                                return port['ip']
                            if '_ipaddresses' in port:
                                return port['_ipaddresses'][0] if port['_ipaddresses'] else ''
                    
                    # If no management port found, take the first one with an IP
                    for port in ports:
                        if 'ip' in port and port['ip']:
                            return port['ip']
                        if '_ipaddresses' in port and port['_ipaddresses']:
                            return port['_ipaddresses'][0]
            return ''
            
        except Exception as e:
            print(f"Error fetching IP for device {device_id}: {e}")
            return ''
            
    def get_manufacturer_name(self, manufacturer_id, headers):
        """Pobiera nazwę producenta na podstawie ID"""
        if not manufacturer_id:
            return 'Unknown Manufacturer'
            
        try:
            url = f'{self.base_url}/apirest.php/Manufacturer/{manufacturer_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                manufacturer_data = response.json()
                return manufacturer_data.get('name', 'Unknown Manufacturer')
            return 'Unknown Manufacturer'
        except Exception as e:
            print(f"Error fetching manufacturer name for ID {manufacturer_id}: {e}")
            return 'Unknown Manufacturer'
            
    def get_os_name(self, os_id, headers):
        """Pobiera nazwę systemu operacyjnego na podstawie ID"""
        if not os_id:
            return 'Unknown OS'
            
        try:
            url = f'{self.base_url}/apirest.php/OperatingSystem/{os_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                os_data = response.json()
                return os_data.get('name', 'Unknown OS')
            return 'Unknown OS'
        except Exception as e:
            print(f"Error fetching OS name for ID {os_id}: {e}")
            return 'Unknown OS'

    def get_user_info(self, user_id, headers):
        """Pobiera informacje o użytkowniku na podstawie ID"""
        if not user_id:
            return 'Unknown User'
            
        try:
            url = f'{self.base_url}/apirest.php/User/{user_id}'
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                user_data = response.json()
                user_name = user_data.get('name', 'Unknown User')
                # Sometimes firstname and realname are available
                first_name = user_data.get('firstname', '')
                last_name = user_data.get('realname', '')
                
                if first_name and last_name:
                    return f"{first_name} {last_name}"
                return user_name
            return 'Unknown User'
        except Exception as e:
            print(f"Error fetching user info for ID {user_id}: {e}")
            return 'Unknown User'

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
                            # Make sure ID is always present and properly named
                            if 'id' in item:
                                item['ID'] = item['id']  # Add uppercase version for compatibility
                            
                            # Location information
                            if item.get('locations_id'):
                                item['location_name'] = self.get_location_name(
                                    item['locations_id'], 
                                    headers
                                )
                                
                            # Model information    
                            if endpoint == 'Computer' and item.get('computermodels_id'):
                                item['model_name'] = self.get_model_name(
                                    item['computermodels_id'],
                                    headers
                                )
                                
                            # Manufacturer information
                            if item.get('manufacturers_id'):
                                item['manufacturer_name'] = self.get_manufacturer_name(
                                    item['manufacturers_id'],
                                    headers
                                )
                                
                            # OS information
                            if endpoint == 'Computer' and item.get('operatingsystems_id'):
                                item['os_name'] = self.get_os_name(
                                    item['operatingsystems_id'],
                                    headers
                                )
                                
                            # Owner/User information
                            if item.get('users_id_tech'):
                                item['tech_owner_name'] = self.get_user_info(
                                    item['users_id_tech'],
                                    headers
                                )
                            
                            if item.get('users_id'):
                                item['owner_name'] = self.get_user_info(
                                    item['users_id'],
                                    headers
                                )
                                
                            # Add IP address
                            if endpoint == 'Computer':
                                item['ip_address'] = self.get_device_ip(item['id'], headers)
                                # Add network port details
                                self.enrich_device_with_network_info(item, headers)
                    
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
            logger.info("Retrieving devices from assets table in database")
            with get_db_cursor() as cursor:
                # Get all assets from database regardless of last_seen timestamp
                # to ensure we load everything on login
                cursor.execute("""
                    SELECT 
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
                    FROM assets
                """)
                assets = cursor.fetchall()

                if not assets:
                    logger.warning("No assets found in database")
                    return self.get_empty_response()
                
                logger.info(f"Found {len(assets)} assets in database")

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

                # Log some sample assets to verify data loading
                if assets and len(assets) > 0:
                    logger.info(f"Sample asset: {assets[0]['name']}, Type: {assets[0]['type']}")

                for asset in assets:
                    # Konwertuj specifications z JSON na słownik jeśli istnieje
                    if asset['specifications']:
                        try:
                            asset['specifications'] = json.loads(asset['specifications'])
                        except:
                            asset['specifications'] = {}

                    name = asset['name'].upper() if asset['name'] else ''
                    asset_type = asset['type'].lower() if asset['type'] else ''
                    
                    # Enhance device data with proper structure
                    device_data = {
                        'id': asset.get('specifications', {}).get('id', 0),
                        'name': asset['name'],
                        'serial': asset['serial_number'],
                        'model_name': asset['model'],
                        'manufacturer_name': asset['manufacturer'],
                        'location_name': asset['location'],
                        'ip_address': asset['ip_address'],
                        'mac_address': asset['mac_address'],
                        'status': 'active' if asset['status'] == 'active' else 'inactive',
                        'type': asset_type,
                        # Include all original specifications
                        **asset.get('specifications', {})
                    }
                    
                    # Extract OS info
                    if asset['os_info']:
                        try:
                            os_info = json.loads(asset['os_info'])
                            device_data['os_name'] = os_info.get('os', '')
                            device_data['os_version'] = os_info.get('version', '')
                        except:
                            pass

                    # Mapuj urządzenia do odpowiednich kategorii
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

                # Create full response with proper counts and structure
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
                    },
                    'last_refresh': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                logger.info(f"Successfully processed database assets into {response['total_count']} devices")
                return response

        except Exception as e:
            logger.error(f"Error getting devices from database: {e}")
            import traceback
            traceback.print_exc()
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

    def refresh_category_from_api(self, category):
        """Refresh data for a specific category from GLPI API"""
        try:
            if not self.session_token:
                if not self.init_session():
                    return self.get_empty_response()

            headers = {
                'Session-Token': self.session_token,
                'App-Token': self.app_token
            }

            # Base data structure that we'll populate with refreshed data
            base_data = self.get_devices_from_db()
            
            # Category mapping to API endpoint
            category_map = {
                'workstations': {'endpoint': 'Computer', 'filter': lambda c: c.get('name', '').upper().startswith('KS')},
                'terminals': {'endpoint': 'Computer', 'filter': lambda c: c.get('name', '').upper().startswith('KT')},
                'servers': {'endpoint': 'Computer', 'filter': lambda c: c.get('name', '').upper().startswith('SRV')},
                'network': {'endpoint': 'NetworkEquipment', 'filter': None},
                'printers': {'endpoint': 'Printer', 'filter': None},
                'monitors': {'endpoint': 'Monitor', 'filter': None},
                'racks': {'endpoint': 'Rack', 'filter': None},
                'others': {'endpoint': 'Computer', 'filter': lambda c: (not c.get('name', '').upper().startswith('KS') and 
                                                                     not c.get('name', '').upper().startswith('KT') and 
                                                                     not c.get('name', '').upper().startswith('SRV'))}
            }
            
            # Check if category is valid
            if category not in category_map:
                print(f"Invalid category: {category}")
                return base_data
                
            # Get category info
            cat_info = category_map[category]
            
            # Fetch data from API
            items = self.get_all_items(cat_info['endpoint'], headers)
            
            # Apply filter if applicable
            if cat_info['filter']:
                items = [item for item in items if cat_info['filter'](item)]
                
            print(f"Retrieved {len(items)} items for category '{category}'")
                
            # Archive each item to the database
            for item in items:
                if cat_info['endpoint'] == 'Computer':
                    asset_type = 'workstation' if item.get('name', '').upper().startswith('KS') else \
                                 'terminal' if item.get('name', '').upper().startswith('KT') else \
                                 'server' if item.get('name', '').upper().startswith('SRV') else 'other'
                    
                    asset_data = {
                        'name': item.get('name'),
                        'type': asset_type,
                        'serial_number': item.get('serial'),
                        'model': item.get('computermodels_id'),
                        'manufacturer': item.get('manufacturers_id'),
                        'location': item.get('location_name'),
                        'ip_address': self.get_device_ip(item['id'], headers) if 'id' in item else '',
                        'mac_address': item.get('mac'),
                        'os_info': json.dumps({
                            'os': item.get('operatingsystems_id'),
                            'version': item.get('operatingsystemversions_id')
                        }),
                        'status': 'active',
                        'specifications': json.dumps(item)
                    }
                elif cat_info['endpoint'] == 'NetworkEquipment':
                    asset_data = {
                        'name': item.get('name'),
                        'type': 'network',
                        'serial_number': item.get('serial'),
                        'model': item.get('networkequipmentmodels_id'),
                        'manufacturer': item.get('manufacturers_id'),
                        'location': item.get('location_name'),
                        'ip_address': item.get('ip'),
                        'mac_address': item.get('mac'),
                        'os_info': json.dumps({}),
                        'status': 'active',
                        'specifications': json.dumps(item)
                    }
                elif cat_info['endpoint'] == 'Printer':
                    asset_data = {
                        'name': item.get('name'),
                        'type': 'printer',
                        'serial_number': item.get('serial'),
                        'model': item.get('printermodels_id'),
                        'manufacturer': item.get('manufacturers_id'),
                        'location': item.get('location_name'),
                        'ip_address': item.get('ip'),
                        'mac_address': item.get('mac'),
                        'os_info': json.dumps({}),
                        'status': 'active',
                        'specifications': json.dumps(item)
                    }
                else:
                    # Generic handling for other types
                    asset_data = {
                        'name': item.get('name'),
                        'type': cat_info['endpoint'].lower(),
                        'serial_number': item.get('serial'),
                        'model': None,
                        'manufacturer': item.get('manufacturers_id'),
                        'location': item.get('location_name') if 'location_name' in item else None,
                        'ip_address': None,
                        'mac_address': None,
                        'os_info': json.dumps({}),
                        'status': 'active',
                        'specifications': json.dumps(item)
                    }
                    
                # Archive to database
                archive_asset(asset_data)
                
            # Log success
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_logs (source, severity, host_name, message)
                    VALUES ('glpi', 'info', 'system', %s)
                """, (f"GLPI category '{category}' refresh completed successfully",))
            
            # Return updated data from database
            return self.get_devices_from_db()
            
        except Exception as e:
            print(f"Error refreshing category '{category}' from API: {e}")
            import traceback
            traceback.print_exc()
            
            # Log error
            with get_db_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_logs (source, severity, host_name, message)
                    VALUES ('glpi', 'error', 'system', %s)
                """, (f"Error refreshing category '{category}': {str(e)}",))
                
            return base_data

def get_glpi_data(refresh_api=False, from_db=True, category=None):
    """
    Get GLPI data with flexible source control.
    """
    try:
        client = GLPIClient()
        logger.info(f"Getting GLPI data (refresh_api={refresh_api}, from_db={from_db}, category={category})")
        
        # Initialize session if we need API access
        if refresh_api and not client.init_session():
            logger.error("Failed to initialize GLPI session")
            return client.get_empty_response()
        
        if refresh_api:
            # Update database with fresh API data
            if category:
                logger.info(f"Refreshing category '{category}' from API to database")
                api_data = client.refresh_category_from_api(category)
                logger.info(f"Category '{category}' refreshed with {len(api_data.get('computers', []))} computers")
            else:
                logger.info("Refreshing all data from API to database")
                api_data = client.refresh_from_api()
                logger.info(f"All GLPI data refreshed with {len(api_data.get('computers', []))} computers")
        
        # Get data from database if requested
        if from_db:
            logger.info("Getting GLPI data from database")
            db_data = client.get_devices_from_db()
            
            # Validate data structure
            if db_data and isinstance(db_data, dict):
                logger.info(f"Retrieved {db_data.get('total_count', 0)} devices from database")
                return db_data
            
            logger.error("Invalid data format from database")
            return client.get_empty_response()
        
        # Return API data if we did a refresh but don't want DB data
        if refresh_api and not from_db:
            if 'api_data' in locals() and api_data and isinstance(api_data, dict):
                logger.info(f"Returning data from API with {api_data.get('total_count', 0)} total devices")
                return api_data
        
        # Default fallback
        logger.warning("No valid data found, returning empty response")
        return client.get_empty_response()
        
    except Exception as e:
        logger.error(f"Error in get_glpi_data: {e}")
        import traceback
        traceback.print_exc()
        return client.get_empty_response()
