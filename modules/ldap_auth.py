from ldap3 import Server, Connection, SIMPLE, ALL, SUBTREE, ALL_ATTRIBUTES, NTLM
from typing import Optional, Dict, Any
from config import *

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user against Active Directory"""
    try:
        # Create server object
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, use_ssl=False)
        
        # Create connection with user credentials using SIMPLE authentication
        user_dn = f"{username}@{LDAP_DOMAIN}"  # używamy pełnej nazwy domeny
        
        # Próbujemy najpierw z SIMPLE auth
        try:
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )
            conn.unbind()
            return True
        except Exception as simple_auth_error:
            print(f"SIMPLE auth failed: {simple_auth_error}")
            
            # Jeśli SIMPLE nie zadziała, próbujemy NTLM
            try:
                conn = Connection(
                    server,
                    user=username,  # sama nazwa użytkownika dla NTLM
                    password=password,
                    authentication=NTLM
                )
                if conn.bind():
                    conn.unbind()
                    return True
            except Exception as ntlm_error:
                print(f"NTLM auth failed: {ntlm_error}")
                
        return False
        
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def get_user_info(username: str) -> Optional[Dict[str, Any]]:
    """Get user information from Active Directory"""
    try:
        # Create server object
        server = Server(LDAP_SERVER, port=LDAP_PORT, get_info=ALL, use_ssl=False)
        
        # Create connection with service account
        service_user = f"{LDAP_SERVICE_USER}@{LDAP_DOMAIN}"
        conn = Connection(
            server,
            user=service_user,
            password=LDAP_SERVICE_PASSWORD,
            authentication=SIMPLE,
            auto_bind=True
        )
        
        # Search for user
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
            "title": str(user_data.title) if hasattr(user_data, 'title') else None,
            "avatar": None  # Dodajemy domyślną wartość dla avatara
        }
        
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None
