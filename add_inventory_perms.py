from modules.database import get_db_cursor

def add_inventory_permissions():
    print("Starting to add inventory permissions to USER role...")
    
    try:
        with get_db_cursor() as cursor:
            # First check current USER permissions
            cursor.execute("""
                SELECT p.permission_key
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = 'user' AND p.category IN ('ASSETS', 'assets')
            """)
            current_perms = [row['permission_key'] for row in cursor.fetchall()]
            print(f"Current USER inventory permissions: {current_perms}")
            
            # Get user role ID
            cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
            user_role = cursor.fetchone()
            if not user_role:
                print("ERROR: User role not found")
                return
            print(f"Found USER role with ID: {user_role['role_id']}")
            
            # Permissions to add
            permissions_to_add = ['manage_equipment', 'assign_equipment']
            
            for perm_key in permissions_to_add:
                print(f"\nProcessing permission: {perm_key}")
                
                # Check if user already has this permission
                if perm_key in current_perms:
                    print(f"  User already has {perm_key} permission")
                    continue
                
                # Get permission ID
                cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm_key,))
                permission = cursor.fetchone()
                if not permission:
                    print(f"  ERROR: Permission {perm_key} not found in database")
                    continue
                
                print(f"  Found permission {perm_key} with ID: {permission['permission_id']}")
                
                # Add the permission to user role
                cursor.execute("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s)
                """, (user_role['role_id'], permission['permission_id']))
                
                print(f"  Successfully added {perm_key} permission to USER role")
            
            print("\n=== FINAL USER INVENTORY PERMISSIONS ===")
            cursor.execute("""
                SELECT p.permission_key, p.name_en
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = 'user' AND p.category IN ('ASSETS', 'assets')
                ORDER BY p.permission_key
            """)
            
            final_perms = cursor.fetchall()
            for perm in final_perms:
                print(f"  * {perm['permission_key']} - {perm['name_en']}")
                
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_inventory_permissions()
    print("Done!")
