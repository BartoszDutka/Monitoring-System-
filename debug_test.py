#!/usr/bin/env python3
import sys
import os

print("=== RBAC TESTING DEBUG ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    print("Attempting to import modules...")
    from modules.database import get_db_cursor
    print("✓ Database module imported successfully")
    
    from modules.permissions import has_permission, get_user_permissions
    print("✓ Permissions module imported successfully")
    
    print("Testing database connection...")
    with get_db_cursor() as cursor:
        cursor.execute('SELECT 1 as test')
        result = cursor.fetchone()
        print(f"✓ Database connection successful: {result}")
        
        # Check tables
        cursor.execute("SHOW TABLES LIKE 'roles'")
        roles_table = cursor.fetchone()
        print(f"Roles table exists: {roles_table is not None}")
        
        if roles_table:
            cursor.execute('SELECT COUNT(*) as count FROM roles')
            count = cursor.fetchone()
            print(f"Roles count: {count['count']}")
        
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("=== END DEBUG ===")
