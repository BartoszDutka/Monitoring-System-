from modules.database import get_db_cursor

def check_user_permissions():
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'user' AND p.category IN ('ASSETS', 'assets')
            ORDER BY p.permission_key
        """)
        
        print("USER ROLE INVENTORY PERMISSIONS:")
        user_perms = cursor.fetchall()
        for perm in user_perms:
            print(f"  * {perm['permission_key']} - {perm['name_en']} ({perm['category']})")
        
        # Check specifically for the required inventory permissions
        required_perms = ['view_assets', 'manage_equipment', 'assign_equipment']
        print("\nREQUIRED INVENTORY PERMISSIONS CHECK:")
        for req_perm in required_perms:
            cursor.execute("""
                SELECT 1 FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.role_id
                JOIN permissions p ON rp.permission_id = p.permission_id
                WHERE r.role_key = 'user' AND p.permission_key = %s
            """, (req_perm,))
            has_perm = cursor.fetchone()
            status = "YES" if has_perm else "NO"
            print(f"  {req_perm}: {status}")

if __name__ == "__main__":
    check_user_permissions()
