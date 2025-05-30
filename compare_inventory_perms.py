#!/usr/bin/env python3

from modules.permissions import get_role_permissions

print("=== PORÓWNANIE UPRAWNIEŃ INVENTORY: USER vs MANAGER ===\n")

# Get permissions for both roles
user_perms = get_role_permissions('user')
manager_perms = get_role_permissions('manager')

# Filter inventory/assets related permissions
inventory_categories = ['assets', 'ASSETS']

print("USER - Uprawnienia inventory/assets:")
user_inventory = [p for p in user_perms if p['category'] in inventory_categories]
for p in user_inventory:
    print(f"  - {p['permission_key']} ({p['category']})")

print(f"\nMANAGER - Uprawnienia inventory/assets:")
manager_inventory = [p for p in manager_perms if p['category'] in inventory_categories]
for p in manager_inventory:
    print(f"  - {p['permission_key']} ({p['category']})")

print(f"\nBRAKUJĄCE UPRAWNIENIA w roli USER:")
user_keys = [p['permission_key'] for p in user_inventory]
manager_keys = [p['permission_key'] for p in manager_inventory]

missing = [key for key in manager_keys if key not in user_keys]
for m in missing:
    print(f"  - {m}")

print(f"\nUprawnienia wymagane przez szablon inventory.html:")
required_perms = ['manage_equipment', 'assign_equipment']
for perm in required_perms:
    has_user = perm in user_keys
    has_manager = perm in manager_keys
    print(f"  - {perm}: USER={has_user}, MANAGER={has_manager}")
