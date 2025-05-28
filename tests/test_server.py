"""Tests for the main MCP server."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from google_mcp_server.server import GoogleMCPServer


class TestGoogleMCPServer:
    """Test GoogleMCPServer class."""
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    def test_init_success(self):
        """Test successful server initialization."""
        server = GoogleMCPServer()
        assert server.client_id == 'test_client_id'
        assert server.client_secret == 'test_client_secret'
        assert server.redirect_uri == 'http://localhost:8080'  # default
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret',
        'GOOGLE_REDIRECT_URI': 'http://localhost:9000',
        'GOOGLE_ADDITIONAL_SCOPES': 'scope1 scope2'
    })
    def test_init_with_custom_config(self):
        """Test server initialization with custom configuration."""
        server = GoogleMCPServer()
        assert server.redirect_uri == 'http://localhost:9000'
        assert server.additional_scopes == ['scope1', 'scope2']
    
    def test_init_missing_credentials(self):
        """Test server initialization with missing credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"):
                GoogleMCPServer()
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('google_mcp_server.server.GoogleAuthManager')
    def test_get_credentials_success(self, mock_auth_manager_class):
        """Test successful credential retrieval."""
        # Mock auth manager
        mock_auth_manager = Mock()
        mock_creds = Mock()
        mock_auth_manager.get_credentials.return_value = mock_creds
        mock_auth_manager_class.return_value = mock_auth_manager
        
        server = GoogleMCPServer()
        result = server._get_credentials()
        assert result == mock_creds
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('google_mcp_server.server.GoogleAuthManager')
    def test_get_credentials_failure(self, mock_auth_manager_class):
        """Test credential retrieval failure."""
        # Mock auth manager
        mock_auth_manager = Mock()
        mock_auth_manager.get_credentials.return_value = None
        mock_auth_manager_class.return_value = mock_auth_manager
        
        server = GoogleMCPServer()
        with pytest.raises(RuntimeError, match="Failed to authenticate with Google"):
            server._get_credentials()
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('google_mcp_server.server.GoogleAuthManager')
    async def test_handle_auth_status_success(self, mock_auth_manager_class):
        """Test successful authentication status check."""
        # Mock auth manager
        mock_auth_manager = Mock()
        mock_user_info = {'name': 'Test User', 'email': 'test@example.com'}
        mock_auth_manager.get_user_info.return_value = mock_user_info
        mock_auth_manager_class.return_value = mock_auth_manager
        
        server = GoogleMCPServer()
        result = await server._handle_auth_status()
        
        assert len(result) == 1
        assert "✅ Authenticated as: Test User (test@example.com)" in result[0].text
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('google_mcp_server.server.GoogleAuthManager')
    async def test_handle_auth_status_not_authenticated(self, mock_auth_manager_class):
        """Test authentication status check when not authenticated."""
        # Mock auth manager
        mock_auth_manager = Mock()
        mock_auth_manager.get_user_info.return_value = None
        mock_auth_manager_class.return_value = mock_auth_manager
        
        server = GoogleMCPServer()
        result = await server._handle_auth_status()
        
        assert len(result) == 1
        assert "❌ Not authenticated" in result[0].text
    
    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'test_client_id',
        'GOOGLE_CLIENT_SECRET': 'test_client_secret'
    })
    @patch('google_mcp_server.server.GoogleAuthManager')
    async def test_handle_auth_revoke_success(self, mock_auth_manager_class):
        """Test successful authentication revocation."""
        # Mock auth manager
        mock_auth_manager = Mock()
        mock_auth_manager.revoke_credentials.return_value = True
        mock_auth_manager_class.return_value = mock_auth_manager
        
        server = GoogleMCPServer()
        result = await server._handle_auth_revoke()
        
        assert len(result) == 1
        assert "✅ Authentication revoked successfully" in result[0].text
        # Check that clients are cleared
        assert server.drive_client is None
        assert server.gmail_client is None
        assert server.calendar_client is None