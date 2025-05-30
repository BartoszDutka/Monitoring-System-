#!/usr/bin/env python3

from modules.database import get_db_cursor

print("=== WSZYSTKIE UPRAWNIENIA W SYSTEMIE ===")

with get_db_cursor() as cursor:
    cursor.execute('''
        SELECT permission_key, category, name_en, name_pl, description_en, description_pl
        FROM permissions 
        ORDER BY category, permission_key
    ''')
    permissions = cursor.fetchall()
    
    current_category = None
    for p in permissions:
        if p['category'] != current_category:
            current_category = p['category']
            print(f"\n--- {current_category.upper()} ---")
        
        print(f"Key: {p['permission_key']}")
        print(f"  EN: {p['name_en']} - {p['description_en']}")
        print(f"  PL: {p['name_pl']} - {p['description_pl']}")
        print()
