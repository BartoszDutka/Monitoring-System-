from flask import Flask, render_template, request, jsonify, session, flash
from flask import redirect, url_for, abort, send_from_directory
from modules.zabbix import get_hosts, get_unknown_hosts
from modules.graylog import get_logs
from modules.glpi import get_glpi_data
from modules.ldap_auth import authenticate_user
from config import *  # Importujemy wszystkie zmienne konfiguracyjne
import urllib3
import urllib.parse  # Add this import
import subprocess
import os
import json  # Add this import
from functools import wraps
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
from datetime import datetime, timedelta  # Keep this import as is
from modules.user_data import update_user_profile
from inventory import inventory  # Import the inventory blueprint
from werkzeug.exceptions import Forbidden  # Add this import
from flask_caching import Cache
import logging
from modules.tasks import tasks, setup_tasks_tables  # Import from the modules directory

# Handle PDF dependency imports
import importlib.util
PDF_CAPABILITY = "none"
PDF_STATUS_MESSAGE = ""

# Try to import weasyprint first
try:
    if importlib.util.find_spec('weasyprint') is not None:
        from modules.reports import ReportGenerator, get_recent_reports, get_report_by_id, delete_report, REPORTS_DIR
        PDF_CAPABILITY = "weasyprint"
        PDF_STATUS_MESSAGE = "Using WeasyPrint for PDF generation"
        print("WeasyPrint is available for PDF generation")
    else:
        PDF_STATUS_MESSAGE = "WeasyPrint module not found"
        print("WeasyPrint not available, checking pdfkit...")
except ImportError as e:
    PDF_STATUS_MESSAGE = f"WeasyPrint import error: {str(e)}"
    print(f"WeasyPrint import error: {e}")

# Try pdfkit next if weasyprint failed
if PDF_CAPABILITY == "none" and importlib.util.find_spec('pdfkit') is not None:
    try:
        import pdfkit
        from modules.reports import ReportGenerator, get_recent_reports, get_report_by_id, delete_report, REPORTS_DIR
        PDF_CAPABILITY = "pdfkit"
        PDF_STATUS_MESSAGE = "Using PDFKit for PDF generation"
        print("PDFKit is available for PDF generation")
        
        # Check if wkhtmltopdf is installed
        try:
            version = subprocess.check_output(['wkhtmltopdf', '--version'], stderr=subprocess.STDOUT)
            print(f"wkhtmltopdf is installed: {version.decode().strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            PDF_STATUS_MESSAGE += " (wkhtmltopdf not installed/not in PATH)"
            print("Warning: wkhtmltopdf is not installed or not in PATH.")
            print("PDF generation may not work correctly.")
            print("Please run: python install_pdf_deps.py")
    except ImportError:
        PDF_STATUS_MESSAGE += ", PDFKit not available"

# If all else failed, use the modules with fallback modes
if PDF_CAPABILITY == "none":
    try:
        from modules.reports import ReportGenerator, get_recent_reports, get_report_by_id, delete_report, REPORTS_DIR
        PDF_STATUS_MESSAGE = "No PDF library available. PDF reports will be saved as text files or Excel."
        print("Warning: No PDF generation library is available.")
        print("PDF reports will be saved as text files.")
        print("Please run: python install_pdf_deps.py to install PDF dependencies")
    except ImportError as e:
        print(f"Critical error importing reports module: {e}")

# Show PDF capability status for debugging
print(f"PDF Generation Capability: {PDF_CAPABILITY}")
print(f"Status: {PDF_STATUS_MESSAGE}")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'twoj_tajny_klucz_do_sesji'  # Poprawiony błąd składni
app.config['SESSION_TYPE'] = 'filesystem'

# Register blueprints
app.register_blueprint(inventory)
app.register_blueprint(tasks)  # Add this line to register the tasks blueprint

# Dodaj globalną zmienną dla cache
glpi_cache = None

# Dodaj nowe stałe na górze pliku
ULTRAVNC_PATH = r"C:\igichp\UltraVNC_Viewer\vncviewer_1.2.0.6.exe"
VNC_PASSWORD = "SW!nk@19"

# Dodaj konfigurację dla uploadów
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'avatars')
TASK_ATTACHMENTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'attachments')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB w bajtach

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TASK_ATTACHMENTS_FOLDER'] = TASK_ATTACHMENTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Upewnij się, że foldery istnieją
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TASK_ATTACHMENTS_FOLDER, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure caching
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})
cache.init_app(app)

# Initialize GLPI module cache
from modules.glpi import cache as glpi_cache
glpi_cache.init_app(app)

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
            user_info = get_user_info(username)
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
                
                try:
                    # Initialize GLPI data from database with clear parameters
                    global glpi_cache
                    logger.info("Loading GLPI data from database after successful login...")
                    
                    # Explicitly force loading from assets table in database
                    data = get_glpi_data(refresh_api=False, from_db=True)
                    
                    if not data or not isinstance(data, dict):
                        logger.error("Invalid GLPI data format from database")
                        data = {
                            'computers': [],
                            'categorized': {
                                'workstations': [],
                                'terminals': [],
                                'servers': [],
                                'other': []
                            },
                            'network_devices': [],
                            'printers': [],
                            'monitors': [],
                            'racks': [],
                            'total_count': 0,
                            'category_counts': {
                                'workstations': 0,
                                'terminals': 0,
                                'servers': 0,
                                'network': 0,
                                'printers': 0,
                                'monitors': 0,
                                'racks': 0,
                                'other': 0
                            }
                        }
                    
                    # Log the number of devices loaded
                    logger.info(f"Loaded {data.get('total_count', 0)} devices from database")
                    logger.info(f"Category counts: {data.get('category_counts', {})}")
                    
                    # Update both global cache and Flask cache
                    glpi_cache = data
                    cache.set('glpi_data', data)
                    logger.info("GLPI data initialized from database successfully")
                    
                except Exception as e:
                    logger.error(f"Error initializing GLPI data: {e}")
                    import traceback
                    traceback.print_exc()
                
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
    """Endpoint to refresh GLPI data from API and update database"""
    try:
        global glpi_cache
        logger.info("Starting GLPI data refresh from API")
        
        # First refresh data from API to database with clear parameters
        refreshed_data = get_glpi_data(refresh_api=True, from_db=False)
        
        # Then get fresh data from database
        glpi_cache = get_glpi_data(refresh_api=False, from_db=True)
        
        # Update the Flask cache
        cache.set('glpi_data', glpi_cache)
        
        logger.info("GLPI data refresh complete")
        return jsonify({
            "status": "success",
            "message": "Data refreshed and retrieved from database",
            "last_refresh": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "category_counts": glpi_cache.get('category_counts', {})
        })
    except Exception as e:
        logger.error(f"Error in refresh_glpi: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/glpi/refresh/<category>')
@login_required
def refresh_glpi_category(category):
    """Endpoint to refresh specific GLPI category from API or get from database"""
    try:
        global glpi_cache
        
        # Check if we should force API refresh
        force_api = request.args.get('force_api', '0') == '1'
        
        if force_api:
            # Force refresh specific category from API
            logger.info(f"Forcing refresh of category '{category}' from API")
            new_data = get_glpi_data(refresh_api=True, from_db=False, category=category)
            
            # Get updated data from database
            glpi_cache = get_glpi_data(refresh_api=False, from_db=True)
        else:
            # Get data from database
            logger.info(f"Retrieving category '{category}' from database")
            glpi_cache = get_glpi_data(refresh_api=False, from_db=True)
            
        # Update the Flask cache
        cache.set('glpi_data', glpi_cache)
            
        return jsonify({
            "status": "success",
            "message": f"Category '{category}' refreshed successfully",
            "source": "api" if force_api else "database",
            "category_counts": glpi_cache.get('category_counts', {})
        })
    except Exception as e:
        logger.error(f"Error in refresh_glpi_category: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Update the cached GLPI data function
@app.route('/api/glpi/data')
@login_required
def get_cached_glpi_data():
    """Get GLPI data with proper caching"""
    start_time = datetime.now()
    
    # Check if force refresh is requested
    force_api = request.args.get('force_api', '0') == '1'
    
    def get_data():
        try:
            # Be explicit about parameters to ensure we get database data
            data = get_glpi_data(refresh_api=False, from_db=True)
            if not isinstance(data, dict) or 'category_counts' not in data:
                # Initialize with proper default structure if invalid data
                return {
                    'computers': [],
                    'categorized': {
                        'workstations': [],
                        'terminals': [],
                        'servers': [],
                        'other': []
                    },
                    'network_devices': [],
                    'printers': [],
                    'monitors': [],
                    'racks': [],
                    'total_count': 0,
                    'category_counts': {
                        'workstations': 0,
                        'terminals': 0,
                        'servers': 0,
                        'network': 0,
                        'printers': 0,
                        'monitors': 0,
                        'racks': 0,
                        'other': 0
                    }
                }
            return data
        except Exception as e:
            logger.error(f"Error getting GLPI data: {e}")
            return {
                'computers': [],
                'categorized': {
                    'workstations': [],
                    'terminals': [],
                    'servers': [],
                    'other': []
                },
                'network_devices': [],
                'printers': [],
                'monitors': [],
                'racks': [],
                'total_count': 0,
                'category_counts': {
                    'workstations': 0,
                    'terminals': 0,
                    'servers': 0,
                    'network': 0,
                    'printers': 0,
                    'monitors': 0,
                    'racks': 0,
                    'other': 0
                }
            }
    
    # Either use cached data or force refresh
    if force_api:
        cache.delete('glpi_data')
        data = get_glpi_data(refresh_api=True, from_db=True)
    else:
        data = cache.get('glpi_data')
        if data is None:
            data = get_data()
            cache.set('glpi_data', data)
    
    response_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"GLPI data retrieved in {response_time:.2f} seconds (source: {'API' if force_api else 'cache/db'})")
    
    return data if request.path.startswith('/api/') else data

@app.route('/')
@login_required
def index():
    """Main dashboard route with proper error handling and caching"""
    start_time = datetime.now()
    
    try:
        # Get GLPI data with proper structure
        glpi_data = get_cached_glpi_data()
        if not isinstance(glpi_data, dict) or 'category_counts' not in glpi_data:
            glpi_data = {
                'category_counts': {
                    'workstations': 0,
                    'terminals': 0,
                    'servers': 0,
                    'network': 0,
                    'printers': 0,
                    'monitors': 0,
                    'racks': 0,
                    'other': 0
                }
            }
        
        # Get other monitoring data
        zabbix_data = get_cached_zabbix_data()
        graylog_data = get_cached_graylog_data()
        
        response_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Dashboard loaded in {response_time:.2f} seconds")
        
        return render_template('index.html',
                             zabbix=zabbix_data,
                             graylog=graylog_data,
                             glpi=glpi_data,
                             request=request)
                             
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('error.html', error=str(e)), 500

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
    """Force refresh of GLPI data from API"""
    try:
        global glpi_cache
        cache.delete('glpi_data')
        
        # Explicitly refresh from API and then get from database
        get_glpi_data(refresh_api=True, from_db=False)
        glpi_cache = get_glpi_data(refresh_api=False, from_db=True)
        
        cache.set('glpi_data', glpi_cache)
        
        return jsonify({
            "status": "success", 
            "message": "GLPI data refreshed from API",
            "category_counts": glpi_cache.get('category_counts', {})
        })
    except Exception as e:
        logger.error(f"Error in force_refresh_glpi: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route('/graylog/loading')
@login_required
def graylog_loading():
    target_page = request.args.get('target', '/graylog/logs')
    query_string = request.args.get('query_string', '')
    
    if (query_string):
        target_page = f"{target_page}?{query_string}"
    
    return render_template('loading.html', target_page=target_page)  # zmiana ścieżki szablonu

@app.route('/graylog/logs')
@login_required
def graylog_logs():
    # Check if we're coming from the loading page
    if not request.referrer or 'loading' not in request.referrer:
        query_string = request.query_string.decode() if request.query_string else ''
        return redirect(url_for('graylog_loading', 
                              target='/graylog/logs',
                              query_string=query_string))
    
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
    # Check if we're coming from the loading page
    if not request.referrer or 'loading' not in request.referrer:
        return redirect(url_for('graylog_loading', target='/graylog/messages-over-time'))
    
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
            if (old_avatar):
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

@app.route('/fetch_logs', methods=['POST'])
def fetch_logs():
    try:
        data = request.get_json()
        force_refresh = data.get('force_refresh', False)
        logs = get_logs(time_range_minutes=30, force_refresh=force_refresh)
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/glpi/devices')
@login_required
def get_glpi_devices():
    """API endpoint to get all GLPI devices for tasks relationship - redirects to tasks/api/devices"""
    # Redirect to the new endpoint in the tasks module
    return redirect(url_for('tasks.get_devices'))

@app.route('/reports')
@login_required
def reports_page():
    """Show the reports generation interface."""
    try:
        # Get list of recent reports with proper formatting
        reports = get_recent_reports()
        
        # Format dates and add necessary fields
        formatted_reports = []
        for report in reports:
            formatted_report = {
                'id': report['id'],
                'name': report['name'],
                'type': report['type'].capitalize(),
                'date': report['generated_at'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(report['generated_at'], datetime) else report['generated_at'],
                'records': report['record_count']
            }
            formatted_reports.append(formatted_report)
            
        return render_template('reports.html', reports=formatted_reports)
    except Exception as e:
        logger.error(f"Error loading reports page: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/generate-report', methods=['POST'])
@login_required
def generate_report():
    """Handle report generation requests with improved error handling."""
    try:
        logger.info("Report generation request received")
        
        # Get form data
        report_type = request.form.get('reportType')
        output_format = request.form.get('outputFormat', 'pdf')
        date_range = request.form.get('dateRange')
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        
        logger.info(f"Report parameters: type={report_type}, format={output_format}, range={date_range}")
        logger.info(f"Custom dates: start={start_date}, end={end_date}")
        
        # Validate required inputs
        if not report_type:
            return jsonify({
                'success': False, 
                'message': 'Report type is required'
            }), 400
            
        if not date_range:
            return jsonify({
                'success': False, 
                'message': 'Date range is required'
            }), 400
            
        # Convert string dates to datetime objects if provided
        start_date_obj = None
        end_date_obj = None
        
        if date_range == 'custom':
            if not start_date or not end_date:
                return jsonify({
                    'success': False, 
                    'message': 'Start and end dates are required for custom date range'
                }), 400
                
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError as e:
                logger.error(f"Date parsing error: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Invalid date format: {str(e)}'
                }), 400
        
        # Initialize report generator
        try:
            logger.info("Initializing report generator")
            report_gen = ReportGenerator(
                report_type=report_type,
                output_format=output_format,
                date_range=date_range,
                start_date=start_date_obj,
                end_date=end_date_obj,
                record_limit=500,
                preview=False
            )
        except Exception as e:
            logger.error(f"Error initializing report generator: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Error initializing report: {str(e)}'
            }), 500
        
        # Generate report
        try:
            logger.info("Generating report...")
            result = report_gen.generate_report()
            logger.info(f"Report generation result: {result}")
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Error generating report: {str(e)}'
            }), 500
        
        if result.get('success'):
            # Return success response with report details
            return jsonify({
                'success': True,
                'message': 'Report generated successfully',
                'report_id': result.get('report_id')
            })
        else:
            # Return error details
            return jsonify({
                'success': False,
                'message': result.get('error', 'Unknown error generating report')
            }), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in generate_report: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

@app.route('/view-report/<report_id>')
@login_required
def view_report(report_id):
    """View a generated report."""
    try:
        # Get report info
        report = get_report_by_id(report_id)
        
        if not report:
            flash('Report not found', 'error')
            return redirect(url_for('reports_page'))
        
        # For HTML reports, we can display them directly
        if report['format'] == 'html':
            with open(os.path.join(REPORTS_DIR, report['path']), 'r', encoding='utf-8') as f:
                html_content = f.read()
            return render_template('report_viewer.html', 
                                 report=report,
                                 html_content=html_content)
        else:
            # For other formats, redirect to download
            return redirect(url_for('download_report', report_id=report_id))
    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}")
        flash(f'Error viewing report: {str(e)}', 'error')
        return redirect(url_for('reports_page'))

@app.route('/download-report/<report_id>')
@login_required
def download_report(report_id):
    """Download a generated report."""
    # Get report info
    report = get_report_by_id(report_id)
    
    if not report:
        flash('Report not found', 'error')
        return redirect(url_for('reports_page'))
    
    # Send the file as an attachment
    return send_from_directory(
        REPORTS_DIR, 
        report['path'],
        as_attachment=True,
        download_name=report['name']
    )

@app.route('/delete-report/<report_id>', methods=['DELETE'])
@login_required
def delete_report_route(report_id):
    """Delete a generated report."""
    success = delete_report(report_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete report'}), 404

if __name__ == '__main__':
    # Import required modules
    from modules.database import setup_departments_table, ensure_default_departments
    
    # Initialize database tables
    setup_departments_table()
    ensure_default_departments()
    setup_tasks_tables()  # Add this line to initialize tasks tables
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)