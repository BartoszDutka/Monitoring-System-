#!/usr/bin/env python3
"""
Debug script to check database schema and user data
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.database import get_db_cursor
    
    print("Checking database schema and user data...")
    
    with get_db_cursor() as cursor:
        # Check if users table exists and its structure
        cursor.execute("DESCRIBE users")
        users_columns = cursor.fetchall()
        print("\nUsers table structure:")
        for col in users_columns:
            print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']} - {col['Default']}")
        
        # Check if roles table exists
        try:
            cursor.execute("DESCRIBE roles")
            roles_columns = cursor.fetchall()
            print("\nRoles table structure:")
            for col in roles_columns:
                print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']} - {col['Default']}")
        except Exception as e:
            print(f"\nRoles table error: {e}")
        
        # Check if departments table exists
        try:
            cursor.execute("DESCRIBE departments")
            dept_columns = cursor.fetchall()
            print("\nDepartments table structure:")
            for col in dept_columns:
                print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']} - {col['Default']}")
        except Exception as e:
            print(f"\nDepartments table error: {e}")
        
        # Check current user data
        cursor.execute("SELECT * FROM users WHERE username = 'bdutka'")
        user_data = cursor.fetchone()
        if user_data:
            print(f"\nUser 'bdutka' data:")
            for key, value in user_data.items():
                print(f"  {key}: {value}")
        else:
            print("\nUser 'bdutka' not found")
            
        # Test the exact query from profile function
        try:
            cursor.execute("""
                SELECT u.*, r.role_key, r.description_en as role_description
                FROM users u
                LEFT JOIN roles r ON u.role_id = r.role_id
                WHERE u.username = %s
            """, ('bdutka',))
            result = cursor.fetchone()
            if result:
                print(f"\nProfile query result for 'bdutka':")
                for key, value in result.items():
                    print(f"  {key}: {value}")
            else:
                print("\nProfile query returned no results")
        except Exception as e:
            print(f"\nProfile query error: {e}")
            
except Exception as e:
    print(f"Database connection error: {e}")
    import traceback
    traceback.print_exc()
