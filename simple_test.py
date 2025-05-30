try:
    from modules.database import get_db_cursor
    print('Database import successful')
    
    with get_db_cursor() as cursor:
        cursor.execute('SELECT COUNT(*) as count FROM roles')
        result = cursor.fetchone()
        print(f'Roles count: {result["count"]}')
        
        cursor.execute('SELECT role_key FROM roles')
        roles = cursor.fetchall()
        print('Available roles:')
        for role in roles:
            print(f'  - {role["role_key"]}')
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
