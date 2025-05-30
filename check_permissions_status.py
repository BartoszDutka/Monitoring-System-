#!/usr/bin/env python3
"""
Check current permissions for different roles to understand the current state
"""

from modules.database import get_db_cursor

def check_permissions_status():
    print("=== CHECKING CURRENT PERMISSION STATUS ===\n")
    
    with get_db_cursor() as cursor:
        # Check all inventory/equipment related permissions
        print("1. INVENTORY/EQUIPMENT RELATED PERMISSIONS:")
        print("-" * 50)
        cursor.execute('''
            SELECT permission_key, name_en, category, description_en
            FROM permissions 
            WHERE permission_key LIKE '%inventory%' 
               OR permission_key LIKE '%equipment%' 
               OR permission_key LIKE '%assets%'
               OR category = 'ASSETS'
            ORDER BY category, permission_key
        ''')
        
        inventory_perms = cursor.fetchall()
        for perm in inventory_perms:
            print(f"{perm['permission_key']} - {perm['name_en']} ({perm['category']})")
            if perm['description_en']:
                print(f"  └─ {perm['description_en']}")
        
        print(f"\nTotal inventory-related permissions: {len(inventory_perms)}\n")
        
        # Check permissions for each role
        roles = ['viewer', 'user', 'manager', 'admin']
        
        for role in roles:
            print(f"2. {role.upper()} ROLE PERMISSIONS:")
            print("-" * 50)
            cursor.execute('''
                SELECT p.permission_key, p.name_en, p.category
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = %s
                ORDER BY p.category, p.permission_key
            ''', (role,))
            
            role_perms = cursor.fetchall()
            current_category = None
            for perm in role_perms:
                if perm['category'] != current_category:
                    current_category = perm['category']
                    print(f"\n{current_category}:")
                print(f"  {perm['permission_key']} - {perm['name_en']}")
            
            print(f"\nTotal permissions for {role}: {len(role_perms)}\n")
            print("=" * 60)

if __name__ == "__main__":
    check_permissions_status()
