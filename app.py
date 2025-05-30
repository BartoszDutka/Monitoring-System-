from flask import Flask, render_template, request, jsonify, session, flash
from flask import redirect, url_for, abort, send_from_directory
from modules.zabbix import get_hosts, get_unknown_hosts
from modules.graylog import get_logs
from modules.glpi import get_glpi_data
from modules.ldap_auth import authenticate_user
from config import *  # Importujemy wszystkie zmienne konfiguracyjne
import urllib3
import urllib.parse
import subprocess
import os
import json
from functools import wraps
from werkzeug.utils import secure_filename
import time
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
# Import the new permissions module
from modules.permissions import permission_required, role_required, admin_required, has_permission, get_user_permissions
from inventory import inventory  # Import the inventory blueprint
from werkzeug.exceptions import Forbidden  # Add this import
from flask_caching import Cache
import logging
from modules.tasks import tasks, setup_tasks_tables  # Import from the modules directory
# Import report functions outside conditional blocks to ensure they're always available
from modules.reports import ReportGenerator, get_recent_reports, get_report_by_id, delete_report, REPORTS_DIR

# Handle PDF dependency imports
import importlib.util
PDF_CAPABILITY = "none"
PDF_STATUS_MESSAGE = ""

# Try to import weasyprint first
try:
    if importlib.util.find_spec('weasyprint') is not None:
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
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sesja będzie ważna przez 7 dni

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
from modules.glpi import init_cache
init_cache(app)

# Custom filter for checking if a character is a digit
@app.template_filter('isdigit')
def isdigit_filter(s):
    if not s:
        return False
    return s[0].isdigit() if s else False

# Add this with the other filters
@app.template_filter('count_values')
def count_values_filter(dictionary):
    """Count all values in a dictionary of lists"""
    count = 0
    for value_list in dictionary.values():
        count += len(value_list)
    return count

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

# Note: These functions are now imported from modules.permissions
# Keeping these for backward compatibility
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

# This now uses the imported admin_required but defining it for backward compatibility
def admin_required(f):
    return role_required(['admin'])(f)

@app.context_processor
def utility_processor():
    # Make both time and permission checking available in templates
    return dict(
        time=time,
        has_permission=has_permission
    )

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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_logs')
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
@permission_required('view_monitoring')
def force_refresh_zabbix():
    cache.delete('zabbix_data')
    return jsonify(get_cached_zabbix_data())

@app.route('/api/glpi/force_refresh')
@login_required
@permission_required('view_glpi')
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
@permission_required('view_logs')
def force_refresh_graylog():
    cache.delete('graylog_data')
    return jsonify(get_cached_graylog_data())

@app.route('/available-hosts')
@login_required
@permission_required('view_monitoring')
def available_hosts():
    return render_template('available_hosts.html', request=request)

@app.route('/unavailable-hosts')
@login_required
@permission_required('view_monitoring')
def unavailable_hosts():
    return render_template('unavailable_hosts.html', request=request)

@app.route('/unknown-hosts')
@login_required
@permission_required('view_monitoring')
def unknown_hosts():
    return render_template('unknown_hosts.html', request=request)

@app.route('/api/data')
@login_required
@permission_required('view_monitoring')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('view_glpi')
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
@permission_required('vnc_connect')
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
@permission_required('view_logs')
def graylog_loading():
    target_page = request.args.get('target', '/graylog/logs')
    query_string = request.args.get('query_string', '')
    
    # Pobierz bieżący język użytkownika
    current_language = session.get('language', 'en')  # Domyślnie angielski (spójnie z resztą aplikacji)
    
    if (query_string):
        target_page = f"{target_page}?{query_string}"
    
    # Przekazujemy informację o języku do szablonu
    return render_template('loading.html', 
                         target_page=target_page,
                         current_language=current_language)  # dodajemy informację o języku

@app.route('/graylog/logs')
@login_required
@permission_required('view_logs')
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
@permission_required('view_logs')
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
@permission_required('view_logs')
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
@permission_required('view_logs')
def get_graylog_timeline():
    try:
        range_value = int(request.args.get('range', '30'))
        range_type = request.args.get('range_type', 'minutes')
        interval = request.args.get('interval', '5 minutes')
        
        # Pobierz język z parametru URL albo z sesji, z domyślną wartością 'en'
        language = request.args.get('language') or session.get('language', 'en')
        
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
        
        # Format danych dla wykresu - dostosuj etykiety do języka
        if language == 'pl':
            # Polskie etykiety priorytetów
            formatted_data = {
                'labels': [],
                'datasets': [
                    {
                        'label': 'Wysoki',
                        'data': [],
                        'backgroundColor': 'rgba(220,53,69,0.5)',
                        'borderColor': '#dc3545',
                        'borderWidth': 1
                    },
                    {
                        'label': 'Średni',
                        'data': [],
                        'backgroundColor': 'rgba(255,193,7,0.5)',
                        'borderColor': '#ffc107',
                        'borderWidth': 1
                    },
                    {
                        'label': 'Niski',
                        'data': [],
                        'backgroundColor': 'rgba(13,202,240,0.5)',
                        'borderColor': '#0dcaf0',
                        'borderWidth': 1
                    }
                ]
            }
        else:
            # Angielskie etykiety priorytetów (domyślne)
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

@app.route('/profile')
@login_required
@permission_required('manage_profile')
def profile():
    """User profile management page"""
    username = session.get('username')
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT u.*, r.role_key, r.description_en as role_description
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.role_id
                WHERE u.username = %s
            """, (username,))
            user = cursor.fetchone()
            
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('index'))
            
        return render_template('profile.html', user=user)
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
        flash('Error loading profile', 'error')
        return redirect(url_for('index'))

@app.route('/update-profile', methods=['POST'])
@login_required
@permission_required('manage_profile')
def update_profile():
    """Update user profile information"""
    username = session.get('username')
    display_name = request.form.get('display_name', '').strip()
    email = request.form.get('email', '').strip()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    try:
        with get_db_cursor() as cursor:
            # Get current user data
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if not user:
                flash('User not found', 'error')
                return redirect(url_for('profile'))
            
            # Update basic profile information
            update_fields = []
            update_values = []
            
            if display_name and display_name != user['display_name']:
                update_fields.append('display_name = %s')
                update_values.append(display_name)
            
            if email and email != user['email']:
                update_fields.append('email = %s')
                update_values.append(email)
            
            # Handle password change
            if new_password:
                if not current_password:
                    flash('Current password is required to change password', 'error')
                    return redirect(url_for('profile'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                    return redirect(url_for('profile'))
                
                # Verify current password (simplified - in production use proper hashing)
                if current_password != user['password']:
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('profile'))
                
                update_fields.append('password = %s')
                update_values.append(new_password)
            
            # Update user data if there are changes
            if update_fields:
                update_values.append(username)
                cursor.execute(f"""
                    UPDATE users SET {', '.join(update_fields)}
                    WHERE username = %s
                """, update_values)
                
                flash('Profile updated successfully', 'success')
            else:
                flash('No changes made', 'info')
                
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        flash('Error updating profile', 'error')
    
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
@permission_required('view_logs')
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
    """View and manage system users"""
    # Przekieruj do nowego ujednoliconego interfejsu z aktywną zakładką "users"
    return redirect(url_for('unified_management', active_tab='users'))

@app.route('/manage_roles')
@admin_required
def manage_roles():
    """View and manage system roles and permissions"""
    # Przekieruj do nowego ujednoliconego interfejsu z aktywną zakładką "role"
    return redirect(url_for('unified_management', active_tab='roles'))

@app.route('/unified_management')
@admin_required
def unified_management():
    """Unified interface for managing users, roles and permissions"""
    # Get active tab from query params
    active_tab = request.args.get('active_tab', 'users')
    
    # Get all users
    with get_db_cursor() as cursor:
        # Get users data
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        # Get all departments with their English and Polish descriptions
        cursor.execute('''
            SELECT name, description_en, description_pl
            FROM departments
            ORDER BY name
        ''')
        departments = cursor.fetchall()
        
        # Get all roles with their descriptions and user counts
        cursor.execute("""
            SELECT r.role_key, r.description_en, r.description_pl,
                   COUNT(u.user_id) as users_count,
                   (
                       SELECT COUNT(rp.permission_id)
                       FROM role_permissions rp
                       WHERE rp.role_id = r.role_id
                   ) as permissions_count
            FROM roles r        LEFT JOIN users u ON r.role_key = u.role
        GROUP BY r.role_key, r.description_en, r.description_pl
            ORDER BY FIELD(r.role_key, 'admin', 'manager', 'user', 'viewer')
        """)
        roles = cursor.fetchall()
    
    # Get current language from session
    current_language = session.get('language', 'en')
    
    # Get permissions by category
    from modules.permissions import get_permissions_by_category
    permissions_by_category = get_permissions_by_category(current_language)
    
    # Remove unwanted permissions
    if 'reporting' in permissions_by_category:
        permissions_by_category['reporting'] = [
            p for p in permissions_by_category['reporting'] 
            if p['permission_key'] != 'export_reports'
        ]
    
    if 'monitoring' in permissions_by_category:
        permissions_by_category['monitoring'] = [
            p for p in permissions_by_category['monitoring'] 
            if p['permission_key'] != 'acknowledge_alerts'
        ]
    
    if 'assets' in permissions_by_category:
        permissions_by_category['assets'] = [
            p for p in permissions_by_category['assets'] 
            if p['permission_key'] != 'assign_assets'
        ]
    
    # Calculate total permissions count
    total_permissions_count = sum(len(perms) for perms in permissions_by_category.values())
    
    return render_template('unified_management.html',
                          users=users,
                          departments=departments,
                          roles=roles,
                          permissions_by_category=permissions_by_category,
                          total_permissions_count=total_permissions_count,
                          active_tab=active_tab,
                          lang=current_language)

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

@app.route('/update_user_role', methods=['POST'])
@admin_required
def update_user_role():
    try:
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        
        # Validate input
        if not user_id or not new_role:
            flash('Niepoprawne dane formularza', 'danger')
            return redirect(url_for('unified_management', active_tab='users'))
        
        # Update the user's role in the database
        with get_db_cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                flash('Nie znaleziono użytkownika', 'danger')
                return redirect(url_for('unified_management', active_tab='users'))
                
            # Update the user's role
            cursor.execute("""
                UPDATE users 
                SET role = %s
                WHERE user_id = %s
            """, (new_role, user_id))
            
        flash(f'Zaktualizowano rolę użytkownika', 'success')
        return redirect(url_for('unified_management', active_tab='users'))
        
    except Exception as e:
        print(f"Error updating user role: {e}")
        flash(f'Błąd podczas aktualizacji roli: {str(e)}', 'danger')
        return redirect(url_for('unified_management', active_tab='users'))

@app.route('/fetch_logs', methods=['POST'])
@login_required
def fetch_logs():
    try:
        data = request.get_json()
        force_refresh = data.get('force_refresh', False)
          # Only allow force refresh if user has view_logs permission
        if force_refresh and not has_permission('view_logs'):
            force_refresh = False
            
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
@permission_required('view_reports')  # Only users with view_reports permission can access
def reports_page():
    """Show the reports generation interface."""
    try:
        # Get list of recent reports with proper formatting
        reports = get_recent_reports()
        
        # Format dates and add necessary fields
        formatted_reports = []
        
        for report in reports:
            # Przygotuj typ raportu - zostanie przetłumaczony przez JS na podstawie atrybutów data-
            report_type = report['type'].lower()
            formatted_report = {
                'id': report['id'],
                'name': report['name'],
                'type': report_type,  # Przekazujemy niżmieniony typ, tłumaczenia obsłużymy w szablonie
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
@permission_required('create_reports')  # Only users with create_reports permission can access
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
        report_language = request.form.get('reportLanguage', 'current')
        
        # If report language is set to current, use the interface language
        if report_language == 'current':
            report_language = session.get('language', 'en')
        
        logger.info(f"Report parameters: type={report_type}, format={output_format}, range={date_range}, language={report_language}")
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
                preview=False,
                language=report_language
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
@permission_required('view_reports')
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
@permission_required('view_reports')
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
@permission_required('delete_reports')
def delete_report_route(report_id):
    """Delete a generated report."""
    success = delete_report(report_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to delete report'}), 404

@app.route('/inventory')
def inventory():    # Get the current language from session or default to English
    current_language = session.get('language', 'en')
    
    # Fetch departments and equipment counts
    departments = []
    current_department = None
    people = []
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT name, (SELECT COUNT(*) FROM equipment WHERE department = d.name) as equipment_count FROM departments d")
            departments = cursor.fetchall()
            
            # Get current department from user's session if available
            current_user = session.get('username')
            cursor.execute("SELECT department FROM users WHERE username = %s", (current_user,))
            user_dept = cursor.fetchone()
            current_department = user_dept['department'] if user_dept else None
            
            # Get all people for equipment assignment
            cursor.execute("SELECT id, name, department FROM users ORDER BY name")
            people = cursor.fetchall()
            
    except Exception as e:
        logging.error(f"Error fetching departments: {e}")
        departments = []
        current_department = None
        people = []
    
    # Set Polish title if Polish language is selected
    page_title = "Zarządzanie inwentarzem" if current_language == 'pl' else "Inventory Management"
    
    return render_template('inventory.html', 
                          departments=departments, 
                          current_department=current_department,
                          people=people,
                          lang=current_language,
                          title=page_title)

@app.route('/api/set_language', methods=['POST'])
def set_language():
    try:
        data = request.json
        language = data.get('language')
        
        if language not in ['en', 'pl']:
            return jsonify({'success': False, 'error': 'Unsupported language'})
        
        session['language'] = language
        session.modified = True
        
        return jsonify({'success': True, 'language': language})
    except Exception as e:
        print(f"Error setting language: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/role_info', methods=['GET'])
@login_required
def api_role_info():
    """API endpoint to get information about a specific role and its permissions"""
    role_key = request.args.get('role')
    
    if not role_key or role_key not in ['admin', 'manager', 'user', 'viewer']:
        return jsonify({
            'error': 'Invalid role specified',
            'success': False
        }), 400
    
    language = session.get('language', 'en')
    
    with get_db_cursor() as cursor:
        # Get role description in both languages
        cursor.execute("""
            SELECT description_en, description_pl
            FROM roles 
            WHERE role_key = %s
        """, (role_key,))
        
        role_data = cursor.fetchone()
        
        if role_data:
            description_en = role_data['description_en']
            description_pl = role_data['description_pl']
            description = role_data[f'description_{language}']
        else:
            description_en = ''
            description_pl = ''
            description = ''
            
        # Get role permissions and role_id
        cursor.execute("SELECT role_id FROM roles WHERE role_key = %s", (role_key,))
        role_result = cursor.fetchone()
        role_id = role_result['role_id'] if role_result else None
        
        if not role_id:
            return jsonify({
                'error': 'Role not found',
                'success': False
            }), 404
        
        # Get all permissions for this role directly from role_permissions table
        perm_field_name = f"name_{language}"
        perm_field_desc = f"description_{language}"
        
        cursor.execute(f"""
            SELECT 
                p.permission_key, 
                p.category, 
                p.{perm_field_name} as name, 
                p.{perm_field_desc} as description
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.category, p.{perm_field_name}
        """, (role_id,))
        
        permissions = cursor.fetchall()
        
        # Convert permissions to a serializable format
        formatted_permissions = []
        for p in permissions:
            formatted_permissions.append({
                'key': p['permission_key'],  # Provides backward compatibility
                'permission_key': p['permission_key'],  # New explicit property
                'category': p['category'],
                'name': p['name'],
                'description': p['description']
            })
        
        # Log the response for debugging
        print(f"API role_info response for {role_key}: {len(formatted_permissions)} permissions found")
        
        return jsonify({
            'role': role_key,
            'description': description,
            'description_en': description_en,
            'description_pl': description_pl,
            'permissions': formatted_permissions,
            'success': True
        })

@app.route('/api/debug/role/<role_key>')
@admin_required
def debug_role(role_key):
    """Debug endpoint for role permissions - ADMIN ONLY"""
    try:
        from modules.permissions import debug_role_permissions
        debug_role_permissions(role_key)
        return jsonify({
            'message': f'Debug info for role {role_key} printed to server console',
            'success': True
        })
    except Exception as e:
        return jsonify({
            'message': f'Error debugging role: {str(e)}',
            'success': False
        })

@app.route('/api/debug/permission/<permission_key>')
@admin_required
def debug_permission(permission_key):
    """Debug endpoint for testing a specific permission - ADMIN ONLY"""
    try:
        from modules.permissions import has_permission, get_user_permissions
        # Get current user info
        username = session.get('username')
        user_role = session.get('user_info', {}).get('role')
        
        # Get all user permissions with debug info
        all_permissions = get_user_permissions(username, debug=True)
        permission_keys = [p['permission_key'] for p in all_permissions]
        
        # Check specific permission with debug info
        has_perm = has_permission(permission_key, debug=True)
        
        return jsonify({
            'username': username,
            'role': user_role,
            'permission': permission_key,
            'has_permission': has_perm,
            'all_permissions': permission_keys,
            'permissions_count': len(permission_keys),
            'success': True
        })
    except Exception as e:
        return jsonify({
            'message': f'Error debugging permission: {str(e)}',
            'success': False
        })
        
@app.route('/api/debug/permissions/tasks')
@admin_required
def debug_task_permissions():
    """Debug endpoint to view task-related permissions - ADMIN ONLY"""
    try:
        with get_db_cursor() as cursor:
            # Get all task permissions
            cursor.execute("""
                SELECT * FROM permissions
                WHERE category = 'tasks' OR permission_key LIKE '%task%'
                ORDER BY permission_key
            """)
            task_perms = cursor.fetchall()
            
            # Convert to serializable format
            result = []
            for perm in task_perms:
                perm_dict = dict(perm)
                
                # Get roles with this permission
                cursor.execute("""
                    SELECT r.role_key FROM roles r
                    JOIN role_permissions rp ON r.role_id = rp.role_id
                    WHERE rp.permission_id = %s
                """, (perm['permission_id'],))
                
                roles = [r['role_key'] for r in cursor.fetchall()]
                perm_dict['assigned_to_roles'] = roles
                result.append(perm_dict)
            
            return jsonify({
                'success': True,
                'permissions': result,
                'count': len(result)
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/refresh_permissions')
@login_required
def refresh_permissions():
    """Force refresh of user permissions cache"""
    try:
        # Remove current permissions from session to force reload
        if 'permissions' in session:
            session.pop('permissions')
            
        # Get username
        username = session.get('username')
        if not username:
            return jsonify({'error': 'Not logged in'}), 401
            
        # Reload permissions
        from modules.permissions import get_user_permissions
        permissions = [p['permission_key'] for p in get_user_permissions(username)]
        session['permissions'] = permissions
        
        return jsonify({
            'success': True,
            'message': 'Permissions refreshed successfully',
            'permissions_count': len(permissions)
        })
    except Exception as e:        return jsonify({'error': str(e)}), 500

@app.route('/api/users')
@login_required
@permission_required('manage_users')
def get_users_api():
    """API endpoint to get users list for role management"""
    try:
        # Check if refresh is requested
        refresh = request.args.get('refresh', '0') == '1'
        
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT user_id, username, name, email, department, role, avatar_path, last_login
                FROM users
                ORDER BY name, username
            """)
            users = cursor.fetchall()
              
            # Convert datetime objects to strings for JSON serialization
            for user in users:
                if user.get('last_login') and isinstance(user['last_login'], datetime):
                    user['last_login'] = user['last_login'].strftime('%Y-%m-%d %H:%M:%S')
            
        return jsonify({
            "success": True,
            "users": users
        })
    except Exception as e:
        logger.error(f"Error in get_users_api: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/admin/cleanup_permissions', methods=['POST'])
@admin_required
def admin_cleanup_permissions():
    """Admin endpoint to clean up duplicate permissions"""
    try:
        from modules.permission_cleanup import cleanup_task_view_permissions
        
        result = cleanup_task_view_permissions()
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Duplikaty uprawnień zostały naprawione pomyślnie.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się naprawić duplikatów uprawnień. Sprawdź logi serwera.'
            })
            
    except Exception as e:
        logger.error(f"Error cleaning up permissions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Wystąpił błąd: {str(e)}"
        }), 500

@app.route('/permissions_debug')
@admin_required
def permissions_debug():
    """Debug endpoint to view all task-related permissions"""
    try:
        with get_db_cursor() as cursor:
            # Get all task-related permissions
            cursor.execute("""
                SELECT permission_id, permission_key, name, category 
                FROM permissions 
                WHERE permission_key LIKE '%task%'
                ORDER BY category, permission_key
            """)
            
            permissions = cursor.fetchall()
            
            # Get role assignments for these permissions
            permission_ids = [p['permission_id'] for p in permissions]
            if permission_ids:
                placeholders = ', '.join(['%s'] * len(permission_ids))
                cursor.execute(f"""
                    SELECT rp.role_id, r.role_key, rp.permission_id, p.permission_key
                    FROM role_permissions rp
                    JOIN roles r ON rp.role_id = r.role_id
                    JOIN permissions p ON rp.permission_id = p.permission_id
                    WHERE p.permission_id IN ({placeholders})
                    ORDER BY r.role_key, p.permission_key
                """, permission_ids)
                
                role_permissions = cursor.fetchall()
            else:
                role_permissions = []
            
            # Build a simple debug page with the information
            html = "<html><head><title>Permissions Debug</title>"
            html += "<style>body{font-family:Arial;margin:20px;} table{border-collapse:collapse;width:100%;} "
            html += "th,td{border:1px solid #ddd;padding:8px;text-align:left;} "
            html += "th{background-color:#f2f2f2;} tr:nth-child(even){background-color:#f9f9f9;} "
            html += ".section{margin-top:30px;}</style></head><body>"
            
            html += "<h1>Task Permissions Debug</h1>"
            
            # Permissions table
            html += "<div class='section'><h2>Task-Related Permissions</h2>"
            if permissions:
                html += "<table><thead><tr><th>ID</th><th>Key</th><th>Name</th><th>Category</th></tr></thead><tbody>"
                for p in permissions:
                    html += f"<tr><td>{p['permission_id']}</td><td>{p['permission_key']}</td>"
                    html += f"<td>{p['name']}</td><td>{p['category']}</td></tr>"
                html += "</tbody></table>"
            else:
                html += "<p>No task-related permissions found.</p>"
            html += "</div>"
            
            # Role assignments table
            html += "<div class='section'><h2>Role Assignments</h2>"
            if role_permissions:
                html += "<table><thead><tr><th>Role</th><th>Permission Key</th></tr></thead><tbody>"
                for rp in role_permissions:
                    html += f"<tr><td>{rp['role_key']}</td><td>{rp['permission_key']}</td></tr>"
                html += "</tbody></table>"
            else:
                html += "<p>No role assignments for task permissions found.</p>"
            html += "</div>"
            
            html += "</body></html>"
            
            return html
            
    except Exception as e:
        logger.error(f"Error in permissions debug: {str(e)}")
        return f"<h1>Error</h1><p>{str(e)}</p>"

@app.route('/update_role_permissions', methods=['POST'])
@admin_required
def update_role_permissions():
    """API endpoint to update role permissions"""
    try:
        role_key = request.form.get('role_key')
        description_en = request.form.get('description_en', '')
        description_pl = request.form.get('description_pl', '')
        permissions = request.form.getlist('permissions[]')          # Validate the role
        if not role_key or role_key not in ['admin', 'manager', 'user', 'viewer']:
            return jsonify({
                'error': 'Invalid role specified',
                'success': False
            }), 400
        
        with get_db_cursor() as cursor:
            # Get role ID
            cursor.execute("SELECT role_id FROM roles WHERE role_key = %s", (role_key,))
            role_result = cursor.fetchone()
            
            if not role_result:
                return jsonify({
                    'error': 'Role not found',
                    'success': False
                }), 404
                
            role_id = role_result['role_id']
            
            # Update role descriptions
            cursor.execute("""
                UPDATE roles 
                SET description_en = %s, description_pl = %s 
                WHERE role_id = %s
            """, (description_en, description_pl, role_id))
            
            # Delete all existing permissions for this role
            cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
              # Add all new permissions
            if permissions:
                # Get permission IDs for the selected permission keys
                # Use placeholders for each item in the list
                placeholders = ', '.join(['%s'] * len(permissions))
                query = f"""
                    SELECT permission_id, permission_key 
                    FROM permissions 
                    WHERE permission_key IN ({placeholders})
                """
                cursor.execute(query, permissions)
                
                permission_ids = cursor.fetchall()
                
                # Insert new permissions
                for perm in permission_ids:
                    cursor.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                    """, (role_id, perm['permission_id']))
            
            # Log the update
            logger.info(f"Updated permissions for role '{role_key}'. Set {len(permissions)} permissions.")
            
            return jsonify({
                'success': True,
                'message': f"Zaktualizowano uprawnienia dla roli {role_key}",
                'updated_permissions': len(permissions)
            })
            
    except Exception as e:
        logger.error(f"Error updating role permissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Wystąpił błąd: {str(e)}"
        }), 500

if __name__ == '__main__':
    # Import required modules
    from modules.database import setup_departments_table, ensure_default_departments
    from modules.permissions import initialize_roles_and_permissions
    from modules.tasks_permissions import initialize_task_permissions
    from modules.permission_cleanup import cleanup_task_view_permissions
    
    # Initialize database tables
    setup_departments_table()
    ensure_default_departments()
    setup_tasks_tables()  # Add this line to initialize tasks tables
    
    print("Initializing roles and permissions system...")
    if initialize_roles_and_permissions():
        print("Roles and permissions system initialized successfully")
    else:
        print("Warning: Failed to initialize roles and permissions system")
    
    # Initialize task-specific permissions
    print("Initializing task permissions...")
    if initialize_task_permissions():
        print("Task permissions initialized successfully")
    else:
        print("Warning: Failed to initialize task permissions")
        
    # Clean up duplicate task view permissions
    print("Cleaning up duplicate task view permissions...")
    if cleanup_task_view_permissions():
        print("Permissions cleanup completed successfully")
    else:
        print("Warning: Failed to clean up permissions")
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)