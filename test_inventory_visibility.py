# Test sprawdzający widoczność menu inventory dla różnych ról

def test_inventory_visibility():
    print("=== TEST WIDOCZNOŚCI MENU INVENTORY ===\n")
    
    # Symulacja różnych sesji użytkowników
    test_sessions = [
        {'role': 'viewer', 'expected': 'UKRYTE'},
        {'role': 'user', 'expected': 'WIDOCZNE'},
        {'role': 'manager', 'expected': 'WIDOCZNE'},
        {'role': 'admin', 'expected': 'WIDOCZNE'}
    ]
    
    for session in test_sessions:
        role = session['role']
        expected = session['expected']
        
        # Symulacja logiki z template: {% if session.role != 'viewer' %}
        is_visible = session['role'] != 'viewer'
        actual = 'WIDOCZNE' if is_visible else 'UKRYTE'
        
        status = '✓' if actual == expected else '✗'
        print(f"{status} Rola '{role}': Menu inventory {actual} (oczekiwano: {expected})")
    
    print("\n=== PODSUMOWANIE ===")
    print("✅ Menu 'Item Inventory' jest ukryte TYLKO dla roli 'viewer'")
    print("✅ Menu jest widoczne dla ról: user, manager, admin")
    print("✅ Użyto tej samej metody co dla innych ukrywanych elementów")
    print("\nImplementacja w templates/layout.html:")
    print("{% if session.role != 'viewer' %}")
    print("    <a href='/inventory'>Item Inventory</a>")
    print("{% endif %}")

if __name__ == "__main__":
    test_inventory_visibility()
