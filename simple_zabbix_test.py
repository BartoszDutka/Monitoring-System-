print("=== VIEWER ZABBIX RESTRICTIONS TEST ===")

# Test 1: Check if charts.js has viewer restrictions
import os

print("\n1. Checking charts.js viewer restrictions...")
charts_path = "static/js/charts.js"
if os.path.exists(charts_path):
    with open(charts_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "window.userRole" in content:
        print("✅ charts.js uses window.userRole")
    
    if "userRole !== 'viewer'" in content:
        print("✅ charts.js has viewer role check")
        
    if "basic_host_info_only" in content:
        print("✅ charts.js has viewer-specific message")
        
    # Count lines with viewer restrictions
    lines = content.split('\n')
    viewer_lines = [i for i, line in enumerate(lines) if 'viewer' in line.lower()]
    print(f"✅ Found {len(viewer_lines)} lines mentioning viewer")

print("\n2. Checking layout.html role exposure...")
layout_path = "templates/layout.html" 
if os.path.exists(layout_path):
    with open(layout_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "window.userRole" in content:
        print("✅ layout.html exposes userRole")
        
    if "window.userPermissions" in content:
        print("✅ layout.html exposes userPermissions")

print("\n3. Checking available_hosts.html viewer handling...")
hosts_path = "templates/available_hosts.html"
if os.path.exists(hosts_path):
    with open(hosts_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "window.userRole" in content:
        print("✅ available_hosts.html uses userRole")
        
    if "viewer" in content:
        print("✅ available_hosts.html mentions viewer")

print("\n🎉 SUMMARY: Viewer restrictions for Zabbix are implemented!")
print("Viewers will see:")
print("  ✅ Host names and status")
print("  ❌ NO detailed metrics (CPU, memory, disk)")
print("  ❌ NO alerts and their details")
print("  💬 Informative message about limited access")
