from modules.database import get_db_cursor

def find_permission_to_block_viewer():
    print("Szukanie uprawnienia które ma USER ale nie ma VIEWER...")
    
    with get_db_cursor() as cursor:
        # Uprawnienia USER
        cursor.execute("""
            SELECT p.permission_key
            FROM permissions p 
            JOIN role_permissions rp ON p.permission_id = rp.permission_id 
            JOIN roles r ON rp.role_id = r.role_id 
            WHERE r.role_key = 'user'
        """)
        user_perms = {row['permission_key'] for row in cursor.fetchall()}
        
        # Uprawnienia VIEWER
        cursor.execute("""
            SELECT p.permission_key
            FROM permissions p 
            JOIN role_permissions rp ON p.permission_id = rp.permission_id 
            JOIN roles r ON rp.role_id = r.role_id 
            WHERE r.role_key = 'viewer'
        """)
        viewer_perms = {row['permission_key'] for row in cursor.fetchall()}
        
        print(f"USER ma {len(user_perms)} uprawnień")
        print(f"VIEWER ma {len(viewer_perms)} uprawnień")
        
        # Co ma USER a nie ma VIEWER
        user_only = user_perms - viewer_perms
        print(f"\nUprawnień które ma USER ale NIE MA VIEWER ({len(user_only)}):")
        for perm in sorted(user_only):
            print(f"  - {perm}")
        
        # Sugestia dla inventory
        if 'manage_equipment' in user_only:
            print("\n✅ ROZWIĄZANIE: Użyj @permission_required('manage_equipment')")
            print("   - USER ma to uprawnienie → dostęp do inventory")
            print("   - VIEWER nie ma → Access Denied")
        elif 'view_reports' in user_only:
            print("\n✅ ROZWIĄZANIE: Użyj @permission_required('view_reports')")  
            print("   - USER ma to uprawnienie → dostęp do inventory")
            print("   - VIEWER nie ma → Access Denied")
        else:
            print(f"\n✅ ROZWIĄZANIE: Użyj dowolnego z: {list(user_only)[:3]}")

if __name__ == "__main__":
    find_permission_to_block_viewer()
