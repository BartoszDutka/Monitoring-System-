#!/usr/bin/env python3
"""
Test script to verify frontend UI restrictions for the viewer role.
This script checks that viewer restrictions are properly implemented in templates.
"""

import requests
import re
from bs4 import BeautifulSoup
import sys

# Test configuration
BASE_URL = "http://localhost:5000"
VIEWER_CREDENTIALS = {"username": "viewer", "password": "viewer123"}

def login_as_viewer():
    """Login as viewer user and return session"""
    session = requests.Session()
    
    # Get login page first to get any CSRF tokens if needed
    login_page = session.get(f"{BASE_URL}/login")
    if login_page.status_code != 200:
        print(f"❌ Failed to access login page: {login_page.status_code}")
        return None
    
    # Attempt login
    login_response = session.post(f"{BASE_URL}/login", data=VIEWER_CREDENTIALS)
    
    # Check if login was successful (usually redirects to dashboard)
    if login_response.status_code == 200 and "login" in login_response.url:
        print("❌ Login failed - still on login page")
        return None
    elif login_response.status_code in [200, 302]:
        print("✅ Login successful")
        return session
    else:
        print(f"❌ Login failed with status: {login_response.status_code}")
        return None

def test_vnc_buttons_hidden(session):
    """Test that VNC buttons are hidden for viewers"""
    print("\n🧪 Testing VNC button restrictions...")
    
    response = session.get(f"{BASE_URL}/available-hosts")
    if response.status_code != 200:
        print(f"❌ Failed to access available hosts page: {response.status_code}")
        return False
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Look for VNC button elements in the HTML
    vnc_buttons = soup.find_all(['a', 'button'], class_=re.compile(r'vnc'))
    
    # Also check for VNC-related text
    vnc_text = re.findall(r'vnc|connect.*desktop|remote.*access', response.text, re.IGNORECASE)
    
    if not vnc_buttons and not vnc_text:
        print("✅ VNC buttons properly hidden for viewer")
        return True
    else:
        print(f"❌ VNC buttons found: {len(vnc_buttons)} buttons, {len(vnc_text)} text references")
        return False

def test_refresh_buttons_hidden(session):
    """Test that refresh buttons are hidden for viewers"""
    print("\n🧪 Testing refresh button restrictions...")
    
    test_pages = [
        ("/graylog/logs", "Graylog logs"),
        ("/graylog/messages_over_time", "Messages over time"),
        ("/glpi/category/workstations", "GLPI workstations"),
    ]
    
    all_passed = True
    
    for url, page_name in test_pages:
        response = session.get(f"{BASE_URL}{url}")
        if response.status_code != 200:
            print(f"⚠️  Could not access {page_name} page: {response.status_code}")
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for refresh buttons
        refresh_buttons = soup.find_all(['button'], class_=re.compile(r'refresh'))
        refresh_buttons += soup.find_all(['button'], id=re.compile(r'refresh'))
        
        if not refresh_buttons:
            print(f"✅ Refresh buttons properly hidden on {page_name}")
        else:
            print(f"❌ Found {len(refresh_buttons)} refresh buttons on {page_name}")
            all_passed = False
    
    return all_passed

def test_inventory_restrictions(session):
    """Test that inventory management features are restricted for viewers"""
    print("\n🧪 Testing inventory management restrictions...")
    
    response = session.get(f"{BASE_URL}/inventory")
    if response.status_code != 200:
        print(f"❌ Failed to access inventory page: {response.status_code}")
        return False
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check for manual input and invoice import buttons (should be hidden)
    manual_button = soup.find('button', {'data-method': 'manual'})
    invoice_button = soup.find('button', {'data-method': 'invoice'})
    
    # Check for equipment button (should be visible)
    equipment_button = soup.find('button', {'data-method': 'equipment'})
    
    # Check for Actions column header (should be hidden)
    actions_header = soup.find('th', string=re.compile(r'Actions|Akcje'))
    
    issues = []
    
    if manual_button:
        issues.append("Manual input button visible")
    if invoice_button:
        issues.append("Invoice import button visible")
    if not equipment_button:
        issues.append("Equipment button not found")
    if actions_header:
        issues.append("Actions column visible")
    
    if not issues:
        print("✅ Inventory restrictions properly implemented")
        return True
    else:
        print(f"❌ Inventory issues found: {', '.join(issues)}")
        return False

def test_permission_context_available(session):
    """Test that has_permission function is available in templates"""
    print("\n🧪 Testing permission context availability...")
    
    # Try to access a page and look for permission-related template code
    response = session.get(f"{BASE_URL}/")
    if response.status_code != 200:
        print(f"❌ Failed to access dashboard: {response.status_code}")
        return False
    
    # Check if userPermissions JavaScript variable is defined
    js_permissions = re.search(r'window\.userPermissions\s*=\s*\[([^\]]*)\]', response.text)
    
    if js_permissions:
        permissions_list = js_permissions.group(1)
        print(f"✅ User permissions found in JavaScript: {permissions_list}")
        return True
    else:
        print("❌ User permissions not found in JavaScript context")
        return False

def main():
    """Run all frontend restriction tests"""
    print("🔬 Starting Frontend Restriction Tests for Viewer Role")
    print("=" * 60)
    
    # Login as viewer
    session = login_as_viewer()
    if not session:
        print("❌ Cannot proceed without valid viewer session")
        sys.exit(1)
    
    # Run all tests
    tests = [
        test_permission_context_available,
        test_vnc_buttons_hidden,
        test_refresh_buttons_hidden,
        test_inventory_restrictions,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test(session):
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Frontend Restriction Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All frontend restrictions are working correctly!")
        return 0
    else:
        print("⚠️  Some frontend restrictions need attention.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
