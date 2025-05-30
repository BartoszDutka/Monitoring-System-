#!/usr/bin/env python3
"""
Check role permissions structure
"""

from modules.database import get_db_cursor

def check_roles():
    print("=== ROLE PERMISSIONS SUMMARY ===\n")
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT r.role_key, p.permission_key, p.name_en, p.category
            FROM roles r
            JOIN role_permissions rp ON r.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.permission_id
            ORDER BY r.role_key, p.category, p.permission_key
        ''')
        
        current_role = None
        for row in cursor.fetchall():
            if row['role_key'] != current_role:
                print(f'\n{row["role_key"].upper()} ROLE:')
                current_role = row['role_key']
            print(f'  ✓ {row["permission_key"]} - {row["name_en"]} ({row["category"]})')

if __name__ == "__main__":
    check_roles()
