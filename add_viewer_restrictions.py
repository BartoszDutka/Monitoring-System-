#!/usr/bin/env python3
"""
Script to add new permissions for operations that should be restricted from viewers
"""

from modules.database import get_db_cursor

def add_permission(cursor, permission_key, category, name_en, name_pl, desc_en, desc_pl):
    """Add a new permission to the database"""
    cursor.execute('''
        INSERT IGNORE INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (permission_key, category, name_en, name_pl, desc_en, desc_pl))

def assign_permission_to_roles(cursor, permission_key, role_keys):
    """Assign permission to specific roles"""
    # Get permission ID
    cursor.execute('SELECT permission_id FROM permissions WHERE permission_key = %s', (permission_key,))
    perm = cursor.fetchone()
    if not perm:
        print(f"Permission {permission_key} not found!")
        return
        
    permission_id = perm['permission_id']
    
    for role_key in role_keys:
        # Get role ID
        cursor.execute('SELECT role_id FROM roles WHERE role_key = %s', (role_key,))
        role = cursor.fetchone()
        if not role:
            print(f"Role {role_key} not found!")
            continue
            
        role_id = role['role_id']
        
        # Assign permission to role
        cursor.execute('''
            INSERT IGNORE INTO role_permissions (role_id, permission_id)
            VALUES (%s, %s)
        ''', (role_id, permission_id))
        print(f"Assigned {permission_key} to {role_key}")

def main():
    try:
        with get_db_cursor() as cursor:
            print("Adding new permissions for viewer restrictions...")
            
            # VNC Connection permission
            add_permission(cursor, 'vnc_connect', 'SYSTEM', 
                          'VNC Connection', 'Połączenie VNC',
                          'Allow VNC connections to remote systems', 'Pozwala na połączenia VNC do zdalnych systemów')
            print("Added vnc_connect permission")
            
            # Data refresh permissions
            add_permission(cursor, 'refresh_data', 'SYSTEM',
                          'Refresh Data', 'Odświeżanie Danych', 
                          'Refresh data from external APIs', 'Odświeżanie danych z zewnętrznych API')
            print("Added refresh_data permission")
            
            # Equipment management permissions (these might already exist)
            add_permission(cursor, 'manage_equipment', 'ASSETS',
                          'Manage Equipment', 'Zarządzanie Sprzętem',
                          'Add, edit, delete equipment', 'Dodawanie, edycja, usuwanie sprzętu')
            print("Added manage_equipment permission")
            
            add_permission(cursor, 'assign_equipment', 'ASSETS', 
                          'Assign Equipment', 'Przypisywanie Sprzętu',
                          'Assign equipment to departments/users', 'Przypisywanie sprzętu do działów/użytkowników')
            print("Added assign_equipment permission")
            
            print("\nAssigning permissions to roles...")
            
            # Assign VNC connection to admin, manager, user (not viewer)
            assign_permission_to_roles(cursor, 'vnc_connect', ['admin', 'manager', 'user'])
            
            # Assign data refresh to admin and manager only (not user or viewer)
            assign_permission_to_roles(cursor, 'refresh_data', ['admin', 'manager'])
            
            # Assign equipment management to admin and manager
            assign_permission_to_roles(cursor, 'manage_equipment', ['admin', 'manager'])
            assign_permission_to_roles(cursor, 'assign_equipment', ['admin', 'manager'])
            
            print("\nPermissions added successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
