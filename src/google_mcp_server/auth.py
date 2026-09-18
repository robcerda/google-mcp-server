"""Google OAuth2 authentication handler with local credential storage."""

import json
import os
import webbrowser
from pathlib import Path
from typing import Optional, List
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Default scopes - comprehensive access to Google services
DEFAULT_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.appdata',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/gmail.addons.current.message.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
]

# Scopes used when authenticating as a service account.
#
# Deliberately narrower than DEFAULT_SCOPES: a service account is its own
# identity, so it can only reach data that has been explicitly shared with it.
# Gmail and Contacts are excluded because reading a human's mailbox or address
# book requires domain-wide delegation, which only a Google Workspace admin can
# grant - a personal Gmail account cannot. Calendar and Drive work without it,
# because calendars and folders can be shared with the service account directly.
SERVICE_ACCOUNT_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
]

# Where the service account key is looked for, unless GOOGLE_SERVICE_ACCOUNT_JSON
# points somewhere else.
DEFAULT_SERVICE_ACCOUNT_FILE = (
    Path.home() / '.config' / 'google-mcp-server' / 'service-account.json'
)


def find_service_account_key() -> Optional[Path]:
    """
    Locate the service account key file, if one is configured.

    Returns:
        Path to an existing key file, or None to fall back to the OAuth flow
    """
    override = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    path = Path(override).expanduser() if override else DEFAULT_SERVICE_ACCOUNT_FILE
    return path if path.exists() else None

class GoogleAuthManager:
    """Manages Google OAuth2 authentication and credential storage."""
    
    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 redirect_uri: str = "http://localhost:8080",
                 additional_scopes: Optional[List[str]] = None):
        """
        Initialize the Google Auth Manager.
        
        If a service account key file is present, that is used and the OAuth2
        flow is skipped entirely - which is the point, since Google Advanced
        Protection blocks the consent screen but not service account JWT
        signing. Otherwise the usual browser-based OAuth2 flow runs, and
        client_id/client_secret are required.
        
        Args:
            client_id: Google OAuth2 client ID (not needed for service accounts)
            client_secret: Google OAuth2 client secret (ditto)
            redirect_uri: OAuth2 redirect URI (must match Google Console config)
            additional_scopes: Additional scopes beyond the defaults
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # Service account key takes precedence over the OAuth flow
        self.service_account_file = find_service_account_key()
        self.use_service_account = self.service_account_file is not None
        self._service_account_credentials: Optional[service_account.Credentials] = None
        
        # Combine default and additional scopes
        base_scopes = SERVICE_ACCOUNT_SCOPES if self.use_service_account else DEFAULT_SCOPES
        self.scopes = base_scopes.copy()
        if additional_scopes:
            self.scopes.extend(additional_scopes)
        # Sort scopes to ensure consistent ordering
        self.scopes = sorted(set(self.scopes))
        
        if self.use_service_account:
            logger.info(f"Using service account credentials from {self.service_account_file}")
        elif not (self.client_id and self.client_secret):
            raise ValueError(
                "client_id and client_secret are required when no service account "
                "key file is present. See docs/setup.md for both auth modes."
            )
        
        # Credential storage path
        self.credentials_dir = Path.home() / '.config' / 'google-mcp-server'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.credentials_dir / 'token.json'
        
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, refreshing or re-authenticating as needed.
        
        Returns:
            Valid Google credentials or None if authentication fails
        """
        if self.use_service_account:
            return self._get_service_account_credentials()
        
        creds = None
        
        # Load existing token if available
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
                logger.info("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")
                
        # Refresh credentials if they're expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed expired credentials")
                self._save_credentials(creds)
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                creds = None
                
        # Run OAuth flow if we don't have valid credentials
        if not creds or not creds.valid:
            creds = self._run_oauth_flow()
            
        return creds
    
    def _get_service_account_credentials(self) -> Optional[service_account.Credentials]:
        """
        Build credentials from the service account key file.
        
        No consent screen and no browser: the key signs a JWT and exchanges it
        for an access token, which is why this works under Advanced Protection.
        
        Returns:
            Valid service account credentials or None if the key is unusable
        """
        try:
            if not self._service_account_credentials:
                self._service_account_credentials = service_account.Credentials.from_service_account_file(
                    str(self.service_account_file),
                    scopes=self.scopes
                )
                logger.info(
                    f"Loaded service account {self._service_account_credentials.service_account_email}"
                )
            
            creds = self._service_account_credentials
            if not creds.valid:
                creds.refresh(Request())
                logger.info("Refreshed service account access token")
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to load service account credentials: {e}")
            print(f"❌ Service account authentication failed: {e}")
            self._service_account_credentials = None
            return None
    
    def _run_oauth_flow(self) -> Optional[Credentials]:
        """
        Run the OAuth2 flow to get new credentials.
        
        Returns:
            New Google OAuth2 credentials or None if flow fails
        """
        try:
            # Create OAuth2 flow
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uris": [self.redirect_uri],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                self.scopes
            )
            
            # Use local server for OAuth callback
            port = int(self.redirect_uri.split(':')[-1]) if ':' in self.redirect_uri else 8080
            
            # If port is busy, try a few alternatives
            import socket
            def check_port(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(('localhost', port))
                        return True
                    except OSError:
                        return False
            
            original_port = port
            for attempt in range(5):
                if check_port(port):
                    break
                port += 1
            else:
                raise RuntimeError(f"Could not find available port starting from {original_port}")
            
            print(f"Starting OAuth2 flow...")
            print(f"Your browser will open to authenticate with Google.")
            print(f"If the browser doesn't open automatically, visit the URL that will be displayed.")
            
            # Update redirect URI if port changed
            if port != original_port:
                flow.redirect_uri = f"http://localhost:{port}"
            
            # Run local server and open browser
            creds = flow.run_local_server(port=port, open_browser=True)
            
            if creds:
                self._save_credentials(creds)
                logger.info("Successfully authenticated with Google")
                print("✅ Authentication successful!")
                return creds
            else:
                logger.error("OAuth flow returned no credentials")
                return None
                
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            print(f"❌ Authentication failed: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials) -> None:
        """
        Save credentials to local storage.
        
        Args:
            creds: Google OAuth2 credentials to save
        """
        try:
            with open(self.token_file, 'w') as f:
                f.write(creds.to_json())
            logger.info(f"Saved credentials to {self.token_file}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def revoke_credentials(self) -> bool:
        """
        Revoke stored credentials and delete local token file.
        
        Returns:
            True if successfully revoked, False otherwise
        """
        if self.use_service_account:
            self._service_account_credentials = None
            print(
                "ℹ️ Using a service account - there is no stored token to revoke. "
                f"To disable access, delete {self.service_account_file} or remove "
                "the key in the Google Cloud Console."
            )
            return True
        
        try:
            if self.token_file.exists():
                # Load credentials to revoke them
                creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)
                
                # Revoke the credentials
                if creds and creds.valid:
                    creds.revoke(Request())
                    logger.info("Revoked Google credentials")
                
                # Delete local token file
                self.token_file.unlink()
                logger.info("Deleted local token file")
                
                print("✅ Credentials revoked successfully")
                return True
            else:
                print("ℹ️ No credentials found to revoke")
                return True
                
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            print(f"❌ Failed to revoke credentials: {e}")
            return False
    
    def get_user_info(self) -> Optional[dict]:
        """
        Get basic user information using the credentials.
        
        Returns:
            User info dict or None if request fails
        """
        creds = self.get_credentials()
        if not creds:
            return None
        
        # A service account is its own identity, not a signed-in user, so the
        # userinfo endpoint does not apply - report the account itself instead.
        if self.use_service_account:
            return {
                'name': 'Service Account',
                'email': creds.service_account_email,
                'auth_mode': 'service_account',
            }
            
        try:
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    def test_authentication(self) -> bool:
        """
        Test if authentication is working by making a simple API call.
        
        Returns:
            True if authentication is working, False otherwise
        """
        user_info = self.get_user_info()
        if user_info:
            print(f"✅ Authentication test successful!")
            print(f"   Authenticated as: {user_info.get('name', 'Unknown')} ({user_info.get('email', 'Unknown')})")
            return True
        else:
            print("❌ Authentication test failed")
            return False