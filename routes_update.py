# Poniżej znajdują się trasy, które należy zaktualizować w app.py

# 1. Zastąp istniejące trasy /manage_users i /manage_roles poniższymi:

@app.route('/manage_users')
@admin_required
def manage_users():
    """View and manage system users"""
    # Przekieruj do nowego ujednoliconego interfejsu z aktywną zakładką "users"
    return redirect(url_for('unified_management', active_tab='users'))

@app.route('/manage_roles')
@admin_required
def manage_roles():
    """View and manage system roles and permissions"""
    # Przekieruj do nowego ujednoliconego interfejsu z aktywną zakładką "roles"
    return redirect(url_for('unified_management', active_tab='roles'))

# 2. Dodaj nową trasę /unified_management poniżej:

@app.route('/unified_management')
@admin_required
def unified_management():
    """Unified interface for managing users, roles and permissions"""
    # Get active tab from query params
    active_tab = request.args.get('active_tab', 'users')
    
    # Get all users
    with get_db_cursor() as cursor:
        # Get users data
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        
        # Get all departments with their English and Polish descriptions
        cursor.execute('''
            SELECT name, description_en, description_pl
            FROM departments
            ORDER BY name
        ''')
        departments = cursor.fetchall()
        
        # Get all roles with their descriptions and user counts
        cursor.execute("""
            SELECT r.role_key, r.description_en, r.description_pl,
                   COUNT(u.user_id) as users_count,
                   (
                       SELECT COUNT(rp.permission_id)
                       FROM role_permissions rp
                       WHERE rp.role_id = r.role_id
                   ) as permissions_count        FROM roles r
            LEFT JOIN users u ON r.role_key = u.role        GROUP BY r.role_key, r.description_en, r.description_pl
            ORDER BY FIELD(r.role_key, 'admin', 'manager', 'user', 'viewer')
        """)
        roles = cursor.fetchall()
    
    # Get current language from session
    current_language = session.get('language', 'en')
    
    # Get permissions by category
    from modules.permissions import get_permissions_by_category
    permissions_by_category = get_permissions_by_category(current_language)
    
    # Remove unwanted permissions
    if 'reporting' in permissions_by_category:
        permissions_by_category['reporting'] = [
            p for p in permissions_by_category['reporting'] 
            if p['permission_key'] != 'export_reports'
        ]
    
    if 'monitoring' in permissions_by_category:
        permissions_by_category['monitoring'] = [
            p for p in permissions_by_category['monitoring'] 
            if p['permission_key'] != 'acknowledge_alerts'
        ]
    
    if 'assets' in permissions_by_category:
        permissions_by_category['assets'] = [
            p for p in permissions_by_category['assets'] 
            if p['permission_key'] != 'assign_assets'
        ]
    
    # Calculate total permissions count
    total_permissions_count = sum(len(perms) for perms in permissions_by_category.values())
    
    return render_template('unified_management.html',
                          users=users,
                          departments=departments,
                          roles=roles,
                          permissions_by_category=permissions_by_category,
                          total_permissions_count=total_permissions_count,
                          active_tab=active_tab,
                          lang=current_language)
