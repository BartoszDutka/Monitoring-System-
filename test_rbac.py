#!/usr/bin/env python3
from modules.permissions import has_permission, get_user_permissions
from modules.database import get_db_cursor
from flask import session

# Test the permission system
print('=== RBAC TESTING ===')

# Check if roles and permissions are properly set up
with get_db_cursor() as cursor:
    cursor.execute('SELECT COUNT(*) as count FROM roles')
    roles_count = cursor.fetchone()['count']
    print(f'Roles in database: {roles_count}')
    
    cursor.execute('SELECT COUNT(*) as count FROM permissions')
    perms_count = cursor.fetchone()['count']
    print(f'Permissions in database: {perms_count}')
    
    cursor.execute('SELECT COUNT(*) as count FROM role_permissions')
    role_perms_count = cursor.fetchone()['count']
    print(f'Role-permission mappings: {role_perms_count}')
    
    # Check viewer role permissions specifically
    cursor.execute('''
        SELECT p.permission_key 
        FROM permissions p
        JOIN role_permissions rp ON p.permission_id = rp.permission_id
        JOIN roles r ON rp.role_id = r.role_id
        WHERE r.role_key = %s
        ORDER BY p.permission_key
    ''', ('viewer',))
    
    viewer_perms = [row['permission_key'] for row in cursor.fetchall()]
    print(f'\nViewer permissions ({len(viewer_perms)}):')
    for perm in viewer_perms:
        print(f'  - {perm}')
        
    # Test all roles
    print(f'\n=== ALL ROLES PERMISSIONS ===')
    cursor.execute('SELECT role_key FROM roles ORDER BY role_key')
    all_roles = [row['role_key'] for row in cursor.fetchall()]
    
    for role in all_roles:
        cursor.execute('''
            SELECT p.permission_key 
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = %s
            ORDER BY p.permission_key
        ''', (role,))
        
        role_perms = [row['permission_key'] for row in cursor.fetchall()]
        print(f'\n{role.upper()} permissions ({len(role_perms)}):')
        for perm in role_perms:
            print(f'  - {perm}')
