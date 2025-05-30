import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

print("Routes containing 'profile':")
for rule in app.url_map.iter_rules():
    if 'profile' in rule.rule.lower():
        print(f"  {rule.rule} -> {rule.endpoint}")

print("\nChecking profile function...")
try:
    profile_func = app.view_functions.get('profile')
    if profile_func:
        print("✅ Profile function exists")
        print(f"Function: {profile_func}")
    else:
        print("❌ Profile function not found")
except Exception as e:
    print(f"Error: {e}")
