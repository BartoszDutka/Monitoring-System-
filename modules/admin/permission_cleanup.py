"""
Function to fix duplicate 'view_tasks' and 'tasks_view' permissions issue.
"""
from ..core.database import get_db_cursor

def cleanup_task_view_permissions():
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
                
                # Get all roles with the view_tasks permission
                cursor.execute("""
                    SELECT role_id FROM role_permissions
                    WHERE permission_id = %s
                """, (view_tasks['permission_id'],))
                
                roles_with_view_tasks = cursor.fetchall()
                
                # For each role, check if they already have tasks_view
                for role in roles_with_view_tasks:
                    cursor.execute("""
                        SELECT 1 FROM role_permissions
                        WHERE role_id = %s AND permission_id = %s
                    """, (role['role_id'], tasks_view['permission_id']))
                    
                    has_tasks_view = cursor.fetchone() is not None
                    
                    if not has_tasks_view:
                        # Add tasks_view permission to this role
                        cursor.execute("""
                            INSERT INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s)
                        """, (role['role_id'], tasks_view['permission_id']))
                
                # Remove all view_tasks permission assignments
                cursor.execute("""
                    DELETE FROM role_permissions
                    WHERE permission_id = %s
                """, (view_tasks['permission_id'],))
                
                # Delete the view_tasks permission
                cursor.execute("""
                    DELETE FROM permissions
                    WHERE permission_id = %s
                """, (view_tasks['permission_id'],))
                
                print(f"Removed duplicate 'view_tasks' permission and consolidated role assignments to 'tasks_view'")
                return True
                
            # No duplicates found
            print("No duplicate task view permissions found.")
            return True
    except Exception as e:
        print(f"Error cleaning up duplicate task permissions: {e}")
        return False
