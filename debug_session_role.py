"""
Debug script to check how role is stored in session
"""

def debug_session_access():
    print("=== DEBUG: SPRAWDZENIE DOSTĘPU DO ROLE W SESSION ===\n")
    
    # Symulacja różnych sposobów dostępu do roli
    test_sessions = [
        {
            'name': 'Session z user_info dict',
            'session': {
                'logged_in': True,
                'username': 'viewer_user',
                'user_info': {'role': 'viewer', 'username': 'viewer_user'}
            }
        },
        {
            'name': 'Session z bezpośrednią rolą',
            'session': {
                'logged_in': True,
                'username': 'viewer_user',
                'role': 'viewer'
            }
        },
        {
            'name': 'Session z oboma',
            'session': {
                'logged_in': True,
                'username': 'viewer_user', 
                'role': 'viewer',
                'user_info': {'role': 'viewer', 'username': 'viewer_user'}
            }
        }
    ]
    
    for test in test_sessions:
        print(f"Test: {test['name']}")
        session = test['session']
        
        # Sprawdź różne sposoby dostępu
        role_1 = session.get('role')
        role_2 = None
        if 'user_info' in session and isinstance(session['user_info'], dict):
            role_2 = session['user_info'].get('role')
        
        print(f"  session.get('role'): {role_1}")
        print(f"  session['user_info'].get('role'): {role_2}")
        
        # Logika z inventory.py
        user_role = None
        if 'user_info' in session and isinstance(session['user_info'], dict):
            user_role = session['user_info'].get('role')
        if not user_role:
            user_role = session.get('role')
            
        print(f"  Finalna role: {user_role}")
        print(f"  Czy viewer?: {user_role == 'viewer'}")
        print(f"  Zablokowany?: {'TAK' if user_role == 'viewer' else 'NIE'}")
        print()

if __name__ == "__main__":
    debug_session_access()
    
    print("=== SPRAWDZENIE TEMPLATE SESSION.ROLE ===")
    print("W template layout.html używane jest: session.role")
    print("To znaczy, że Flask automatycznie udostępnia session['role'] jako session.role")
    print("ALBO role jest ustawiana bezpośrednio w session podczas logowania")
    print("\nSprawdź w app.py jak session jest ustawiana podczas login!")
