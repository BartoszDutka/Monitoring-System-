#!/usr/bin/env python3
"""
Add view_assets permission to viewer role so they can see equipment inventory
"""

from modules.database import get_db_cursor

def add_view_assets_to_viewer():
    print("🔍 Checking view_assets permission for viewer role...")
    with get_db_cursor() as cursor:
        # Check if viewer role already has view_assets permission
        cursor.execute("""
            SELECT 1 FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.role_id
            JOIN permissions p ON rp.permission_id = p.permission_id
            WHERE r.role_key = 'viewer' AND p.permission_key = 'view_assets'
        """)
        
        if cursor.fetchone():
            print("✅ Viewer already has view_assets permission")
            return
        
        # Get viewer role ID
        cursor.execute("SELECT role_id FROM roles WHERE role_key = 'viewer'")
        viewer_role = cursor.fetchone()
        if not viewer_role:
            print("❌ Viewer role not found")
            return
        
        # Get view_assets permission ID
        cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = 'view_assets'")
        view_assets_perm = cursor.fetchone()
        if not view_assets_perm:
            print("❌ view_assets permission not found")
            return
        
        # Add the permission to viewer role
        cursor.execute("""
            INSERT INTO role_permissions (role_id, permission_id)
            VALUES (%s, %s)
        """, (viewer_role['role_id'], view_assets_perm['permission_id']))
        
        print("✅ Added view_assets permission to viewer role")
        
        # Verify the addition
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'viewer'
            ORDER BY p.category, p.permission_key
        """)
        
        print("\n📋 Updated VIEWER permissions:")
        viewer_perms = cursor.fetchall()
        for perm in viewer_perms:
            print(f"  ✓ {perm['permission_key']} - {perm['name_en']} ({perm['category']})")

if __name__ == "__main__":
    add_view_assets_to_viewer()
