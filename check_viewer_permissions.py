#!/usr/bin/env python3
from modules.database import get_db_connection
import sqlite3

def check_viewer_permissions():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sprawdź uprawnienia VIEWER
        cursor.execute('''
            SELECT p.name as permission_name, p.description 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN roles r ON rp.role_id = r.id
            WHERE r.name = 'VIEWER'
            ORDER BY p.name
        ''')
        
        print('=== UPRAWNIENIA VIEWER ===')
        viewer_perms = cursor.fetchall()
        for perm in viewer_perms:
            print(f'- {perm[0]}: {perm[1]}')
        
        print(f'\nViewer ma {len(viewer_perms)} uprawnień')
        
        # Sprawdź czy viewer ma dostęp do logów
        logs_access = any('view_monitoring' in perm[0] or 'logs' in perm[0].lower() or 'graylog' in perm[0].lower() for perm in viewer_perms)
        print(f'\nCzy viewer ma dostęp do logów: {"TAK" if logs_access else "NIE"}')
        
        conn.close()
        return viewer_perms
        
    except Exception as e:
        print(f'Błąd: {e}')
        return []

if __name__ == "__main__":
    check_viewer_permissions()
