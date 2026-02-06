"""
LDAP Authentication Service
Authentifizierung gegen Active Directory / LDAP
"""
import logging
import ldap
from ldap.filter import filter_format
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


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
            logger.warning(f"LDAP authentication failed: Invalid credentials for user {username}")
            return False
        except ldap.SERVER_DOWN as e:
            logger.error(f"LDAP server unreachable: {self.server}:{self.port}")
            logger.debug(f"Server error details: {e}", exc_info=True)
            return False
        except ldap.LDAPError as e:
            logger.error(f"LDAP error during authentication for {username}: {type(e).__name__}")
            logger.debug(f"LDAP error details: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error during LDAP authentication for {username}: {type(e).__name__}")
            logger.debug(f"Unexpected error details: {e}", exc_info=True)
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
            search_filter = ldap.filter.filter_format("(uid=%s)", [username])  # oder (sAMAccountName={username}) für AD
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

        except ldap.SERVER_DOWN as e:
            logger.error(f"LDAP server unreachable during user search: {self.server}:{self.port}")
            logger.debug(f"Server error details: {e}", exc_info=True)
            return None
        except ldap.LDAPError as e:
            logger.error(f"LDAP error during user search for {username}: {type(e).__name__}")
            logger.debug(f"LDAP error details: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during LDAP user search for {username}: {type(e).__name__}")
            logger.debug(f"Unexpected error details: {e}", exc_info=True)
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
            
            search_filter = filter_format("(uid=%s)", [username])
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

        except ldap.SERVER_DOWN as e:
            logger.error(f"LDAP server unreachable during get_user_info: {self.server}:{self.port}")
            logger.debug(f"Server error details: {e}", exc_info=True)
            return None
        except ldap.LDAPError as e:
            logger.error(f"LDAP error during get_user_info for {username}: {type(e).__name__}")
            logger.debug(f"LDAP error details: {e}", exc_info=True)
            return None
        except (KeyError, IndexError, UnicodeDecodeError) as e:
            logger.error(f"Data parsing error during get_user_info for {username}: {type(e).__name__}")
            logger.debug(f"Parsing error details: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during get_user_info for {username}: {type(e).__name__}")
            logger.debug(f"Unexpected error details: {e}", exc_info=True)
            return None


# Singleton Instance
ldap_service = LDAPService()
