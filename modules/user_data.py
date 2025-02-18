import json
import os
from modules.database import get_db_cursor
from werkzeug.security import generate_password_hash, check_password_hash

USER_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'user_data.json')

# Upewnij się, że folder data istnieje
os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def create_user(username, email, password, display_name=None, role='user'):
    """Create a new user"""
    with get_db_cursor() as cursor:
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, display_name, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, email, password_hash, display_name, role))

def update_user_avatar(username, avatar_filename):
    """Update user's avatar path"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE users 
            SET avatar_path = %s 
            WHERE username = %s
        """, (avatar_filename, username))

def get_user_avatar(username):
    """Get user's avatar filename from database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT avatar_path
            FROM users 
            WHERE username = %s
        """, (username,))
        result = cursor.fetchone()
        return result['avatar_path'] if result else None

def get_user_info(username):
    """Get user information from database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT user_id, username, email, display_name, avatar_path, 
                   role, department
            FROM users 
            WHERE username = %s
        """, (username,))
        return cursor.fetchone()

def verify_user(username, password):
    """Verify user credentials"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT password_hash 
            FROM users 
            WHERE username = %s
        """, (username,))
        result = cursor.fetchone()
        if result and check_password_hash(result['password_hash'], password):
            return True
        return False

def update_user_profile(username: str, email: str = None, department: str = None, role: str = None):
    """Update user profile information"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE users 
            SET email = COALESCE(%s, email),
                department = COALESCE(%s, department),
                role = COALESCE(%s, role)
            WHERE username = %s
        """, (email, department, role, username))
