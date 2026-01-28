"""
LDAP Authentication Service
Authentifizierung gegen Active Directory / LDAP
"""
import ldap
from typing import Optional
from app.core.config import settings


class LDAPService:
    """Service für LDAP-Authentifizierung"""
    
    def __init__(self):
        self.server = settings.LDAP_SERVER
        self.port = settings.LDAP_PORT
        self.base_dn = settings.LDAP_BASE_DN
        self.bind_dn = settings.LDAP_BIND_DN
        self.bind_password = settings.LDAP_BIND_PASSWORD
        self.use_ssl = settings.LDAP_USE_SSL
    
    def _get_connection(self) -> ldap.ldapobject.LDAPObject:
        """Erstellt LDAP-Verbindung"""
        protocol = "ldaps" if self.use_ssl else "ldap"
        ldap_url = f"{protocol}://{self.server}:{self.port}"
        
        conn = ldap.initialize(ldap_url)
        conn.set_option(ldap.OPT_REFERRALS, 0)
        
        if self.use_ssl:
            conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        return conn
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authentifiziert einen Benutzer gegen LDAP
        
        Args:
            username: Benutzername (z.B. "max.mustermann")
            password: Passwort
            
        Returns:
            True wenn Authentifizierung erfolgreich, sonst False
        """
        try:
            conn = self._get_connection()
            
            # Suche User DN
            user_dn = self._find_user_dn(username)
            if not user_dn:
                return False
            
            # Versuche Bind mit User-Credentials
            conn.simple_bind_s(user_dn, password)
            conn.unbind_s()
            
            return True
            
        except ldap.INVALID_CREDENTIALS:
            return False
        except Exception as e:
            print(f"LDAP Auth Error: {e}")
            return False
    
    def _find_user_dn(self, username: str) -> Optional[str]:
        """
        Findet den DN eines Benutzers
        
        Args:
            username: Benutzername
            
        Returns:
            DN des Benutzers oder None
        """
        try:
            conn = self._get_connection()
            conn.simple_bind_s(self.bind_dn, self.bind_password)
            
            # Suche nach User
            search_filter = f"(uid={username})"  # oder (sAMAccountName={username}) für AD
            result = conn.search_s(
                self.base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ["dn"]
            )
            
            conn.unbind_s()
            
            if result and len(result) > 0:
                return result[0][0]  # DN ist das erste Element
            
            return None
            
        except Exception as e:
            print(f"LDAP Search Error: {e}")
            return None
    
    def get_user_info(self, username: str) -> Optional[dict]:
        """
        Holt Benutzerinformationen aus LDAP
        
        Args:
            username: Benutzername
            
        Returns:
            Dictionary mit Benutzerinfos oder None
        """
        try:
            conn = self._get_connection()
            conn.simple_bind_s(self.bind_dn, self.bind_password)
            
            search_filter = f"(uid={username})"
            result = conn.search_s(
                self.base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ["mail", "cn", "displayName", "givenName", "sn"]
            )
            
            conn.unbind_s()
            
            if result and len(result) > 0:
                attrs = result[0][1]
                return {
                    "email": attrs.get("mail", [b""])[0].decode("utf-8"),
                    "full_name": attrs.get("displayName", [b""])[0].decode("utf-8"),
                    "first_name": attrs.get("givenName", [b""])[0].decode("utf-8"),
                    "last_name": attrs.get("sn", [b""])[0].decode("utf-8"),
                }
            
            return None
            
        except Exception as e:
            print(f"LDAP Get User Info Error: {e}")
            return None


# Singleton Instance
ldap_service = LDAPService()
