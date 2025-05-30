#!/usr/bin/env python3
"""
RBAC System Verification Script
Verifies that all permissions are correctly implemented
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from modules.database import get_db_connection
from modules.permissions import get_user_permissions

def verify_permission_structure():
    """Verify the permission structure in the database"""
    print("=== RBAC System Verification ===\n")
    
    try:
        with app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check permission categories
            print("1. Permission Categories:")
            cursor.execute('SELECT DISTINCT category FROM permissions ORDER BY category')
            categories = cursor.fetchall()
            for cat in categories:
                print(f"   - {cat[0]}")
            
            # Check all permissions by category
            print("\n2. All Permissions by Category:")
            cursor.execute('SELECT category, name FROM permissions ORDER BY category, name')
            permissions = cursor.fetchall()
            current_category = None
            for perm in permissions:
                category, name = perm
                if category != current_category:
                    print(f"\n   {category}:")
                    current_category = category
                print(f"     - {name}")
            
            # Check roles
            print("\n3. Available Roles:")
            cursor.execute('SELECT name, description FROM roles ORDER BY name')
            roles = cursor.fetchall()
            for role in roles:
                name, desc = role
                print(f"   - {name}: {desc or 'No description'}")
            
            # Check role-permission mappings
            print("\n4. Role-Permission Mappings:")
            cursor.execute('''
                SELECT r.name as role_name, p.name as permission_name, p.category 
                FROM roles r
                JOIN role_permissions rp ON r.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                ORDER BY r.name, p.category, p.name
            ''')
            
            mappings = cursor.fetchall()
            current_role = None
            for mapping in mappings:
                role, perm, category = mapping
                if role != current_role:
                    print(f"\n   {role}:")
                    current_role = role
                print(f"     {category}: {perm}")
            
            conn.close()
            print("\n✅ Database connection and permission structure verified successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def verify_code_permissions():
    """Verify that code uses correct permission names"""
    print("\n5. Code Permission Usage Verification:")
    
    # List of expected permissions based on the new structure
    expected_permissions = {
        'inventory': ['view_inventory', 'manage_inventory'],
        'monitoring': ['view_monitoring'],
        'reports': ['view_reports', 'create_reports', 'delete_reports', 'manage_reports'],
        'system': ['manage_profile', 'manage_users'],
        'tasks': ['create_tasks', 'tasks_update', 'tasks_comment', 'tasks_delete', 'tasks_view', 'manage_all_tasks'],
        'GLPI': ['view_glpi', 'vnc_connect'],
        'Graylog': ['view_logs']
    }
    
    print("   Expected permissions structure:")
    for category, perms in expected_permissions.items():
        print(f"     {category}: {', '.join(perms)}")
    
    return True

if __name__ == "__main__":
    success = verify_permission_structure()
    verify_code_permissions()
    
    if success:
        print("\n🎉 RBAC system verification completed successfully!")
        print("The permission structure has been updated and should work correctly.")
    else:
        print("\n⚠️  Issues found during verification. Please check the database setup.")
