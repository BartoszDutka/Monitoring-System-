"""
Functions for managing task-related permissions
"""
from modules.database import get_db_cursor
from flask import session

def cleanup_duplicate_task_permissions():
    """
    Remove duplicate View Tasks permissions.
    This addresses the issue where both 'tasks_view' and 'view_tasks' may appear in the UI.
    """
    try:
        with get_db_cursor() as cursor:
            # First check if 'view_tasks' exists
            cursor.execute("""
                SELECT permission_id FROM permissions 
                WHERE permission_key = 'view_tasks'
            """)
            view_tasks = cursor.fetchone()
            
            # Also check if 'tasks_view' exists
            cursor.execute("""
                SELECT permission_id FROM permissions 
                WHERE permission_key = 'tasks_view'
            """)
            tasks_view = cursor.fetchone()
            
            # If both exist, we need to fix the duplicate
            if view_tasks and tasks_view:
                print(f"Found duplicate task view permissions: 'view_tasks' (ID: {view_tasks['permission_id']}) and 'tasks_view' (ID: {tasks_view['permission_id']})")
                
                # Update any role_permissions using view_tasks to use tasks_view instead
                cursor.execute("""
                    UPDATE role_permissions 
                    SET permission_id = %s
                    WHERE permission_id = %s
                """, (tasks_view['permission_id'], view_tasks['permission_id']))
                
                # Delete the view_tasks permission
                cursor.execute("""
                    DELETE FROM permissions
                    WHERE permission_id = %s
                """, (view_tasks['permission_id'],))
                
                print(f"Removed duplicate 'view_tasks' permission and consolidated role assignments to 'tasks_view'")
                return True
                
        # No duplicates found
        return True
    except Exception as e:
        print(f"Error cleaning up duplicate task permissions: {e}")
        return False

def initialize_task_permissions():
    """
    Ensure task-related permissions are added to the database
    """
    permissions = [
        {
            'key': 'tasks_view',
            'category': 'tasks',
            'name_en': 'View Tasks',
            'name_pl': 'Wyświetlanie zadań',
            'description_en': 'Allows users to view tasks assigned to them',
            'description_pl': 'Pozwala użytkownikom przeglądać przydzielone im zadania'
        },
        {
            'key': 'tasks_create',
            'category': 'tasks',
            'name_en': 'Create Tasks',
            'name_pl': 'Tworzenie zadań',
            'description_en': 'Allows users to create new tasks',
            'description_pl': 'Pozwala użytkownikom tworzyć nowe zadania'
        },
        {
            'key': 'tasks_update',
            'category': 'tasks',
            'name_en': 'Update Tasks',
            'name_pl': 'Aktualizacja zadań',
            'description_en': 'Allows users to update their assigned tasks',
            'description_pl': 'Pozwala użytkownikom aktualizować przydzielone im zadania'
        },
        {
            'key': 'tasks_delete',
            'category': 'tasks',
            'name_en': 'Delete Tasks',
            'name_pl': 'Usuwanie zadań',
            'description_en': 'Allows users to delete tasks',
            'description_pl': 'Pozwala użytkownikom usuwać zadania'
        },
        {
            'key': 'tasks_comment',
            'category': 'tasks',
            'name_en': 'Comment on Tasks',
            'name_pl': 'Komentowanie zadań',
            'description_en': 'Allows users to add comments to tasks',
            'description_pl': 'Pozwala użytkownikom dodawać komentarze do zadań'
        },
        {
            'key': 'tasks_manage_all',
            'category': 'tasks',
            'name_en': 'Manage All Tasks',
            'name_pl': 'Zarządzanie wszystkimi zadaniami',
            'description_en': 'Allows users to view and manage all tasks, not just assigned ones',
            'description_pl': 'Pozwala użytkownikom przeglądać i zarządzać wszystkimi zadaniami, nie tylko przypisanymi'
        }
    ]
    
    try:
        with get_db_cursor() as cursor:
            # Add each permission if it doesn't exist
            for perm in permissions:
                cursor.execute("""
                    SELECT permission_id FROM permissions 
                    WHERE permission_key = %s
                """, (perm['key'],))
                
                result = cursor.fetchone()
                
                if not result:
                    # Permission doesn't exist, add it
                    cursor.execute("""
                        INSERT INTO permissions 
                        (permission_key, category, name_en, name_pl, description_en, description_pl)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        perm['key'],
                        perm['category'],
                        perm['name_en'],
                        perm['name_pl'],
                        perm['description_en'],
                        perm['description_pl']
                    ))
                    print(f"Added task permission: {perm['key']}")
            
            # Assign necessary permissions to admin role
            cursor.execute("SELECT role_id FROM roles WHERE role_key = 'admin'")
            admin_role = cursor.fetchone()
            
            if admin_role:
                admin_role_id = admin_role['role_id']
                
                # Get all task permission IDs
                cursor.execute("""
                    SELECT permission_id FROM permissions 
                    WHERE permission_key LIKE 'tasks_%'
                """)
                
                for perm in cursor.fetchall():
                    # Check if permission is already assigned
                    cursor.execute("""
                        SELECT 1 FROM role_permissions 
                        WHERE role_id = %s AND permission_id = %s
                    """, (admin_role_id, perm['permission_id']))
                    
                    if not cursor.fetchone():
                        # Assign permission to admin role
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                        """, (admin_role_id, perm['permission_id']))
            
            # Assign basic task permissions to regular user roles
            user_roles = ['manager', 'technician', 'analyst', 'operator', 'user']
            basic_permissions = ['tasks_view', 'tasks_update', 'tasks_comment']
            
            for role_key in user_roles:
                cursor.execute("SELECT role_id FROM roles WHERE role_key = %s", (role_key,))
                role = cursor.fetchone()
                
                if role:
                    role_id = role['role_id']
                    
                    for perm_key in basic_permissions:
                        cursor.execute("""
                            SELECT permission_id FROM permissions 
                            WHERE permission_key = %s
                        """, (perm_key,))
                        
                        perm = cursor.fetchone()
                        
                        if perm:
                            # Check if permission is already assigned
                            cursor.execute("""
                                SELECT 1 FROM role_permissions 
                                WHERE role_id = %s AND permission_id = %s
                            """, (role_id, perm['permission_id']))
                            
                            if not cursor.fetchone():                                # Assign permission to role
                                cursor.execute("""
                                    INSERT INTO role_permissions (role_id, permission_id)
                                    VALUES (%s, %s)
                                """, (role_id, perm['permission_id']))
            
            # Clear any cached permissions in active sessions
            # This is just for initialization - actual sessions will need to be refreshed through the API
            try:
                if 'permissions' in session:
                    session.pop('permissions')
                    print("Cleared permissions from current session")
            except RuntimeError:
                # This might happen outside of request context, which is fine
                pass
                
            return True
    except Exception as e:
        print(f"Error initializing task permissions: {e}")
        return False
