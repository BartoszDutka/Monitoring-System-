#!/usr/bin/env python3
"""
Check equipment-related permissions in the database
"""

from modules.database import get_db_cursor

def check_equipment_permissions():
    print("Starting check...")
    with get_db_cursor() as cursor:
        print("Connected to database...")
        # Check all permissions related to viewing or equipment
        cursor.execute("""
            SELECT permission_key, name_en, category, description_en
            FROM permissions 
            WHERE permission_key LIKE '%view%' 
               OR permission_key LIKE '%equipment%' 
               OR permission_key LIKE '%inventory%'
               OR category = 'ASSETS'
            ORDER BY category, permission_key
        """)
        
        permissions = cursor.fetchall()
        
        print("=== Equipment/View Related Permissions ===")
        current_category = None
        for perm in permissions:
            if perm['category'] != current_category:
                print(f"\n{perm['category']}:")
                current_category = perm['category']
            print(f"  {perm['permission_key']} - {perm['name_en']}")
            if perm['description_en']:
                print(f"    └─ {perm['description_en']}")
        
        # Check what permissions viewer has
        print("\n=== VIEWER Role Permissions ===")
        cursor.execute("""
            SELECT p.permission_key, p.name_en, p.category
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'viewer'
            ORDER BY p.category, p.permission_key
        """)
        
        viewer_perms = cursor.fetchall()
        for perm in viewer_perms:
            print(f"  {perm['permission_key']} - {perm['name_en']} ({perm['category']})")
        
        # Check if there's a view_equipment permission
        cursor.execute("""
            SELECT permission_key FROM permissions 
            WHERE permission_key = 'view_equipment'
        """)
        
        view_equipment_exists = cursor.fetchone()
        print(f"\nview_equipment permission exists: {bool(view_equipment_exists)}")

if __name__ == "__main__":
    check_equipment_permissions()
