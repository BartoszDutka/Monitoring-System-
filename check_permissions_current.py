#!/usr/bin/env python3
"""
Sprawdzenie obecnego stanu uprawnień - diagnostyka
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from modules.database import get_db_cursor

def check_permissions_implementation():
    """Sprawdza obecny stan implementacji uprawnień"""
    print("=== DIAGNOSTYKA SYSTEMU UPRAWNIEŃ ===\n")
    
    try:
        with app.app_context():
            conn = get_db_cursor()
            cursor = conn.cursor()
            
            # 1. Sprawdź role i ich uprawnienia
            print("1. ROLE I UPRAWNIENIA:")
            cursor.execute("""
                SELECT r.role_key, r.description_en, p.permission_key, p.category, p.name_en
                FROM roles r
                JOIN role_permissions rp ON r.role_id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.permission_id
                WHERE r.role_key IN ('admin', 'manager', 'user', 'viewer')
                ORDER BY r.role_key, p.category, p.permission_key
            """)
            
            mappings = cursor.fetchall()
            current_role = None
            for mapping in mappings:
                role, desc, perm, category, name = mapping
                if role != current_role:
                    print(f"\n{role.upper()} ({desc}):")
                    current_role = role
                print(f"  {category}: {perm} ({name})")
            
            # 2. Sprawdź użytkowników testowych
            print("\n\n2. UŻYTKOWNICY TESTOWI:")
            cursor.execute("""
                SELECT username, role, email 
                FROM users 
                WHERE username IN ('admin', 'viewer', 'user', 'manager')
                ORDER BY username
            """)
            
            users = cursor.fetchall()
            for user in users:
                print(f"  {user['username']}: {user['role']} ({user['email']})")
            
            # 3. Sprawdź uprawnienia dla viewer
            print("\n\n3. UPRAWNIENIA DLA VIEWER:")
            cursor.execute("""
                SELECT p.permission_key, p.category, p.name_en
                FROM permissions p
                JOIN role_permissions rp ON p.permission_id = rp.permission_id
                JOIN roles r ON rp.role_id = r.role_id
                WHERE r.role_key = 'viewer'
                ORDER BY p.category, p.permission_key
            """)
            
            viewer_perms = cursor.fetchall()
            current_cat = None
            for perm in viewer_perms:
                key, cat, name = perm
                if cat != current_cat:
                    print(f"\n  {cat.upper()}:")
                    current_cat = cat
                print(f"    {key} - {name}")
            
            conn.close()
            print("\n✅ Diagnostyka zakończona pomyślnie!")
            return True
            
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

if __name__ == "__main__":
    check_permissions_implementation()
