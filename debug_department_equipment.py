#!/usr/bin/env python3
"""
Script to debug the department equipment endpoint from viewer perspective
"""

from modules.database import get_db_cursor
import json

def debug_department_equipment():
    """Simulate what happens when a viewer calls the API endpoint"""
    print("🔍 Debugging department equipment API for viewer role...")
    print("DEBUG START ==============================")
    
    # 1. Get a test department with equipment
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT d.name 
            FROM departments d
            JOIN equipment e ON e.assigned_to_department = d.name
            GROUP BY d.name
            HAVING COUNT(e.id) > 0
            LIMIT 1
        """)
        
        dept = cursor.fetchone()
        if not dept:
            print("❌ No department with equipment found for testing")
            return
            
        department = dept['name']
        print(f"📁 Testing with department: {department}")
        
        # 2. Check what the API would return
        cursor.execute("""
            SELECT name, description_en as description, location
            FROM departments
            WHERE name = %s
        """, (department,))
        dept_info = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                e.id,
                e.name,
                e.type,
                e.serial_number,
                e.status,
                e.quantity,
                e.assigned_date,
                e.notes
            FROM equipment e
            WHERE e.assigned_to_department = %s
            ORDER BY e.type, e.name
        """, (department,))
        equipment = cursor.fetchall()
        
        print(f"📊 Department info: {dept_info}")
        print(f"📊 Equipment count: {len(equipment)}")
        
        # Print first item for debugging
        if equipment:
            print(f"📦 First equipment item:")
            print(json.dumps(dict(equipment[0]), default=str, indent=2))
        
        # 3. Check if the viewer role has the needed permission
        cursor.execute("""
            SELECT 1
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'viewer' AND p.permission_key = 'view_assets'
        """)
        
        has_permission = cursor.fetchone() is not None
        print(f"\n✅ Viewer has view_assets permission: {has_permission}")
        
        # 4. Check if any permission filtering logic exists
        print("\n🛡️ Checking for permission filtering in code:")
        print("   * API endpoint requires @permission_required('view_assets')")
        print("   * No other filtering logic at database level")
        
        # 5. Check if frontend is restricting display
        print("\n🖥️ Frontend can display equipment if:")
        print("   * Department data is returned from API endpoint") 
        print("   * Equipment array is not empty")
        print("   * No JavaScript permission filtering exists")
        
        # 6. Make sure view_assets doesn't have typos
        cursor.execute("""
            SELECT permission_id, permission_key, name_en, category
            FROM permissions
            WHERE permission_key LIKE '%view%' AND permission_key LIKE '%asset%'
        """)
        
        asset_perms = cursor.fetchall()
        print("\n🔤 Asset viewing permissions in database:")
        for perm in asset_perms:
            print(f"   * {perm['permission_key']} - {perm['name_en']} ({perm['category']})")

if __name__ == "__main__":
    print("SCRIPT STARTING")
    debug_department_equipment()
    print("DEBUG END ===============================")
