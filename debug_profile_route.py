#!/usr/bin/env python3
"""
Debug script to check session and profile route
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app
    from flask import session
    import requests
    
    print("Testing profile route access...")
    
    # Test if we can access the profile route directly
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Simulate logged in session
            sess['logged_in'] = True
            sess['username'] = 'bdutka'
            sess['user_info'] = {
                'username': 'bdutka',
                'display_name': 'Bartosz Dutka',
                'role': 'admin'
            }
            
        print("Testing GET /profile with simulated session...")
        response = client.get('/profile')
        print(f"Status Code: {response.status_code}")
        print(f"Location header: {response.headers.get('Location', 'None')}")
        
        if response.status_code == 302:
            print("❌ Profile route is redirecting")
            print(f"Redirecting to: {response.headers.get('Location')}")
        elif response.status_code == 200:
            print("✅ Profile route works correctly")
            print(f"Response contains 'User Profile': {'User Profile' in response.get_data(as_text=True)}")
        else:
            print(f"❓ Unexpected status code: {response.status_code}")
            
        # Check what routes are available
        print("\nAvailable routes:")
        for rule in app.url_map.iter_rules():
            if 'profile' in rule.rule.lower():
                print(f"  {rule.rule} [{', '.join(rule.methods)}] -> {rule.endpoint}")
                
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
