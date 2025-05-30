#!/usr/bin/env python3

from modules.database import get_db_cursor

def add_inventory_permissions_to_user():
    """
    Add missing inventory permissions to user role to match manager functionality
    """
    # Permissions that user role needs to access inventory like manager
    permissions_to_add = [
        'assign_assets',      # Assign assets to departments/users
        'assign_equipment',   # Required by inventory.html template (line 335)
        'manage_assets',      # Manage assets
        'manage_equipment'    # Required by inventory.html template (lines 45, 62)
    ]
    
    print("=== DODAWANIE UPRAWNIEŃ INVENTORY DO ROLI USER ===\n")
    
    with get_db_cursor() as cursor:
        # Get user role ID
        cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
        user_role = cursor.fetchone()
        
        if not user_role:
            print("ERROR: Role 'user' not found!")
            return False
            
        user_role_id = user_role['role_id']
        print(f"User role ID: {user_role_id}")
        
        # Check and add each permission
        for perm_key in permissions_to_add:
            # Get permission ID
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm_key,))
            perm = cursor.fetchone()
            
            if not perm:
                print(f"WARNING: Permission '{perm_key}' not found in database!")
                continue
                
            perm_id = perm['permission_id']
            
            # Check if already assigned
            cursor.execute("""
                SELECT 1 FROM role_permissions 
                WHERE role_id = %s AND permission_id = %s
            """, (user_role_id, perm_id))
            
            if cursor.fetchone():
                print(f"✓ Permission '{perm_key}' already assigned to user role")
            else:
                # Add permission
                cursor.execute("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s)
                """, (user_role_id, perm_id))
                print(f"✅ Added permission '{perm_key}' to user role")
        
        print(f"\n=== WERYFIKACJA ===")
        
        # Verify final permissions count
        cursor.execute("""
            SELECT COUNT(*) as count FROM role_permissions WHERE role_id = %s
        """, (user_role_id,))
        final_count = cursor.fetchone()['count']
        print(f"User role now has {final_count} total permissions")
        
        # Show inventory permissions
        cursor.execute("""
            SELECT p.permission_key, p.category 
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s AND p.category IN ('assets', 'ASSETS')
            ORDER BY p.permission_key
        """, (user_role_id,))
        
        inventory_perms = cursor.fetchall()
        print("Inventory permissions for user role:")
        for p in inventory_perms:
            print(f"  - {p['permission_key']} ({p['category']})")
            
    print("\n✅ User role updated successfully!")
    print("User role can now access inventory functionality like manager role")
    return True

if __name__ == "__main__":
    add_inventory_permissions_to_user()
