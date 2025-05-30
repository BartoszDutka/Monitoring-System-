from modules.database import get_db_cursor

def check_user_inventory_permissions():
    print("Sprawdzanie uprawnień dla roli USER...")
    
    with get_db_cursor() as cursor:
        # Sprawdź obecne uprawnienia USER dla inventory
        cursor.execute("""
            SELECT p.permission_key, p.name_en
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'user' AND p.category IN ('ASSETS', 'assets')
            ORDER BY p.permission_key
        """)
        
        print("Obecne uprawnienia USER dla inventory:")
        perms = cursor.fetchall()
        if perms:
            for perm in perms:
                print(f"  - {perm['permission_key']} ({perm['name_en']})")
        else:
            print("  BRAK uprawnień inventory!")
        
        # Sprawdź wymagane uprawnienia
        required_perms = ['view_assets', 'manage_equipment', 'assign_equipment']
        print("\nSprawdzenie wymaganych uprawnień:")
        
        for req_perm in required_perms:
            cursor.execute("""
                SELECT 1 FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.role_id
                JOIN permissions p ON rp.permission_id = p.permission_id
                WHERE r.role_key = 'user' AND p.permission_key = %s
            """, (req_perm,))
            has_perm = cursor.fetchone()
            status = "✓ MA" if has_perm else "✗ BRAK"
            print(f"  {req_perm}: {status}")

if __name__ == "__main__":
    check_user_inventory_permissions()
