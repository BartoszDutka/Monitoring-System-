#!/usr/bin/env python3
"""
Test script to check profile route functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, get_db_cursor
    from flask import url_for
    
    print("Testing profile route...")
    
    with app.app_context():
        # Check if profile route exists
        try:
            profile_url = url_for('profile')
            print(f"✓ Profile route URL: {profile_url}")
        except Exception as e:
            print(f"✗ Error generating profile URL: {e}")
            
        # List all routes
        print("\nAll routes:")
        for rule in app.url_map.iter_rules():
            if 'profile' in rule.rule:
                print(f"  {rule.rule} -> {rule.endpoint}")
                
        # Test database connection
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT 1")
                print("✓ Database connection works")
        except Exception as e:
            print(f"✗ Database connection error: {e}")
            
        print("\nProfile route should be working. If it's redirecting to dashboard,")
        print("check if the user is properly logged in and has a valid session.")
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed.")
except Exception as e:
    print(f"Error: {e}")
