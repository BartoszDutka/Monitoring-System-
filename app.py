from flask import Flask, render_template, request, jsonify, session
from modules.zabbix import get_hosts, get_unknown_hosts
from modules.graylog import get_logs
from modules.glpi import get_glpi_data
import urllib3
import subprocess
import os
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'twoj_tajny_klucz_do_sesji'  # Dodaj sekretny klucz dla sesji
app.config['SESSION_TYPE'] = 'filesystem'

# Dodaj globalną zmienną dla cache
glpi_cache = None

# Dodaj nowe stałe na górze pliku
ULTRAVNC_PATH = r"C:\igichp\UltraVNC_Viewer\vncviewer_1.2.0.6.exe"
VNC_PASSWORD = "SW!nk@19"

@app.route('/api/glpi/refresh')
def refresh_glpi():
    """Endpoint do odświeżania danych GLPI"""
    try:
        global glpi_cache
        glpi_cache = get_glpi_data()  # Jednorazowe pobranie danych
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/glpi/refresh/<category>')
def refresh_glpi_category(category):
    """Endpoint do odświeżania konkretnej kategorii GLPI"""
    try:
        global glpi_cache
        if glpi_cache is None:
            glpi_cache = get_glpi_data()
        else:
            # Odśwież tylko wybraną kategorię
            new_data = get_glpi_data()
            if category == 'workstations':
                glpi_cache['categorized']['workstations'] = new_data['categorized']['workstations']
            elif category == 'terminals':
                glpi_cache['categorized']['terminals'] = new_data['categorized']['terminals']
            elif category == 'servers':
                glpi_cache['categorized']['servers'] = new_data['categorized']['servers']
            elif category == 'network':
                glpi_cache['network_devices'] = new_data['network_devices']
            elif category == 'printers':
                glpi_cache['printers'] = new_data['printers']
            elif category == 'monitors':
                glpi_cache['monitors'] = new_data['monitors']
            elif category == 'racks':
                glpi_cache['racks'] = new_data['racks']
            elif category == 'others':
                glpi_cache['categorized']['other'] = new_data['categorized']['other']
            
            # Zaktualizuj liczniki
            glpi_cache['category_counts'] = new_data['category_counts']
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    global glpi_cache
    if (glpi_cache is None):
        glpi_cache = get_glpi_data()
    
    zabbix_data = get_hosts()
    graylog_data = get_logs()
    return render_template('index.html', 
                         zabbix=zabbix_data, 
                         graylog=graylog_data, 
                         glpi=glpi_cache, 
                         request=request)

@app.route('/available-hosts')
def available_hosts():
    return render_template('available_hosts.html', request=request)

@app.route('/unavailable-hosts')
def unavailable_hosts():
    return render_template('unavailable_hosts.html', request=request)

@app.route('/unknown-hosts')
def unknown_hosts():
    return render_template('unknown_hosts.html', request=request)

@app.route('/api/data')
def get_data():
    """API endpoint zwraca dane Zabbix, Graylog i informacje o nieznanych hostach"""
    try:
        zabbix_data = get_hosts()
        graylog_data = get_logs()
        unknown_hosts = get_unknown_hosts()
        
        return {
            'zabbix': zabbix_data,
            'graylog': graylog_data,
            'unknown': unknown_hosts
        }
    except Exception as e:
        print(f"Error in get_data: {e}")
        return {
            'zabbix': {"result": []},
            'graylog': {},
            'unknown': []
        }

@app.route('/glpi/workstations')
def glpi_workstations():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Workstations (KS)',
                         devices=glpi_cache['categorized']['workstations'],
                         request=request)

@app.route('/glpi/terminals')
def glpi_terminals():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Terminals (KT)',
                         devices=glpi_cache['categorized']['terminals'],
                         request=request)

@app.route('/glpi/servers')
def glpi_servers():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Servers',
                         devices=glpi_cache['categorized']['servers'],
                         request=request)

@app.route('/glpi/network')
def glpi_network():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Network Devices',
                         devices=glpi_cache['network_devices'],
                         request=request)

@app.route('/glpi/printers')
def glpi_printers():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Printers',
                         devices=glpi_cache['printers'],
                         request=request)

@app.route('/glpi/monitors')
def glpi_monitors():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Monitors',
                         devices=glpi_cache['monitors'],
                         request=request)

@app.route('/glpi/racks')
def glpi_racks():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Racks',
                         devices=glpi_cache['racks'],
                         request=request)

@app.route('/glpi/others')
def glpi_others():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Other Devices',
                         devices=glpi_cache['categorized']['other'],
                         request=request)

@app.route('/connect_vnc', methods=['POST'])
def connect_vnc():
    try:
        data = request.json
        hostname = data.get('hostname')
        if not hostname:
            return jsonify({"status": "error", "message": "No hostname provided"}), 400

        # Przygotuj komendę VNC używając nazwy hosta bezpośrednio
        vnc_command = [
            ULTRAVNC_PATH,
            "-connect", hostname,  # Używamy nazwy hosta zamiast IP
            "-password", VNC_PASSWORD,
            "-dsmplugin", "SecureVNCPlugin.dsm"
        ]

        # Uruchom UltraVNC Viewer
        subprocess.Popen(vnc_command)
        
        return jsonify({"status": "success", "message": f"Connecting to {hostname}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/graylog/logs')
def graylog_logs():
    logs_data = get_logs()
    return render_template('graylog/logs.html', 
                         graylog=logs_data,
                         request=request)

if __name__ == '__main__': 
    app.run(debug=True, host='0.0.0.0', port=5000)