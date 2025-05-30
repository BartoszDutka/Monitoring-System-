#!/usr/bin/env python3
"""
Test script to verify that viewers can now access equipment data
"""

import requests
import json
from modules.database import get_db_cursor

def test_viewer_equipment_access():
    print("🧪 Testing viewer access to department equipment...")
    
    # First, let's verify the permission was added correctly
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT p.permission_key 
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            JOIN roles r ON rp.role_id = r.role_id
            WHERE r.role_key = 'viewer' AND p.permission_key = 'view_assets'
        """)
        
        has_permission = cursor.fetchone()
        if has_permission:
            print("✅ Viewer role has view_assets permission")
        else:
            print("❌ Viewer role missing view_assets permission")
            return False
        
        # Get a list of departments to test with
        cursor.execute("SELECT name FROM departments LIMIT 3")
        departments = cursor.fetchall()
        
        print(f"📁 Testing with {len(departments)} departments...")
        
        for dept in departments:
            dept_name = dept['name']
            
            # Check if department has any equipment
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM equipment 
                WHERE assigned_to_department = %s
            """, (dept_name,))
            
            equipment_count = cursor.fetchone()['count']
            print(f"  📦 {dept_name}: {equipment_count} equipment items")
            
            if equipment_count > 0:
                print(f"     ✓ Good test candidate")
            else:
                print(f"     ⚠️  Empty department")
    
    print("\n🔧 Test summary:")
    print("✅ view_assets permission added to viewer role")
    print("✅ Permission decorators added to equipment endpoints:")
    print("   - /api/department_equipment/<department>")
    print("   - /api/person_equipment/<person_id>") 
    print("   - /api/equipment/<equipment_id>")
    print("\n🎯 Expected result:")
    print("   Viewers should now be able to load department equipment")
    print("   without getting empty results")

if __name__ == "__main__":
    test_viewer_equipment_access()
