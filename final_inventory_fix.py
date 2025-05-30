from modules.database import get_db_cursor

def add_missing_inventory_permissions():
    print("Dodawanie brakujących uprawnień inventory do roli USER...")
    
    try:
        with get_db_cursor() as cursor:
            # Pobierz ID roli USER
            cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
            user_role = cursor.fetchone()
            
            if not user_role:
                print("BŁĄD: Nie znaleziono roli 'user'")
                return
                
            user_role_id = user_role['role_id']
            print(f"Znaleziono rolę USER (ID: {user_role_id})")
            
            # Uprawnienia do dodania
            permissions_to_add = ['manage_equipment', 'assign_equipment']
            
            for perm_key in permissions_to_add:
                print(f"\nDodawanie uprawnienia: {perm_key}")
                
                # Sprawdź czy już ma to uprawnienie
                cursor.execute("""
                    SELECT 1 FROM role_permissions rp
                    JOIN permissions p ON rp.permission_id = p.permission_id
                    WHERE rp.role_id = %s AND p.permission_key = %s
                """, (user_role_id, perm_key))
                
                if cursor.fetchone():
                    print(f"  USER już ma uprawnienie {perm_key}")
                    continue
                
                # Pobierz ID uprawnienia
                cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm_key,))
                permission = cursor.fetchone()
                
                if not permission:
                    print(f"  BŁĄD: Nie znaleziono uprawnienia {perm_key}")
                    continue
                
                permission_id = permission['permission_id']
                
                # Dodaj uprawnienie
                cursor.execute("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (%s, %s)
                """, (user_role_id, permission_id))
                
                print(f"  ✓ Dodano uprawnienie {perm_key}")
            
            print("\n=== PODSUMOWANIE ===")
            print("1. Menu 'Item Inventory' jest ukryte dla roli 'viewer'")
            print("2. Rola 'user' ma teraz pełne uprawnienia inventory:")
            
            # Sprawdź finalne uprawnienia
            cursor.execute("""
                SELECT p.permission_key
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                WHERE rp.role_id = %s AND p.category IN ('ASSETS', 'assets')
                ORDER BY p.permission_key
            """, (user_role_id,))
            
            final_perms = cursor.fetchall()
            for perm in final_perms:
                print(f"   - {perm['permission_key']}")
                
    except Exception as e:
        print(f"BŁĄD: {e}")

if __name__ == "__main__":
    add_missing_inventory_permissions()
    print("\nGOTOWE! Inventory jest ukryte dla viewer, a user ma pełny dostęp.")
