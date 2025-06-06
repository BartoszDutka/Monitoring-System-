import functools
from flask import session, redirect, url_for, render_template, flash, request
from .database import get_db_cursor
from typing import List, Optional, Dict, Any

def get_user_permissions(username: str, debug: bool = False) -> List[Dict[str, Any]]:
    """
    Get all permissions assigned to a user's role
    Set debug=True to print information for troubleshooting
    """
    with get_db_cursor() as cursor:
        # First, get the user's role
        cursor.execute("""
            SELECT role FROM users WHERE username = %s
        """, (username,))
        user_result = cursor.fetchone()
        
        if not user_result:
            if debug:
                print(f"DEBUG get_user_permissions: User '{username}' not found")
            return []
            
        user_role = user_result['role']
        
        if debug:
            print(f"DEBUG get_user_permissions: User '{username}' has role '{user_role}'")
        
        # Get the role_id from the roles table
        cursor.execute("""
            SELECT role_id FROM roles WHERE role_key = %s
        """, (user_role,))
        role_result = cursor.fetchone()
        
        if not role_result:
            if debug:
                print(f"DEBUG get_user_permissions: Role '{user_role}' not found in roles table")
            return []
            
        role_id = role_result['role_id']
        
        # Get all permissions assigned to this role
        cursor.execute("""
            SELECT p.* FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.category, p.name_en
        """, (role_id,))
        
        permissions = cursor.fetchall()
        
        if debug:
            perm_keys = [p['permission_key'] for p in permissions]
            print(f"DEBUG get_user_permissions: User '{username}' has {len(permissions)} permissions: {perm_keys}")
            
        return permissions

def has_permission(permission_key: str, debug: bool = False) -> bool:
    """
    Check if the current user has a specific permission
    Set debug=True to print information for troubleshooting
    """
    if not session.get('logged_in'):
        if debug:
            print(f"DEBUG permission '{permission_key}': User not logged in")
        return False
        
    # Admin has all permissions
    if session.get('user_info', {}).get('role') == 'admin':
        if debug:
            print(f"DEBUG permission '{permission_key}': Admin has all permissions")
        return True
        
    # Get user permissions
    username = session.get('username')
    if not username:
        if debug:
            print(f"DEBUG permission '{permission_key}': No username in session")
        return False
        
    # Get permissions from cache if available
    if 'permissions' not in session:
        permissions = [p['permission_key'] for p in get_user_permissions(username, debug=debug)]
        session['permissions'] = permissions
        if debug:
            print(f"DEBUG permission '{permission_key}': Retrieved permissions from database: {permissions}")
    else:
        permissions = session['permissions']
        if debug:
            print(f"DEBUG permission '{permission_key}': Using cached permissions: {permissions}")
    
    has_perm = permission_key in permissions
    
    if debug:
        print(f"DEBUG permission '{permission_key}': Result = {has_perm}")
        
    return has_perm

def permission_required(permission_key: str):
    """
    Decorator to check if user has specific permission
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                            return redirect(url_for('login', next=request.url))
                
            if not has_permission(permission_key):
                flash("Nie masz uprawnień do wykonania tej akcji", "error")
                return render_template('errors/403.html'), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(required_roles: List[str]):
    """
    Decorator to check if user has one of the required roles
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login', next=request.url))
                
            user_role = session.get('user_info', {}).get('role')
            if not user_role or user_role not in required_roles:
                return render_template('errors/403.html'), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Define convenience decorators for common role checks
def admin_required(f):
    return role_required(['admin'])(f)
    
def manager_required(f):
    return role_required(['admin', 'manager'])(f)

def get_role_description(role_key: str, language: str = 'en') -> str:
    """
    Get the description for a specific role in the specified language
    """
    with get_db_cursor() as cursor:
        field = f"description_{language}" if language in ('en', 'pl') else "description_en"
        
        cursor.execute(f"""
            SELECT {field} FROM roles WHERE role_key = %s
        """, (role_key,))
        
        result = cursor.fetchone()
        return result[field] if result else ""

def get_all_roles():
    """
    Get all available roles
    """
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT role_key, description_en, description_pl            FROM roles
            ORDER BY FIELD(role_key, 'admin', 'manager', 'user', 'viewer')
        """)
        return cursor.fetchall()

def get_permissions_by_category(language: str = 'en'):
    """
    Get all permissions grouped by category
    """
    field_name = f"name_{language}" if language in ('en', 'pl') else "name_en"
    field_desc = f"description_{language}" if language in ('en', 'pl') else "description_en"
    
    with get_db_cursor() as cursor:
        cursor.execute(f"""
            SELECT permission_key, category, {field_name} as name, {field_desc} as description
            FROM permissions
            ORDER BY category, {field_name}
        """)
        
        permissions = cursor.fetchall()
        result = {}
        
        for perm in permissions:
            category = perm['category']
            if category not in result:
                result[category] = []
            result[category].append(perm)
            
        return result

def get_role_permissions(role_key: str) -> List[Dict[str, Any]]:
    """
    Get all permissions for a specific role
    """
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT p.* FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = %s
            ORDER BY p.category, p.name_en
        """, (role_key,))
        
        return cursor.fetchall()

def can_user_perform_action(username: str, permission_key: str) -> bool:
    """
    Check if a specific user can perform an action (has permission)
    Used for dynamic UI rendering
    """
    # Get user role
    with get_db_cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        
        if not user_result:
            return False
            
        role = user_result['role']
        
        # Admin has all permissions
        if role == 'admin':
            return True
            
        # Check role permissions
        cursor.execute("""
            SELECT 1 FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = %s AND p.permission_key = %s
            LIMIT 1
        """, (role, permission_key))
        
        return cursor.fetchone() is not None

def get_user_preferences(user_id: int, preference_key: str = None) -> Dict[str, Any]:
    """
    Get user preferences for personalization
    """
    with get_db_cursor() as cursor:
        if preference_key:
            cursor.execute("""
                SELECT preference_key, preference_value 
                FROM user_preferences 
                WHERE user_id = %s AND preference_key = %s
            """, (user_id, preference_key))
            result = cursor.fetchone()
            return {result['preference_key']: result['preference_value']} if result else {}
        else:
            cursor.execute("""
                SELECT preference_key, preference_value 
                FROM user_preferences 
                WHERE user_id = %s
            """, (user_id,))
            results = cursor.fetchall()
            return {r['preference_key']: r['preference_value'] for r in results} if results else {}

def set_user_preference(user_id: int, preference_key: str, preference_value: str) -> bool:
    """
    Set or update a user preference
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_preferences (user_id, preference_key, preference_value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE preference_value = %s
            """, (user_id, preference_key, preference_value, preference_value))
            return True
    except Exception as e:
        print(f"Error setting user preference: {e}")
        return False

def debug_role_permissions(role_key: str):
    """
    Debug helper function to print detailed role permission information
    """
    print(f"\n=== DEBUG ROLE PERMISSIONS FOR '{role_key}' ===")
    
    with get_db_cursor() as cursor:
        # 1. Check if role exists
        cursor.execute("SELECT * FROM roles WHERE role_key = %s", (role_key,))
        role = cursor.fetchone()
        
        if not role:
            print(f"ERROR: Role '{role_key}' not found in database!")
            return
        
        print(f"Role found: ID={role['role_id']}, Name={role_key}")
        print(f"Description (EN): {role['description_en']}")
        print(f"Description (PL): {role['description_pl']}")
        
        # 2. Get permissions count
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM role_permissions
            WHERE role_id = %s
        """, (role['role_id'],))
        count = cursor.fetchone()['count']
        print(f"Total permissions: {count}")
        
        # 3. Get detailed permissions
        cursor.execute("""
            SELECT p.permission_key, p.category, p.name_en, p.name_pl
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.category, p.name_en
        """, (role['role_id'],))
        
        permissions = cursor.fetchall()
        
        # Group by category
        by_category = {}
        for p in permissions:
            cat = p['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(p['permission_key'])
        
        # Print permissions by category
        print("\nPermissions by category:")
        for cat, perms in by_category.items():
            print(f"  {cat} ({len(perms)}):")
            for p in perms:
                print(f"    - {p}")
                
    print("="*40)

def initialize_roles_and_permissions():
    """
    Check if roles and permissions tables are populated, if not, run the SQL script
    """
    with get_db_cursor() as cursor:
        # Check if the roles table exists and has data
        cursor.execute("SHOW TABLES LIKE 'roles'")
        roles_table_exists = cursor.fetchone() is not None
        
        if roles_table_exists:
            cursor.execute("SELECT COUNT(*) as count FROM roles")
            roles_count = cursor.fetchone()['count']
            
            if roles_count > 0:
                # Roles already initialized
                return True
    
    # If we get here, we need to initialize the roles and permissions
    try:
        # Read the SQL script
        import os
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'role_system_update.sql')
        
        if os.path.exists(script_path):
            with open(script_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                
            # Execute each statement separately
            with get_db_cursor() as cursor:
                # Split by semicolons but preserve those in quotes
                import re
                statements = re.split(r';(?=(?:[^\']*\'[^\']*\')*[^\']*$)', sql_script)
                
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        cursor.execute(statement)
                        
            return True
    except Exception as e:
        print(f"Error initializing roles and permissions: {e}")
        return False
