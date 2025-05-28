"""Google OAuth2 authentication handler with local credential storage."""

import json
import os
import webbrowser
from pathlib import Path
from typing import Optional, List
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
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
    'https://www.googleapis.com/auth/contacts',
    'https://www.googleapis.com/auth/gmail.addons.current.message.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
]

class GoogleAuthManager:
    """Manages Google OAuth2 authentication and credential storage."""
    
    def __init__(self, client_id: str, client_secret: str, 
                 redirect_uri: str = "http://localhost:8080",
                 additional_scopes: Optional[List[str]] = None):
        """
        Initialize the Google Auth Manager.
        
        Args:
            client_id: Google OAuth2 client ID
            client_secret: Google OAuth2 client secret
            redirect_uri: OAuth2 redirect URI (must match Google Console config)
            additional_scopes: Additional OAuth2 scopes beyond defaults
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # Combine default and additional scopes
        self.scopes = DEFAULT_SCOPES.copy()
        if additional_scopes:
            self.scopes.extend(additional_scopes)
        # Sort scopes to ensure consistent ordering
        self.scopes = sorted(self.scopes)
        
        # Credential storage path
        self.credentials_dir = Path.home() / '.config' / 'google-mcp-server'
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.credentials_dir / 'token.json'
        
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, refreshing or re-authenticating as needed.
        
        Returns:
            Valid Google OAuth2 credentials or None if authentication fails
        """
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