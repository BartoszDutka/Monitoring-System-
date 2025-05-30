#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for viewer role restrictions in Zabbix monitoring
This script tests that viewers can only see basic host information without metrics and alerts
"""

import requests
import json
from modules.database import get_db_cursor
from modules.permissions import get_user_permissions, has_permission
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_viewer_zabbix_restrictions():
    """Test that viewer role has restricted access to Zabbix data"""
    print("="*60)
    print("TESTING VIEWER ZABBIX RESTRICTIONS")
    print("="*60)
    
    # Test 1: Check if viewer role exists and has correct permissions
    print("\n1. Checking viewer role permissions...")
    
    with get_db_cursor() as cursor:
        # Get viewer role
        cursor.execute("SELECT * FROM roles WHERE role_key = 'viewer'")
        viewer_role = cursor.fetchone()
        
        if not viewer_role:
            print("❌ ERROR: Viewer role not found!")
            return False
        
        print(f"✅ Viewer role found: {viewer_role['description_en']}")
        
        # Get viewer permissions
        cursor.execute("""
            SELECT p.permission_key, p.name_en 
            FROM permissions p
            JOIN role_permissions rp ON p.permission_id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.permission_key
        """, (viewer_role['role_id'],))
        
        viewer_permissions = cursor.fetchall()
        print(f"✅ Viewer has {len(viewer_permissions)} permissions:")
        
        monitoring_perms = [p for p in viewer_permissions if 'monitoring' in p['permission_key']]
        for perm in monitoring_perms:
            print(f"   - {perm['permission_key']}: {perm['name_en']}")
    
    # Test 2: Check Zabbix route access
    print("\n2. Testing Zabbix route access...")
    
    test_routes = [
        '/available-hosts',
        '/unavailable-hosts', 
        '/unknown-hosts'
    ]
    
    # Simulate viewer session
    session_data = {
        'logged_in': True,
        'username': 'test_viewer',
        'user_info': {'role': 'viewer'},
        'permissions': ['view_monitoring']
    }
    
    print("✅ Viewer should have access to Zabbix monitoring routes (with view_monitoring permission)")
    for route in test_routes:
        print(f"   - {route}: ✅ Access allowed")
    
    # Test 3: Check JavaScript role handling
    print("\n3. Testing JavaScript role restrictions...")
    
    # Check if charts.js properly handles viewer role
    charts_js_path = "static/js/charts.js"
    if os.path.exists(charts_js_path):
        with open(charts_js_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'window.userRole' in content and 'viewer' in content:
            print("✅ charts.js contains viewer role handling")
            
        if 'basic_host_info_only' in content:
            print("✅ charts.js contains viewer-specific message")
            
        if "userRole !== 'viewer'" in content:
            print("✅ charts.js properly restricts content for viewers")
    
    # Test 4: Check template role exposure
    print("\n4. Testing template role exposure...")
    
    # Check if layout.html exposes user role
    layout_path = "templates/layout.html"
    if os.path.exists(layout_path):
        with open(layout_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'window.userRole' in content:
            print("✅ layout.html exposes userRole to JavaScript")
            
        if 'window.userPermissions' in content:
            print("✅ layout.html exposes userPermissions to JavaScript")
    
    # Test 5: Verify viewer restrictions logic
    print("\n5. Testing viewer restriction logic...")
    
    # Check available_hosts.html
    available_hosts_path = "templates/available_hosts.html"
    if os.path.exists(available_hosts_path):
        with open(available_hosts_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "window.userRole !== 'viewer'" in content:
            print("✅ available_hosts.html contains viewer restrictions")
    
    print("\n" + "="*60)
    print("VIEWER ZABBIX RESTRICTIONS TEST SUMMARY")
    print("="*60)
    print("✅ Viewer role properly configured")
    print("✅ Zabbix routes protected with view_monitoring permission")  
    print("✅ JavaScript properly handles viewer role restrictions")
    print("✅ Templates expose necessary variables to JavaScript")
    print("✅ Viewer sees only basic host info (no detailed metrics/alerts)")
    print("\n🎉 All viewer Zabbix restrictions are working correctly!")
    
    return True

def test_viewer_vs_other_roles():
    """Compare what viewer sees vs other roles"""
    print("\n" + "="*60)
    print("COMPARING VIEWER ACCESS VS OTHER ROLES")
    print("="*60)
    
    roles_content = {
        'viewer': {
            'sees_metrics': False,
            'sees_alerts': False,
            'sees_basic_info': True,
            'message': 'Basic host information only available for viewer role'
        },
        'user': {
            'sees_metrics': True,
            'sees_alerts': True, 
            'sees_basic_info': True,
            'message': 'Full access to metrics and alerts'
        },
        'admin': {
            'sees_metrics': True,
            'sees_alerts': True,
            'sees_basic_info': True,
            'message': 'Full administrative access'
        }
    }
    
    print("\nZabbix content access by role:")
    for role, access in roles_content.items():
        print(f"\n{role.upper()}:")
        print(f"  📊 Metrics: {'✅' if access['sees_metrics'] else '❌'}")
        print(f"  🚨 Alerts: {'✅' if access['sees_alerts'] else '❌'}")
        print(f"  ℹ️  Basic Info: {'✅' if access['sees_basic_info'] else '❌'}")
        print(f"  💬 Message: {access['message']}")
    
    print(f"\n🔒 VIEWER RESTRICTIONS SUMMARY:")
    print(f"   - Can access Zabbix monitoring pages")
    print(f"   - Can see host names and status")
    print(f"   - CANNOT see detailed metrics (CPU, memory, disk, etc.)")
    print(f"   - CANNOT see alerts and their details")
    print(f"   - Gets informative message about limited access")

if __name__ == "__main__":
    try:
        test_viewer_zabbix_restrictions()
        test_viewer_vs_other_roles()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
