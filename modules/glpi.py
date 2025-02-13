import requests
from requests.exceptions import RequestException, Timeout
import time
from config import GLPI_URL, GLPI_USER_TOKEN, GLPI_APP_TOKEN
from flask import session

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

            # Pobieramy wszystkie urządzenia z timeoutem
            computers = self.get_all_items('Computer', headers)
            network_devices = self.get_all_items('NetworkEquipment', headers)
            printers = self.get_all_items('Printer', headers)
            monitors = self.get_all_items('Monitor', headers)
            racks = self.get_all_items('Rack', headers)
            # Można dodać więcej typów urządzeń jeśli są potrzebne

            # Kategoryzujemy komputery
            categorized_computers = self.categorize_computers(computers)

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

def get_glpi_data():
    try:
        client = GLPIClient()
        return client.get_devices()
    except Exception as e:
        print(f"Error in get_glpi_data: {e}")
        return GLPIClient().get_empty_response()
