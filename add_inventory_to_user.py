#!/usr/bin/env python3
"""
Add missing inventory permissions to USER role
"""

from modules.database import get_db_cursor

def add_inventory_permissions_to_user():
    print("🔧 Adding inventory permissions to USER role...")
    
    with get_db_cursor() as cursor:
        # Get user role ID
        cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
        user_role = cursor.fetchone()
        if not user_role:
            print("❌ User role not found")
            return
        
        # List of permissions to add
        permissions_to_add = ['manage_equipment', 'assign_equipment']
        
        for perm_key in permissions_to_add:
            # Check if user already has this permission
            cursor.execute("""
                SELECT 1 FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.role_id
                JOIN permissions p ON rp.permission_id = p.permission_id
                WHERE r.role_key = 'user' AND p.permission_key = %s
            """, (perm_key,))
            
            if cursor.fetchone():
                print(f"✅ User already has {perm_key} permission")
                continue
            
            # Get permission ID
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm_key,))
            permission = cursor.fetchone()
            if not permission:
                print(f"❌ Permission {perm_key} not found")
                continue
            
            # Add the permission to user role
            cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (%s, %s)
            """, (user_role['role_id'], permission['permission_id']))
            
            print(f"✅ Added {perm_key} permission to user role")
        
        # Verify final permissions for user
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'user' AND p.category IN ('ASSETS', 'assets')
            ORDER BY p.permission_key
        """)
        
        print("\n📋 USER asset/inventory permissions:")
        user_perms = cursor.fetchall()
        for perm in user_perms:
            print(f"  ✓ {perm['permission_key']} - {perm['name_en']} ({perm['category']})")

if __name__ == "__main__":
    add_inventory_permissions_to_user()
