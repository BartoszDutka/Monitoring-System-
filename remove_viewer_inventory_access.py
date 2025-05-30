from modules.database import get_db_cursor

def remove_viewer_inventory_access():
    print("Usuwanie dostępu viewer do inventory...")
    
    try:
        with get_db_cursor() as cursor:
            # Sprawdź obecne uprawnienia viewer
            cursor.execute("""
                SELECT p.permission_key, p.name_en
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = 'viewer' AND p.category IN ('ASSETS', 'assets')
            """)
            
            current_perms = cursor.fetchall()
            print("Obecne uprawnienia inventory dla viewer:")
            for perm in current_perms:
                print(f"  - {perm['permission_key']} ({perm['name_en']})")
            
            if not current_perms:
                print("Viewer nie ma żadnych uprawnień inventory - już zablokowany!")
                return
                
            # Usuń wszystkie uprawnienia inventory z roli viewer
            cursor.execute("""
                DELETE rp FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.role_id
                JOIN permissions p ON rp.permission_id = p.permission_id
                WHERE r.role_key = 'viewer' AND p.category IN ('ASSETS', 'assets')
            """)
            
            rows_affected = cursor.rowcount
            print(f"Usunięto {rows_affected} uprawnień inventory z roli viewer")
            
            # Sprawdź końcowy stan
            cursor.execute("""
                SELECT p.permission_key
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = 'viewer' AND p.category IN ('ASSETS', 'assets')
            """)
            
            remaining_perms = cursor.fetchall()
            if remaining_perms:
                print("POZOSTAŁE uprawnienia inventory:")
                for perm in remaining_perms:
                    print(f"  - {perm['permission_key']}")
            else:
                print("✅ Viewer NIE MA już żadnych uprawnień inventory")
                print("✅ Teraz dostanie 'Access Denied' przy próbie wejścia w /inventory")
                
    except Exception as e:
        print(f"BŁĄD: {e}")

if __name__ == "__main__":
    remove_viewer_inventory_access()
    print("\nGOTOWE! Viewer zostanie zablokowany przy próbie wejścia w inventory.")
