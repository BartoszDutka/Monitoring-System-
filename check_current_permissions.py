#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.database import connect_db

def check_current_permissions():
    """Check current permissions in database"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("=== Current Permissions in Database ===")
    cursor.execute("""
        SELECT permission_key, permission_name, category, description 
        FROM permissions 
        ORDER BY category, permission_key
    """)
    
    current_category = None
    for row in cursor.fetchall():
        permission_key, permission_name, category, description = row
        if category != current_category:
            print(f"\n{category.upper()}:")
            current_category = category
        print(f"  {permission_key} - {permission_name}")
        if description:
            print(f"    └─ {description}")
    
    print("\n=== VIEWER Role Permissions ===")
    cursor.execute("""
        SELECT p.permission_key, p.permission_name, p.category
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        JOIN roles r ON rp.role_id = r.id
        WHERE r.role_name = 'viewer'
        ORDER BY p.category, p.permission_key
    """)
    
    viewer_perms = cursor.fetchall()
    print(f"VIEWER has {len(viewer_perms)} permissions:")
    for row in viewer_perms:
        permission_key, permission_name, category = row
        print(f"  {category}: {permission_key} - {permission_name}")
    
    conn.close()

if __name__ == '__main__':
    check_current_permissions()
