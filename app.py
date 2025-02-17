from flask import Flask, render_template, request, jsonify, session, flash
from modules.zabbix import get_hosts, get_unknown_hosts
from modules.graylog import get_logs
from modules.glpi import get_glpi_data
from modules.ldap_auth import authenticate_user, get_user_info
from config import *  # Importujemy wszystkie zmienne konfiguracyjne
import urllib3
import subprocess
import os
from functools import wraps
from flask import redirect, url_for
from werkzeug.utils import secure_filename
import time  # Dodaj na początku pliku z innymi importami
from modules.user_data import update_user_avatar, get_user_avatar
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'twoj_tajny_klucz_do_sesji'  # Poprawiony błąd składni
app.config['SESSION_TYPE'] = 'filesystem'

# Dodaj globalną zmienną dla cache
glpi_cache = None

# Dodaj nowe stałe na górze pliku
ULTRAVNC_PATH = r"C:\igichp\UltraVNC_Viewer\vncviewer_1.2.0.6.exe"
VNC_PASSWORD = "SW!nk@19"

# Dodaj konfigurację dla uploadów
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB w bajtach

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Upewnij się, że folder istnieje
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def utility_processor():
    return dict(time=time)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password')
            return render_template('login.html', error='Please provide both username and password')
            
        if authenticate_user(username, password):
            user_info = get_user_info(username)
            if user_info:
                # Dodaj zapisany avatar do informacji o użytkowniku
                saved_avatar = get_user_avatar(username)
                if saved_avatar and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], saved_avatar)):
                    user_info['avatar'] = saved_avatar
                
                session['logged_in'] = True
                session['username'] = username
                session['user_info'] = user_info
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Could not retrieve user information')
        
        return render_template('login.html', error='Invalid username or password')
    
    if session.get('logged_in'):
        return redirect(url_for('index'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/glpi/refresh')
@login_required
def refresh_glpi():
    """Endpoint do odświeżania danych GLPI"""
    try:
        global glpi_cache
        glpi_cache = get_glpi_data()  # Jednorazowe pobranie danych
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/glpi/refresh/<category>')
@login_required
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
@login_required
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
@login_required
def available_hosts():
    return render_template('available_hosts.html', request=request)

@app.route('/unavailable-hosts')
@login_required
def unavailable_hosts():
    return render_template('unavailable_hosts.html', request=request)

@app.route('/unknown-hosts')
@login_required
def unknown_hosts():
    return render_template('unknown_hosts.html', request=request)

@app.route('/api/data')
@login_required
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
@login_required
def glpi_workstations():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Workstations (KS)',
                         devices=glpi_cache['categorized']['workstations'],
                         request=request)

@app.route('/glpi/terminals')
@login_required
def glpi_terminals():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Terminals (KT)',
                         devices=glpi_cache['categorized']['terminals'],
                         request=request)

@app.route('/glpi/servers')
@login_required
def glpi_servers():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Servers',
                         devices=glpi_cache['categorized']['servers'],
                         request=request)

@app.route('/glpi/network')
@login_required
def glpi_network():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Network Devices',
                         devices=glpi_cache['network_devices'],
                         request=request)

@app.route('/glpi/printers')
@login_required
def glpi_printers():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Printers',
                         devices=glpi_cache['printers'],
                         request=request)

@app.route('/glpi/monitors')
@login_required
def glpi_monitors():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Monitors',
                         devices=glpi_cache['monitors'],
                         request=request)

@app.route('/glpi/racks')
@login_required
def glpi_racks():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Racks',
                         devices=glpi_cache['racks'],
                         request=request)

@app.route('/glpi/others')
@login_required
def glpi_others():
    global glpi_cache
    if glpi_cache is None:
        glpi_cache = get_glpi_data()
    return render_template('glpi_category.html',
                         category_title='Other Devices',
                         devices=glpi_cache['categorized']['other'],
                         request=request)

@app.route('/connect_vnc', methods=['POST'])
@login_required
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
@login_required
def graylog_logs():
    logs_data = get_logs()
    return render_template('graylog/logs.html', 
                         graylog=logs_data,
                         request=request)

@app.route('/graylog/messages-over-time')
@login_required
def graylog_messages_over_time():
    # Pobierz początkowe dane
    logs_data = get_logs(time_range_minutes=60)  # domyślnie 1 godzina
    return render_template('graylog/messages_over_time.html', graylog=logs_data)

@app.route('/api/graylog/messages')
@login_required
def get_graylog_messages():
    try:
        time_range = request.args.get('timeRange', '60')  # domyślnie 60 minut
        logs_data = get_logs(time_range_minutes=int(time_range))
        # Dodaj nagłówek CORS jeśli potrzebny
        response = jsonify(logs_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        print(f"Error in get_graylog_messages: {e}")  # Dodaj logging błędów
        return jsonify({"error": str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    if 'user_info' not in session:
        session['user_info'] = {}
    return render_template('profile.html',
                         username=session.get('username'),
                         user_info=session.get('user_info'))

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            flash('Nie wybrano pliku')
            return redirect(url_for('profile'))
        
        file = request.files['avatar']
        if file.filename == '':
            flash('Nie wybrano pliku')
            return redirect(url_for('profile'))

        if file and allowed_file(file.filename):
            # Usuń stare zdjęcie jeśli istnieje
            if session.get('user_info', {}).get('avatar'):
                old_avatar = os.path.join(app.config['UPLOAD_FOLDER'], session['user_info']['avatar'])
                try:
                    if os.path.exists(old_avatar):
                        os.remove(old_avatar)
                except Exception as e:
                    print(f"Błąd podczas usuwania starego avatara: {e}")

            # Zapisz nowy plik
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{session['username']}_{int(time.time())}.{ext}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            try:
                os.chmod(filepath, 0o644)
            except Exception as e:
                print(f"Błąd podczas ustawiania uprawnień: {e}")

            # Zaktualizuj sesję
            if 'user_info' not in session:
                session['user_info'] = {}
            
            session['user_info'] = dict(session['user_info'])
            session['user_info']['avatar'] = filename
            session.modified = True

            # Zapisz informację o avatarze na stałe
            update_user_avatar(session['username'], filename)

            flash('Zdjęcie profilowe zostało zaktualizowane')
            return redirect(url_for('profile'))

    except Exception as e:
        print(f"Błąd podczas przetwarzania avatara: {e}")
        flash('Wystąpił błąd podczas zapisywania zdjęcia')
    
    return redirect(url_for('profile'))

if __name__ == '__main__': 
    app.run(debug=True, host='0.0.0.0', port=5000)