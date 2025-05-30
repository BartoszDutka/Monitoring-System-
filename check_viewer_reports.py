from modules.database import get_db_cursor

def check_viewer_reports_access():
    print("Sprawdzanie czy viewer ma dostęp do raportów...")
    
    with get_db_cursor() as cursor:
        # Sprawdź wszystkie uprawnienia viewer
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p 
            JOIN role_permissions rp ON p.permission_id = rp.permission_id 
            JOIN roles r ON rp.role_id = r.role_id 
            WHERE r.role_key = 'viewer'
            ORDER BY p.category, p.permission_key
        """)
        
        perms = cursor.fetchall()
        print("Wszystkie uprawnienia VIEWER:")
        for perm in perms:
            print(f"  - {perm['permission_key']} ({perm['category']}) - {perm['name_en']}")
        
        # Sprawdź konkretnie view_reports
        has_view_reports = any(p['permission_key'] == 'view_reports' for p in perms)
        print(f"\nViewer ma view_reports: {has_view_reports}")
        
        # Sprawdź konkretnie view_assets
        has_view_assets = any(p['permission_key'] == 'view_assets' for p in perms)
        print(f"Viewer ma view_assets: {has_view_assets}")
        
        print("\n=== WNIOSEK ===")
        if not has_view_reports:
            print("✅ Viewer NIE MA view_reports - dlatego raporty są zablokowane!")
        if has_view_assets:
            print("❌ Viewer MA view_assets - dlatego inventory NIE jest zablokowane!")

if __name__ == "__main__":
    check_viewer_reports_access()
