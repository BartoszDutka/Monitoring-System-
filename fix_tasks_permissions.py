#!/usr/bin/env python3
"""
Skrypt do naprawy uprawnień zadań - usunięcie duplikatów i ujednolicenie nazw
"""

from modules.database import get_db_cursor

def fix_tasks_permissions():
    """Napraw uprawnienia zadań - usuń duplikaty i ujednolic nazwy"""
    print("=== NAPRAWA UPRAWNIEŃ ZADAŃ ===\n")
    
    with get_db_cursor() as cursor:
        print("1. Sprawdzenie obecnych uprawnień zadań...")
        cursor.execute("""
            SELECT permission_id, permission_key, name_en, name_pl
            FROM permissions 
            WHERE category = 'tasks' OR permission_key LIKE '%task%'
            ORDER BY permission_key
        """)
        
        current_perms = cursor.fetchall()
        print("Obecne uprawnienia:")
        for perm in current_perms:
            print(f"  - {perm['permission_key']} (ID: {perm['permission_id']}) - {perm['name_en']}")
        
        print("\n2. Usuwanie duplikatów...")
        
        # Mapowanie: duplikat -> właściwe uprawnienie
        duplicates_map = {
            'tasks_create': 'create_tasks',  # tasks_create -> create_tasks
            'tasks_manage_all': 'manage_all_tasks'  # tasks_manage_all -> manage_all_tasks
        }
        
        for duplicate, correct in duplicates_map.items():
            print(f"\nPrzetwarzanie duplikatu: {duplicate} -> {correct}")
            
            # Sprawdź czy duplikat istnieje
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (duplicate,))
            dup_perm = cursor.fetchone()
            
            # Sprawdź czy właściwe uprawnienie istnieje  
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (correct,))
            correct_perm = cursor.fetchone()
            
            if dup_perm and correct_perm:
                print(f"  Znaleziono duplikat {duplicate} (ID: {dup_perm['permission_id']}) i właściwe {correct} (ID: {correct_perm['permission_id']})")
                
                # Przenieś przypisania ról z duplikatu na właściwe uprawnienie
                cursor.execute("""
                    SELECT role_id FROM role_permissions 
                    WHERE permission_id = %s
                """, (dup_perm['permission_id'],))
                
                roles_with_duplicate = cursor.fetchall()
                
                for role in roles_with_duplicate:
                    # Sprawdź czy rola ma już właściwe uprawnienie
                    cursor.execute("""
                        SELECT 1 FROM role_permissions 
                        WHERE role_id = %s AND permission_id = %s
                    """, (role['role_id'], correct_perm['permission_id']))
                    
                    if not cursor.fetchone():
                        # Dodaj właściwe uprawnienie do roli
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                        """, (role['role_id'], correct_perm['permission_id']))
                        print(f"    Dodano {correct} do roli (ID: {role['role_id']})")
                
                # Usuń duplikat z role_permissions
                cursor.execute("""
                    DELETE FROM role_permissions 
                    WHERE permission_id = %s
                """, (dup_perm['permission_id'],))
                
                # Usuń duplikat z permissions
                cursor.execute("""
                    DELETE FROM permissions 
                    WHERE permission_id = %s
                """, (dup_perm['permission_id'],))
                
                print(f"  ✅ Usunięto duplikat {duplicate}")
                
            elif dup_perm and not correct_perm:
                print(f"  Duplikat {duplicate} istnieje, ale brak właściwego {correct} - przemianowuję")
                # Przemianuj duplikat na właściwą nazwę
                cursor.execute("""
                    UPDATE permissions 
                    SET permission_key = %s 
                    WHERE permission_id = %s
                """, (correct, dup_perm['permission_id']))
                print(f"  ✅ Przemianowano {duplicate} na {correct}")
                
            elif not dup_perm and correct_perm:
                print(f"  ✅ Duplikat {duplicate} już nie istnieje, właściwe {correct} jest OK")
                
            else:
                print(f"  ⚠️ Ani duplikat {duplicate} ani właściwe {correct} nie istnieją")
        
        print("\n3. Sprawdzenie czy wszystkie potrzebne uprawnienia istnieją...")
        
        # Lista wszystkich potrzebnych uprawnień zadań
        required_permissions = [
            {
                'key': 'create_tasks',
                'name_en': 'Create Tasks',
                'name_pl': 'Tworzenie zadań',
                'description_en': 'Create new tasks and assign them to users',
                'description_pl': 'Tworzenie nowych zadań i przypisywanie ich użytkownikom'
            },
            {
                'key': 'tasks_update',
                'name_en': 'Update Tasks',
                'name_pl': 'Aktualizacja zadań',
                'description_en': 'Update task status and modify task details',
                'description_pl': 'Aktualizacja statusu zadań i modyfikacja szczegółów'
            },
            {
                'key': 'tasks_comment',
                'name_en': 'Comment on Tasks',
                'name_pl': 'Komentowanie zadań',
                'description_en': 'Add comments to tasks',
                'description_pl': 'Dodawanie komentarzy do zadań'
            },
            {
                'key': 'tasks_delete',
                'name_en': 'Delete Tasks',
                'name_pl': 'Usuwanie zadań',
                'description_en': 'Delete tasks from the system',
                'description_pl': 'Usuwanie zadań z systemu'
            },
            {
                'key': 'tasks_view',
                'name_en': 'View Tasks',
                'name_pl': 'Wyświetlanie zadań',
                'description_en': 'View assigned tasks and task details',
                'description_pl': 'Przeglądanie przypisanych zadań i szczegółów'
            },
            {
                'key': 'manage_all_tasks',
                'name_en': 'Manage All Tasks',
                'name_pl': 'Zarządzanie wszystkimi zadaniami',
                'description_en': 'View and manage all tasks in the system regardless of assignment',
                'description_pl': 'Przeglądanie i zarządzanie wszystkimi zadaniami niezależnie od przypisania'
            }
        ]
        
        for perm in required_permissions:
            cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = %s", (perm['key'],))
            if not cursor.fetchone():
                print(f"  Dodaję brakujące uprawnienie: {perm['key']}")
                cursor.execute("""
                    INSERT INTO permissions (permission_key, category, name_en, name_pl, description_en, description_pl)
                    VALUES (%s, 'tasks', %s, %s, %s, %s)
                """, (perm['key'], perm['name_en'], perm['name_pl'], perm['description_en'], perm['description_pl']))
            else:
                print(f"  ✅ {perm['key']} już istnieje")
        
        print("\n4. Finalne sprawdzenie uprawnień zadań...")
        cursor.execute("""
            SELECT permission_key, name_en, name_pl
            FROM permissions 
            WHERE category = 'tasks'
            ORDER BY permission_key
        """)
        
        final_perms = cursor.fetchall()
        print("Finalne uprawnienia zadań:")
        for perm in final_perms:
            print(f"  ✅ {perm['permission_key']} - {perm['name_en']}")
        
        print(f"\n✅ Naprawiono {len(final_perms)} uprawnień zadań")
        return True

if __name__ == "__main__":
    try:
        fix_tasks_permissions()
        print("\n🎉 Naprawa uprawnień zadań zakończona pomyślnie!")
    except Exception as e:
        print(f"\n❌ Błąd podczas naprawy uprawnień: {e}")
        import traceback
        traceback.print_exc()
