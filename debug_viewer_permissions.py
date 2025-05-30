#!/usr/bin/env python3
"""
Script to debug and verify the view_assets permission for the viewer role
"""

from modules.database import get_db_cursor
from flask import session
from modules.permissions import has_permission, get_user_permissions

def debug_viewer_permissions():
    """Debug the viewer permissions"""
    print("DEBUG: Checking if viewer has view_assets permission")
    print("====================================")
    
    with get_db_cursor() as cursor:
        # Check view_assets permission
        cursor.execute("""
            SELECT p.permission_key, p.name_en
            FROM permissions p
            WHERE p.permission_key = 'view_assets'
        """)
        permission = cursor.fetchone()
        
        if not permission:
            print("ERROR: view_assets permission does not exist")
            return
            
        print(f"FOUND permission: {permission['permission_key']} - {permission['name_en']}")
        
        # Check if viewer role has this permission
        cursor.execute("""
            SELECT r.role_key, p.permission_key
            FROM roles r
            JOIN role_permissions rp ON r.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.permission_id
            WHERE r.role_key = 'viewer' AND p.permission_key = 'view_assets'
        """)
        
        role_has_permission = cursor.fetchone()
        if role_has_permission:
            print("SUCCESS: viewer role has view_assets permission")
        else:
            print("ERROR: viewer role does NOT have view_assets permission")
        
        # Check the structure of view_assets permission
        cursor.execute("""
            SELECT *
            FROM permissions
            WHERE permission_key = 'view_assets'
        """)
        
        assets_permission = cursor.fetchone()
        if assets_permission:
            print("\nview_assets permission details:")
            for key, value in assets_permission.items():
                print(f"  {key}: {value}")
        
        # Check if there's a category mismatch
        cursor.execute("""
            SELECT p.permission_key, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'viewer'
        """)
        
        viewer_permissions = cursor.fetchall()
        print("\nAll viewer permissions:")
        for perm in viewer_permissions:
            print(f"  {perm['permission_key']} (category: {perm['category']})")

if __name__ == "__main__":
    print("SCRIPT STARTING...")
    try:
        debug_viewer_permissions()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    print("SCRIPT FINISHED")
