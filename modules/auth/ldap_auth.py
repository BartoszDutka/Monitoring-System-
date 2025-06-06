from ldap3 import Server, Connection, SIMPLE, ALL, SUBTREE, ALL_ATTRIBUTES, NTLM
from typing import Optional, Dict, Any
from config import *
from ..core.database import get_db_cursor
from ..data.user_data import create_user

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user against Active Directory and sync with local database"""
    try:
        # Create server object
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, use_ssl=False)
        authenticated = False
        
        # Try NTLM first
        try:
            conn = Connection(
                server,
                user=username,  # For NTLM, use just username
                password=password,
                authentication=NTLM
            )
            if conn.bind():
                authenticated = True
                conn.unbind()
        except Exception as ntlm_error:
            print(f"NTLM auth failed: {ntlm_error}")
            
            # If NTLM fails, try SIMPLE
            try:
                user_dn = f"{username}@{LDAP_DOMAIN}"
                conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=True
                )
                authenticated = True
                conn.unbind()
            except Exception as simple_auth_error:
                print(f"SIMPLE auth failed: {simple_auth_error}")

        if authenticated:
            # If LDAP authentication successful, sync user to database
            sync_ldap_user_to_db(username)
            return True
            
        return False
        
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def sync_ldap_user_to_db(username: str):
    """Synchronize LDAP user with local database"""
    user_info = get_user_info_from_ldap(username)
    if user_info:
        with get_db_cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            
            if not result:
                # Create new user
                cursor.execute("""
                    INSERT INTO users 
                    (username, email, display_name, role, avatar_path)
                    VALUES (%s, %s, %s, 'user', NULL)
                """, (username, user_info.get('mail'), user_info.get('displayName')))
            else:
                # Update existing user but preserve avatar_path
                cursor.execute("""
                    UPDATE users 
                    SET email = %s, 
                        display_name = %s
                    WHERE username = %s
                """, (user_info.get('mail'), user_info.get('displayName'), username))

def get_user_info_from_ldap(username: str) -> Optional[Dict[str, Any]]:
    """Get user information from Active Directory"""
    try:
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, use_ssl=False)
        service_user = f"{LDAP_SERVICE_USER}@{LDAP_DOMAIN}"
        
        conn = Connection(
            server,
            user=service_user,
            password=LDAP_SERVICE_PASSWORD,
            authentication=SIMPLE,
            auto_bind=True
        )
        
        search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
        conn.search(
            LDAP_BASE_DN,
            search_filter,
            SUBTREE,
            attributes=['displayName', 'mail', 'department', 'title']
        )
        
        if len(conn.entries) == 0:
            return None
            
        user_data = conn.entries[0]
        return {
            "displayName": str(user_data.displayName) if hasattr(user_data, 'displayName') else username,
            "mail": str(user_data.mail) if hasattr(user_data, 'mail') else None,
            "department": str(user_data.department) if hasattr(user_data, 'department') else None,
            "title": str(user_data.title) if hasattr(user_data, 'title') else None
        }
        
    except Exception as e:
        print(f"Error getting LDAP user info: {e}")
        return None
