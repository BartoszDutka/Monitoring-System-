#!/usr/bin/env python3

from modules.permissions import debug_role_permissions

print("=== SPRAWDZENIE UPRAWNIEŃ ROLI USER ===")
debug_role_permissions('user')

print("\n" + "="*50 + "\n")

print("=== SPRAWDZENIE UPRAWNIEŃ ROLI MANAGER ===")
debug_role_permissions('manager')
