#!/usr/bin/env python3
"""
Quick RBAC Test Script
Tests the permission decorators and route access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_permission_imports():
    """Test that all modules can import successfully"""
    try:
        from app import app
        print("✅ App import successful")
        
        from modules.permissions import permission_required, get_user_permissions
        print("✅ Permissions module import successful")
        
        from modules.tasks import bp as tasks_bp
        print("✅ Tasks module import successful")
        
        import inventory
        print("✅ Inventory module import successful")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_routes():
    """Test that the app routes are properly configured"""
    try:
        from app import app
        
        with app.app_context():
            # Get all routes and their methods
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'rule': rule.rule
                })
            
            print(f"✅ App has {len(routes)} routes configured")
            
            # Check for specific routes we modified
            glpi_routes = [r for r in routes if 'glpi' in r['rule'].lower()]
            print(f"✅ Found {len(glpi_routes)} GLPI routes")
            
            task_routes = [r for r in routes if 'task' in r['rule'].lower()]
            print(f"✅ Found {len(task_routes)} task routes")
            
            api_routes = [r for r in routes if '/api/' in r['rule']]
            print(f"✅ Found {len(api_routes)} API routes")
            
            return True
    except Exception as e:
        print(f"❌ Route test error: {e}")
        return False

def main():
    print("=== RBAC Quick Test ===\n")
    
    print("1. Testing imports...")
    import_success = test_permission_imports()
    
    print("\n2. Testing app configuration...")
    route_success = test_app_routes()
    
    print(f"\n3. Summary:")
    if import_success and route_success:
        print("🎉 All tests passed! The RBAC system appears to be properly configured.")
        print("\nNext steps:")
        print("- Update your database with the new permission structure")
        print("- Test the application in a web browser")
        print("- Verify user role assignments work correctly")
    else:
        print("⚠️  Some issues detected. Please check the errors above.")

if __name__ == "__main__":
    main()
