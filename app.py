from flask import Flask, render_template, request, jsonify, session, flash
from modules.zabbix import get_hosts, get_unknown_hosts
from modules.graylog import get_logs
from modules.glpi import get_glpi_data
from modules.ldap_auth import authenticate_user
from config import *  # Importujemy wszystkie zmienne konfiguracyjne
import urllib3
import subprocess
import os
import json  # Add this import
from functools import wraps
from flask import redirect, url_for, abort
from werkzeug.utils import secure_filename
import time  # Dodaj na początku pliku z innymi importami
from modules.user_data import update_user_avatar, get_user_avatar, verify_user, get_user_info
from modules.database import (
    get_db_cursor, 
    get_historical_metrics, 
    get_host_status_history,
    get_messages_timeline,
    get_detailed_messages  # Dodaj ten import
)
from datetime import datetime, timedelta
from modules.user_data import update_user_profile
from inventory import inventory  # Import the inventory blueprint
from werkzeug.exceptions import Forbidden  # Add this import
from flask_caching import Cache
import logging
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'twoj_tajny_klucz_do_sesji'  # Poprawiony błąd składni
app.config['SESSION_TYPE'] = 'filesystem'

# Register blueprints
app.register_blueprint(inventory)

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure caching
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})
cache.init_app(app)

# Custom filter for checking if a character is a digit
@app.template_filter('isdigit')
def isdigit_filter(s):
    if not s:
        return False
    return s[0].isdigit() if s else False

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

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            user_role = session.get('user_info', {}).get('role', 'viewer')
            if user_role not in required_roles:
                return render_template('403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required(['admin'])(f)

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
        
        # Najpierw próbujemy logowania LDAP
        if authenticate_user(username, password):
            user_info = get_user_info(username)  # Pobierz dane z lokalnej bazy
            if user_info:
                session['logged_in'] = True
                session['username'] = username
                session['user_info'] = user_info
                
                # Update last login timestamp
                with get_db_cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET last_login = CURRENT_TIMESTAMP 
                        WHERE username = %s
                    """, (username,))
                    
                return redirect(url_for('index'))
        
        # Jeśli LDAP nie zadziała, próbujemy lokalnej bazy
        elif verify_user(username, password):
            user_info = get_user_info(username)
            if user_info:
                session['logged_in'] = True
                session['username'] = username
                session['user_info'] = user_info
                return redirect(url_for('index'))
        
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
        glpi_cache = get_glpi_data(refresh=True)  # Wymuszamy odświeżenie z API
        return jsonify({
            "status": "success",
            "message": "Data refreshed successfully",
            "last_refresh": glpi_cache.get('last_refresh')
        })
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

# Modify index route to use cached data
@app.route('/')
@login_required
def index():
    start_time = datetime.now()
    
    zabbix_data = get_cached_zabbix_data()
    graylog_data = get_cached_graylog_data()
    glpi_data = get_cached_glpi_data()
    
    response_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Dashboard loaded in {response_time:.2f} seconds")
    
    return render_template('index.html',
                         zabbix=zabbix_data,
                         graylog=graylog_data,
                         glpi=glpi_data,
                         request=request)

# Add new API endpoints for cached data
@app.route('/api/zabbix/refresh')
@login_required
def get_cached_zabbix_data():
    start_time = datetime.now()
    
    @cache.cached(timeout=60, key_prefix='zabbix_data')
    def get_data():
        return get_hosts()
    
    data = get_data()
    response_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Zabbix data retrieved in {response_time:.2f} seconds")
    
    return jsonify(data) if request.path.startswith('/api/') else data

@app.route('/api/glpi/refresh')
@login_required
def get_cached_glpi_data():
    start_time = datetime.now()
    
    @cache.cached(timeout=300, key_prefix='glpi_data')
    def get_data():
        return get_glpi_data(refresh=False)
    
    data = get_data()
    response_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"GLPI data retrieved in {response_time:.2f} seconds")
    
    return jsonify(data) if request.path.startswith('/api/') else data

@app.route('/api/graylog/refresh')
@login_required
def get_cached_graylog_data():
    start_time = datetime.now()
    
    @cache.cached(timeout=30, key_prefix='graylog_data')
    def get_data():
        return get_logs(time_range_minutes=5)
    
    data = get_data()
    response_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Graylog data retrieved in {response_time:.2f} seconds")
    
    return jsonify(data) if request.path.startswith('/api/') else data

# Force cache refresh endpoints
@app.route('/api/zabbix/force_refresh')
@login_required
def force_refresh_zabbix():
    cache.delete('zabbix_data')
    return jsonify(get_cached_zabbix_data())

@app.route('/api/glpi/force_refresh')
@login_required
def force_refresh_glpi():
    cache.delete('glpi_data')
    return jsonify(get_cached_glpi_data())

@app.route('/api/graylog/force_refresh')
@login_required
def force_refresh_graylog():
    cache.delete('graylog_data')
    return jsonify(get_cached_graylog_data())

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
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=5)
    
    # Pobierz limit z URL lub session storage
    limit = request.args.get('limit', type=int)
    if limit is None:
        limit = session.get('graylog_limit', 300)
    
    # Zapisz limit do sesji
    session['graylog_limit'] = limit
    
    force_refresh = request.args.get('refresh', '0') == '1'
    
    if force_refresh:
        get_logs(force_refresh=True)
    
    logs_data = get_detailed_messages(start_time, end_time, limit=limit)
    
    formatted_data = {
        'logs': [
            {
                'timestamp': msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'level': msg['level'],
                'severity': msg['severity'],
                'category': msg['category'],
                'message': msg['message'],
                'details': json.loads(msg['details']) if msg['details'] else {}
            }
            for msg in logs_data['messages']
        ],
        'total_results': logs_data['total_results'],
        'time_range': f"Last 5 minutes • Showing {limit} of {logs_data['total_in_db']} entries",
        'stats': logs_data['stats']
    }
    
    return render_template('graylog/logs.html', 
                         graylog=formatted_data,
                         request=request)

@app.route('/graylog/messages-over-time')
@login_required
def graylog_messages_over_time():
    # Get initial Graylog data with increased limit
    graylog_data = get_logs(time_range_minutes=60, force_refresh=True)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    timeline_data = get_messages_timeline(start_time, end_time, '1 hours')  # Changed from '1 hour' to '1 hours'
    
    return render_template('graylog/messages_over_time.html', 
                         graylog=graylog_data,
                         timeline_data=timeline_data,
                         start_time=start_time.strftime('%Y-%m-%d %H:%M'),
                         end_time=end_time.strftime('%Y-%m-%d %H:%M'))

@app.route('/api/graylog/messages')
@login_required
def get_graylog_messages():
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        limit = request.args.get('limit', session.get('graylog_limit', 300), type=int)
        session['graylog_limit'] = limit
        
        messages_data = get_detailed_messages(start_time, end_time, limit=limit)
        
        response = {
            'logs': [
                {
                    'timestamp': msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'level': msg['level'],
                    'severity': msg['severity'],
                    'category': msg['category'],
                    'message': msg['message'],
                    'details': json.loads(msg['details']) if msg['details'] else {}
                }
                for msg in messages_data['messages']
            ],
            'total_results': messages_data['total_in_db'],
            'time_range': f"Last 5 minutes • Showing {limit} of {messages_data['total_in_db']} entries",
            'stats': messages_data['stats']
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in get_graylog_messages: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/graylog/timeline')
@login_required
def get_graylog_timeline():
    try:
        range_value = int(request.args.get('range', '30'))
        range_type = request.args.get('range_type', 'minutes')
        interval = request.args.get('interval', '5 minutes')
        
        # Ustaw koniec na aktualną datę
        end_time = datetime.now()

        # Oblicz start_time w zależności od typu zakresu
        if range_type == 'minutes':
            start_time = end_time - timedelta(minutes=range_value)
            if not interval.endswith('minutes'):
                interval = '5 minutes'
        elif range_type == 'hours':
            start_time = end_time - timedelta(hours=range_value)
            if not interval.endswith('minutes'):
                interval = '30 minutes'
        else:  # days
            # Dla dni, ustaw end_time na koniec aktualnego dnia
            end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            # Ustaw start_time na początek dnia sprzed range_value dni
            start_time = (end_time - timedelta(days=range_value-1)).replace(hour=0, minute=0, second=0, microsecond=0)
            interval = '1 day'

        print(f"Fetching timeline from {start_time} to {end_time} with interval {interval}")
        
        # Pobierz dane z bazy
        timeline_data = get_messages_timeline(start_time, end_time, interval)
        
        # Format danych dla wykresu
        formatted_data = {
            'labels': [],
            'datasets': [
                {
                    'label': 'High Priority',
                    'data': [],
                    'backgroundColor': 'rgba(220,53,69,0.5)',
                    'borderColor': '#dc3545',
                    'borderWidth': 1
                },
                {
                    'label': 'Medium Priority',
                    'data': [],
                    'backgroundColor': 'rgba(255,193,7,0.5)',
                    'borderColor': '#ffc107',
                    'borderWidth': 1
                },
                {
                    'label': 'Low Priority',
                    'data': [],
                    'backgroundColor': 'rgba(13,202,240,0.5)',
                    'borderColor': '#0dcaf0',
                    'borderWidth': 1
                }
            ]
        }
        
        # Wypełnij dane wykresu
        for row in timeline_data:
            formatted_data['labels'].append(row['time_interval'])
            formatted_data['datasets'][0]['data'].append(row['high_count'])
            formatted_data['datasets'][1]['data'].append(row['medium_count'])
            formatted_data['datasets'][2]['data'].append(row['low_count'])
        
        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error in timeline: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET', 'POST'])
@role_required(['admin', 'user'])  # Viewers can't access profile
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    user_info = get_user_info(session['username'])
    if not user_info:
        return redirect(url_for('login'))
    
    # Get departments list
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT name, description
            FROM departments
            ORDER BY name
        ''')
        departments = cursor.fetchall()
        
    session['user_info'] = user_info
    return render_template('profile.html',
                         username=session['username'],
                         user_info=user_info,
                         departments=departments)

@app.route('/update_profile', methods=['POST'])
@role_required(['admin', 'user'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    email = request.form.get('email')
    department = request.form.get('department')
    role = request.form.get('role')  # Changed from title to role
    
    try:
        update_user_profile(
            username=session['username'],
            email=email,
            department=department,
            role=role  # Changed from title to role
        )
        flash('Profile updated successfully')
        
        # Update session info
        user_info = get_user_info(session['username'])
        if user_info:
            session['user_info'] = user_info
            
    except Exception as e:
        print(f"Error updating profile: {e}")
        flash('Error updating profile')
        
    return redirect(url_for('profile'))

@app.route('/upload_avatar', methods=['POST'])
@role_required(['admin', 'user'])  # Viewers can't upload avatars
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            flash('No file selected')
            return redirect(url_for('profile'))
            
        file = request.files['avatar']
        if file.filename == '':
            flash('No file selected')
            return redirect(url_for('profile'))
            
        if file and allowed_file(file.filename):
            # Delete old avatar if exists
            old_avatar = session.get('user_info', {}).get('avatar_path')
            if old_avatar:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
                    
            # Save new avatar
            filename = secure_filename(f"{session['username']}_{int(time.time())}.{file.filename.rsplit('.', 1)[1].lower()}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Update database and session
            update_user_avatar(session['username'], filename)
            
            # Refresh user info in session
            user_info = get_user_info(session['username'])
            if user_info:
                session['user_info'] = user_info
                
            flash('Avatar updated successfully')
            
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        flash('Error uploading avatar')
        
    return redirect(url_for('profile'))

@app.route('/api/history/metrics/<host_id>')
@login_required
def get_host_metrics_history(host_id):
    """Get historical metrics for a host"""
    try:
        days = int(request.args.get('days', 7))
        metric_type = request.args.get('type', 'cpu')
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        metrics = get_historical_metrics(host_id, metric_type, start_time, end_time)
        return jsonify({'metrics': metrics})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/status/<host_id>')
@login_required
def get_host_history(host_id):
    """Get historical status for a host"""
    try:
        limit = int(request.args.get('limit', 100))
        history = get_host_status_history(host_id, limit)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/graylog/refresh', methods=['POST'])
@login_required
def refresh_graylog_logs():
    try:
        # Pobierz limit z parametrów URL
        limit = request.args.get('limit', session.get('graylog_limit', 300), type=int)
        session['graylog_limit'] = limit
        
        # Force refresh from Graylog API and store in database
        logs_data = get_logs(force_refresh=True)
        
        # Return new statistics from database
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        db_data = get_detailed_messages(start_time, end_time, limit=limit)
        
        return jsonify({
            'status': 'success',
            'stats': db_data['stats'],
            'time_range': f"Last 5 minutes • Showing {limit} of {db_data['total_in_db']} entries"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/manage_users')
@admin_required
def manage_users():
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
    return render_template('manage_users.html', users=users)

@app.route('/update_user_role', methods=['POST'])
@admin_required
def update_user_role():
    user_id = request.form.get('user_id')
    new_role = request.form.get('role')
    
    if new_role not in ['admin', 'user', 'viewer']:
        flash('Invalid role specified')
        return redirect(url_for('manage_users'))
        
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE users 
            SET role = %s 
            WHERE user_id = %s
        """, (new_role, user_id))
        
    flash('User role updated successfully')
    return redirect(url_for('manage_users'))

# Add error handler for 403 errors
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.route('/api/delete_user', methods=['POST'])
@admin_required
def delete_user():
    try:
        data = request.json
        user_id = data.get('user_id')
        
        with get_db_cursor() as cursor:
            # Check if user exists and is not the current user
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user or user['username'] == session['username']:
                return jsonify({'success': False, 'message': 'Cannot delete this user'}), 400
                
            # Delete the user
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/update_user', methods=['POST'])
@admin_required
def update_user_info():
    try:
        data = request.json
        user_id = data.get('user_id')
        email = data.get('email')
        department = data.get('department')
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET email = %s, 
                    department = %s 
                WHERE user_id = %s
            """, (email, department, user_id))
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Import required modules
    from modules.database import setup_departments_table, ensure_default_departments
    
    # Initialize database tables
    setup_departments_table()
    ensure_default_departments()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)