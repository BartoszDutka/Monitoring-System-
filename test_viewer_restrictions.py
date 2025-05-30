#!/usr/bin/env python3
"""
Test script to verify viewer role restrictions are working correctly
"""

from modules.database import get_db_cursor
from modules.permissions import has_permission, get_user_permissions
from flask import session
import sys

def test_user_permissions(username):
    """Test permissions for a specific user"""
    print(f"\n=== Testing permissions for user: {username} ===")
    
    # Get user role
    with get_db_cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if not user:
            print(f"User '{username}' not found!")
            return
            
        role = user['role']
        print(f"User role: {role}")
    
    # Get user permissions
    permissions = get_user_permissions(username)
    permission_keys = [p['permission_key'] for p in permissions]
    
    print(f"Total permissions: {len(permissions)}")
    print("Permissions:", ", ".join(permission_keys))
    
    # Test specific restricted permissions
    restricted_permissions = [
        'vnc_connect',
        'refresh_data', 
        'manage_equipment',
        'assign_equipment'
    ]
    
    print("\n--- Restricted Permission Tests ---")
    for perm in restricted_permissions:
        has_perm = perm in permission_keys
        status = "✓ ALLOWED" if has_perm else "✗ BLOCKED"
        print(f"{perm}: {status}")
    
    # Test viewing permissions (should be allowed for all roles)
    viewing_permissions = [
        'view_monitoring',
        'tasks_view',
        'manage_profile'
    ]
    
    print("\n--- Viewing Permission Tests ---")
    for perm in viewing_permissions:
        has_perm = perm in permission_keys
        status = "✓ ALLOWED" if has_perm else "✗ BLOCKED"
        print(f"{perm}: {status}")

def test_all_roles():
    """Test permissions for all role types"""
    roles_to_test = ['admin', 'manager', 'user', 'viewer']
    
    with get_db_cursor() as cursor:
        for role in roles_to_test:
            # Find a user with this role
            cursor.execute("SELECT username FROM users WHERE role = %s LIMIT 1", (role,))
            user = cursor.fetchone()
            
            if user:
                test_user_permissions(user['username'])
            else:
                print(f"\n=== No user found with role: {role} ===")

def create_test_viewer():
    """Create a test viewer user if one doesn't exist"""
    with get_db_cursor() as cursor:
        # Check if viewer user exists
        cursor.execute("SELECT username FROM users WHERE role = 'viewer' LIMIT 1")
        if cursor.fetchone():
            print("Viewer user already exists")
            return
            
        # Create test viewer
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, Department)
            VALUES ('test_viewer', 'dummy_hash', 'viewer', 'viewer@test.com', 'Test')
        """)
        print("Created test viewer user: test_viewer")

def main():
    try:
        print("Testing Viewer Role Restrictions")
        print("=" * 50)
        
        # Ensure we have a test viewer
        create_test_viewer()
        
        # Test all roles
        test_all_roles()
        
        print("\n" + "=" * 50)
        print("Expected Results:")
        print("- VIEWER: Should only have view_monitoring, tasks_view, manage_profile")
        print("- USER: Should have viewer permissions + vnc_connect + view permissions") 
        print("- MANAGER: Should have user permissions + refresh_data + equipment management")
        print("- ADMIN: Should have all permissions")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
