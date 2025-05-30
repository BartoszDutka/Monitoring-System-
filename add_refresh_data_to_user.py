#!/usr/bin/env python3

from modules.database import get_db_cursor

def add_refresh_data_to_user():
    """
    Add refresh_data permission to user role for logs access
    """
    try:
        with get_db_cursor() as cursor:
            # Get role_id for user
            cursor.execute("SELECT role_id FROM roles WHERE role_key = 'user'")
            user_role = cursor.fetchone()
            
            if not user_role:
                print("ERROR: User role not found!")
                return False
                
            user_role_id = user_role['role_id']
            print(f"Found user role with ID: {user_role_id}")
            
            # Get permission_id for refresh_data
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = 'refresh_data'")
            permission = cursor.fetchone()
            
            if not permission:
                print("ERROR: refresh_data permission not found!")
                return False
                
            permission_id = permission['permission_id']
            print(f"Found refresh_data permission with ID: {permission_id}")
            
            # Check if assignment already exists
            cursor.execute("""
                SELECT 1 FROM role_permissions 
                WHERE role_id = %s AND permission_id = %s
            """, (user_role_id, permission_id))
            
            if cursor.fetchone():
                print("refresh_data permission already assigned to user role!")
                return True
            
            # Add permission to user role
            cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_id) 
                VALUES (%s, %s)
            """, (user_role_id, permission_id))
            
            print("✅ Successfully added refresh_data permission to user role!")
            print("📝 User role now has access to Graylog logs menu")
            return True
            
    except Exception as e:
        print(f"❌ Error adding refresh_data permission: {e}")
        return False

if __name__ == "__main__":
    print("=== ADDING REFRESH_DATA PERMISSION TO USER ROLE ===")
    success = add_refresh_data_to_user()
    
    if success:
        print("\n🎉 Process completed successfully!")
        print("📋 User role now has:")
        print("   - Graylog logs menu access")
        print("   - All inventory management features") 
        print("   - Monitoring and task management")
    else:
        print("\n❌ Process failed!")
