#!/usr/bin/env python3
"""
Script to simulate a viewer login and verify permissions
"""

from modules.database import get_db_cursor
from modules.permissions import get_user_permissions, has_permission
from flask import Flask, session
import json

app = Flask(__name__)
app.secret_key = 'test_secret_key'  # Just for the test session

def simulate_viewer_login():
    print("🔑 Simulating viewer login and checking permissions...")
    
    with app.test_request_context():
        # Get a viewer username
        with get_db_cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE role = 'viewer' LIMIT 1")
            viewer = cursor.fetchone()
            if not viewer:
                print("❌ No viewer user found in database")
                return
                
            username = viewer['username']
            print(f"👤 Using viewer: {username}")
            
            # Set up a mock login session
            session['logged_in'] = True
            session['username'] = username
            session['user_info'] = {'role': 'viewer'}
            
            # Clear permissions cache
            if 'permissions' in session:
                del session['permissions']
            
            # Get permissions directly from database
            permissions = get_user_permissions(username, debug=True)
            permission_keys = [p['permission_key'] for p in permissions]
            
            print(f"\n👮 Viewer has {len(permissions)} permissions:")
            for p in permissions:
                print(f"  ✓ {p['permission_key']} - {p['name_en']} ({p['category']})")
            
            # Check view_assets permission
            has_view_assets = has_permission('view_assets', debug=True)
            print(f"\n🔍 has_permission('view_assets') = {has_view_assets}")
            
            # Check if view_assets is in session permissions
            session_perms = session.get('permissions', [])
            in_session = 'view_assets' in session_perms
            print(f"📝 'view_assets' in session permissions: {in_session}")
            if in_session:
                print(f"📋 Session permissions: {session_perms}")
            else:
                print(f"❌ Session permissions missing 'view_assets': {session_perms}")

if __name__ == "__main__":
    simulate_viewer_login()
