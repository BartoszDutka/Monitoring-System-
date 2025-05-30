#!/usr/bin/env python3
import sys
import traceback

try:
    from modules.database import get_db_cursor
    print("Existing permissions:")
    print("-" * 50)
except Exception as e:
    print(f"Error importing modules: {e}")
    traceback.print_exc()
    sys.exit(1)

with get_db_cursor() as cursor:
    cursor.execute('SELECT permission_key, category, name_en FROM permissions ORDER BY category, permission_key')
    perms = cursor.fetchall()
    
    current_category = ""
    for p in perms:
        if p['category'] != current_category:
            current_category = p['category']
            print(f"\n{current_category.upper()}:")
        print(f"  {p['permission_key']} - {p['name_en']}")

print("\n" + "=" * 50)
print("Current role permissions:")

with get_db_cursor() as cursor:
    cursor.execute('''
        SELECT r.role_key, p.permission_key, p.name_en
        FROM roles r
        JOIN role_permissions rp ON r.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.permission_id
        ORDER BY r.role_key, p.category, p.permission_key
    ''')
    role_perms = cursor.fetchall()
    
    current_role = ""
    for rp in role_perms:
        if rp['role_key'] != current_role:
            current_role = rp['role_key']
            print(f"\n{current_role.upper()}:")
        print(f"  {rp['permission_key']} - {rp['name_en']}")
