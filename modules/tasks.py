from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from modules.database import get_db_cursor
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

# Define a path for task attachments
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'attachments')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

tasks = Blueprint('tasks', __name__, url_prefix='/tasks')

def login_required(f):
    """Decorator to check if user is logged in"""
    from functools import wraps
    from flask import session, redirect, url_for
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to check if user is an admin"""
    from functools import wraps
    from flask import session, redirect, url_for, render_template
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        if session.get('user_info', {}).get('role') != 'admin':
            return render_template('403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

@tasks.route('/')
@login_required
def index():
    """Show tasks page based on user role"""
    user_role = session.get('user_info', {}).get('role', 'viewer')
    username = session.get('username')
    
    with get_db_cursor() as cursor:
        if user_role == 'admin':
            # Admins see all tasks
            cursor.execute("""
                SELECT t.*, u.display_name as assignee_name 
                FROM tasks t
                LEFT JOIN users u ON t.assignee = u.username
                ORDER BY t.created_at DESC
            """)
        else:
            # Users see only their tasks
            cursor.execute("""
                SELECT t.*, u.display_name as assignee_name 
                FROM tasks t
                LEFT JOIN users u ON t.assignee = u.username
                WHERE t.assignee = %s
                ORDER BY t.created_at DESC
            """, (username,))
        
        tasks_list = cursor.fetchall()
        
    # Get users list for assignment
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT username, display_name, email, department
            FROM users
            ORDER BY username
        """)
        users = cursor.fetchall()
        
    return render_template('tasks.html', 
                          tasks=tasks_list, 
                          users=users, 
                          is_admin=(user_role == 'admin'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@tasks.route('/create', methods=['POST'])
@admin_required
def create_task():
    """Create a new task"""
    title = request.form.get('title')
    description = request.form.get('description')
    assignee = request.form.get('assignee')
    priority = request.form.get('priority', 'medium')
    due_date = request.form.get('due_date')
    related_type = request.form.get('related_type')
    related_id = request.form.get('related_id')
    related_data = request.form.get('related_data', '{}')
    
    # Validate input
    if not title or not assignee:
        flash('Title and assignee are required')
        return redirect(url_for('tasks.index'))
    
    attachment_path = None
    
    # Handle file upload
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename and allowed_file(file.filename):
            # Create a secure filename with timestamp
            filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            attachment_path = filename
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO tasks (
                title, description, assignee, creator, 
                status, priority, due_date, 
                related_type, related_id, related_data,
                attachment_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            title, description, assignee, session.get('username'),
            'new', priority, due_date if due_date else None,
            related_type, related_id, related_data,
            attachment_path
        ))
        
    flash('Task created successfully')
    return redirect(url_for('tasks.index'))

@tasks.route('/update/<int:task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    """Update a task status"""
    status = request.form.get('status')
    comment = request.form.get('comment', '')
    
    user_role = session.get('user_info', {}).get('role')
    username = session.get('username')
    
    # Get current task details
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM tasks WHERE task_id = %s
        """, (task_id,))
        task = cursor.fetchone()
        
    if not task:
        flash('Task not found')
        return redirect(url_for('tasks.index'))
        
    # Only assignee or admin can update task
    if username != task['assignee'] and user_role != 'admin':
        flash('You cannot update this task')
        return redirect(url_for('tasks.index'))
    
    # Update task status
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE tasks SET
            status = %s,
            updated_at = CURRENT_TIMESTAMP
            WHERE task_id = %s
        """, (status, task_id))
        
    # Add comment if provided
    if comment:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO task_comments (
                    task_id, username, comment
                ) VALUES (%s, %s, %s)
            """, (task_id, username, comment))
    
    flash('Task updated successfully')
    return redirect(url_for('tasks.index'))

@tasks.route('/delete/<int:task_id>', methods=['POST'])
@admin_required
def delete_task(task_id):
    """Delete a task"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            DELETE FROM tasks WHERE task_id = %s
        """, (task_id,))
        
    flash('Task deleted successfully')
    return redirect(url_for('tasks.index'))

@tasks.route('/api/task/<int:task_id>')
@login_required
def get_task(task_id):
    """Get task details"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT t.*, u.display_name as assignee_name 
            FROM tasks t
            LEFT JOIN users u ON t.assignee = u.username
            WHERE t.task_id = %s
        """, (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        # Get comments
        cursor.execute("""
            SELECT c.*, u.display_name
            FROM task_comments c
            LEFT JOIN users u ON c.username = u.username
            WHERE c.task_id = %s
            ORDER BY c.created_at
        """, (task_id,))
        comments = cursor.fetchall()
        
    # Convert to JSON-serializable format
    task_data = dict(task)
    task_data['created_at'] = task_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    task_data['updated_at'] = task_data['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if task_data['updated_at'] else None
    task_data['due_date'] = task_data['due_date'].strftime('%Y-%m-%d') if task_data['due_date'] else None
    
    # Add attachment URL if present
    if task_data.get('attachment_path'):
        task_data['attachment_url'] = url_for('tasks.get_attachment', filename=task_data['attachment_path'])
    
    if task_data.get('related_data'):
        try:
            task_data['related_data'] = json.loads(task_data['related_data'])
        except (json.JSONDecodeError, TypeError):
            task_data['related_data'] = {}
    
    comments_data = []
    for comment in comments:
        comment_dict = dict(comment)
        comment_dict['created_at'] = comment_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        comments_data.append(comment_dict)
        
    return jsonify({
        'task': task_data,
        'comments': comments_data
    })

@tasks.route('/attachments/<path:filename>')
@login_required
def get_attachment(filename):
    """Serve task attachment files"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@tasks.route('/add_comment/<int:task_id>', methods=['POST'])
@login_required
def add_comment(task_id):
    """Add a comment to a task"""
    comment = request.form.get('comment')
    
    if not comment:
        flash('Comment cannot be empty')
        return redirect(url_for('tasks.index'))
        
    username = session.get('username')
    
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO task_comments (
                task_id, username, comment
            ) VALUES (%s, %s, %s)
        """, (task_id, username, comment))
        
    flash('Comment added successfully')
    return redirect(url_for('tasks.index'))

@tasks.route('/api/devices')
@login_required
def get_devices():
    """Get all devices from assets table for task related items"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    asset_id as id, 
                    name, 
                    type,
                    serial_number, 
                    model,
                    manufacturer,
                    location,
                    ip_address
                FROM assets
                WHERE status = 'active'
                ORDER BY name
            """)
            devices = cursor.fetchall()
            
            # Convert to list of dictionaries for JSON serialization
            return jsonify(devices)
    except Exception as e:
        print(f"Error fetching devices: {e}")
        return jsonify([]), 500

@tasks.route('/api/related_device/<int:device_id>')
@login_required
def get_related_device(device_id):
    """Get information about a related device"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    asset_id,
                    name, 
                    type,
                    serial_number, 
                    model,
                    manufacturer,
                    location,
                    ip_address,
                    mac_address,
                    os_info,
                    last_seen
                FROM assets
                WHERE asset_id = %s
            """, (device_id,))
            device = cursor.fetchone()
            
            if not device:
                return jsonify({"error": "Device not found"}), 404
                
            # Format dates for JSON serialization
            if device.get('last_seen'):
                device['last_seen'] = device['last_seen'].strftime('%Y-%m-%d %H:%M:%S')
                
            return jsonify(device)
    except Exception as e:
        print(f"Error fetching related device: {e}")
        return jsonify({"error": str(e)}), 500

def setup_tasks_tables():
    """Create tasks tables if not exists"""
    with get_db_cursor() as cursor:
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                assignee VARCHAR(100) NOT NULL,
                creator VARCHAR(100) NOT NULL,
                status ENUM('new', 'in_progress', 'completed', 'cancelled') NOT NULL DEFAULT 'new',
                priority ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium',
                due_date DATE,
                related_type VARCHAR(50),
                related_id VARCHAR(100),
                related_data TEXT,
                attachment_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Task comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_comments (
                comment_id INT AUTO_INCREMENT PRIMARY KEY,
                task_id INT NOT NULL,
                username VARCHAR(100) NOT NULL,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)