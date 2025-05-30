#!/usr/bin/env python3
import sys
import os
sys.path.append('.')

try:
    from modules.database import get_db_cursor
    print("Database module imported successfully")
    
    with get_db_cursor() as cursor:
        print("Database connection established")
        
        # Check current USER permissions for inventory
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'user' AND p.permission_key IN ('view_assets', 'manage_equipment', 'assign_equipment')
            ORDER BY p.permission_key
        """)
        
        current_perms = cursor.fetchall()
        print(f"\nCurrent USER inventory permissions: {len(current_perms)} found")
        for perm in current_perms:
            print(f"  - {perm['permission_key']}")
        
        # Check what's missing
        required = ['view_assets', 'manage_equipment', 'assign_equipment']
        existing = [p['permission_key'] for p in current_perms]
        missing = [p for p in required if p not in existing]
        
        print(f"\nMissing permissions: {missing}")
        
        if missing:
            print("\nAdding missing permissions...")
            
            # Get USER role ID
            cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
            user_role = cursor.fetchone()
            
            for perm_key in missing:
                cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm_key,))
                permission = cursor.fetchone()
                
                if permission:
                    cursor.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                    """, (user_role['role_id'], permission['permission_id']))
                    print(f"  Added {perm_key}")
                else:
                    print(f"  Permission {perm_key} not found in database")
        
        print("\n=== FINAL CHECK ===")
        cursor.execute("""
            SELECT p.permission_key
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'user' AND p.permission_key IN ('view_assets', 'manage_equipment', 'assign_equipment')
            ORDER BY p.permission_key
        """)
        
        final_perms = [row['permission_key'] for row in cursor.fetchall()]
        print(f"USER now has inventory permissions: {final_perms}")
        
        # Check all roles have correct setup
        print("\n=== ROLE SUMMARY ===")
        for role in ['viewer', 'user']:
            cursor.execute("""
                SELECT p.permission_key
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = %s AND p.permission_key IN ('view_assets', 'manage_equipment', 'assign_equipment')
                ORDER BY p.permission_key
            """, (role,))
            
            role_perms = [row['permission_key'] for row in cursor.fetchall()]
            print(f"{role.upper()}: {role_perms}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
