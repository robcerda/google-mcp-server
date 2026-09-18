"""Tests for the main MCP server module.

The server is a module-level FastMCP instance, not a class: configuration is
read and validated at import time, and each tool is a plain module-level
function registered with @mcp.tool(). Startup behaviour therefore has to be
exercised by reloading the module under a controlled environment.
"""

import importlib
import os
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from google_mcp_server import server as server_module

# A path that will never hold a service account key, so tests stay hermetic
# regardless of whether the developer running them has one installed.
NO_SERVICE_ACCOUNT = "/nonexistent/service-account.json"

GOOGLE_ENV_VARS = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "GOOGLE_ADDITIONAL_SCOPES",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
)

OAUTH_ENV = {
    "GOOGLE_CLIENT_ID": "test_client_id",
    "GOOGLE_CLIENT_SECRET": "test_client_secret",
}


def _reload_with(env):
    """Reload the server module with only the given Google env vars set."""
    for key in GOOGLE_ENV_VARS:
        os.environ.pop(key, None)
    os.environ.update(env)
    # Without a key path the manager would find a real one in ~/.config.
    os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_JSON", NO_SERVICE_ACCOUNT)
    importlib.reload(server_module)


@contextmanager
def reloaded_server(env):
    """
    Re-import server.py under a controlled environment.

    load_dotenv is patched out so the repository's own .env cannot leak real
    credentials into the test. The module is always reloaded back to a working
    OAuth configuration afterwards, so later tests see a sane server.
    """
    try:
        with patch.dict(os.environ), patch("dotenv.load_dotenv"):
            _reload_with(env)
            yield server_module
    finally:
        with patch.dict(os.environ), patch("dotenv.load_dotenv"):
            _reload_with(OAUTH_ENV)


@pytest.fixture
def mock_auth_manager():
    """Replace the module's auth manager with a mock."""
    manager = Mock()
    with patch.object(server_module, "auth_manager", manager):
        yield manager


class TestServerStartup:
    """Configuration read and validated at import time."""

    def test_reads_oauth_credentials(self):
        with reloaded_server(OAUTH_ENV) as server:
            assert server.client_id == "test_client_id"
            assert server.client_secret == "test_client_secret"
            assert server.redirect_uri == "http://localhost:8080"  # default
            assert server.auth_manager.use_service_account is False

    def test_reads_custom_redirect_and_scopes(self):
        env = dict(
            OAUTH_ENV,
            GOOGLE_REDIRECT_URI="http://localhost:9000",
            GOOGLE_ADDITIONAL_SCOPES="scope1 scope2",
        )
        with reloaded_server(env) as server:
            assert server.redirect_uri == "http://localhost:9000"
            assert server.additional_scopes == ["scope1", "scope2"]

    def test_missing_credentials_raises(self):
        with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"):
            with reloaded_server({}):
                pass

    def test_service_account_key_replaces_oauth_credentials(self, tmp_path):
        """A key file is enough on its own - no client ID or secret needed."""
        key_file = tmp_path / "service-account.json"
        key_file.write_text("{}")  # startup only checks that the file exists

        with reloaded_server({"GOOGLE_SERVICE_ACCOUNT_JSON": str(key_file)}) as server:
            assert server.auth_manager.use_service_account is True
            assert server.client_id is None


class TestGetCredentials:
    """The shared helper every client getter goes through."""

    def test_returns_credentials(self, mock_auth_manager):
        creds = Mock()
        mock_auth_manager.get_credentials.return_value = creds
        assert server_module.get_credentials() is creds

    def test_raises_when_authentication_fails(self, mock_auth_manager):
        mock_auth_manager.get_credentials.return_value = None
        with pytest.raises(RuntimeError, match="Failed to authenticate with Google"):
            server_module.get_credentials()


class TestAuthTools:
    """google_auth_status and google_auth_revoke."""

    def test_status_when_authenticated(self, mock_auth_manager):
        mock_auth_manager.get_user_info.return_value = {
            "name": "Test User",
            "email": "test@example.com",
        }
        result = server_module.google_auth_status()
        assert "✅ Authenticated as: Test User (test@example.com)" in result

    def test_status_reports_service_account(self, mock_auth_manager):
        mock_auth_manager.get_user_info.return_value = {
            "name": "Service Account",
            "email": "mcp@project.iam.gserviceaccount.com",
            "auth_mode": "service_account",
        }
        result = server_module.google_auth_status()
        assert "mcp@project.iam.gserviceaccount.com" in result

    def test_status_when_not_authenticated(self, mock_auth_manager):
        mock_auth_manager.get_user_info.return_value = None
        assert "❌ Not authenticated" in server_module.google_auth_status()

    def test_status_handles_errors(self, mock_auth_manager):
        mock_auth_manager.get_user_info.side_effect = RuntimeError("boom")
        assert "Authentication check failed" in server_module.google_auth_status()

    def test_revoke_clears_cached_clients(self, mock_auth_manager):
        mock_auth_manager.revoke_credentials.return_value = True

        # Prime the module-level client cache so we can watch it being cleared.
        cached = (
            "drive_client",
            "gmail_client",
            "calendar_client",
            "integration_client",
            "contacts_client",
            "smart_tools",
            "safe_tools",
        )
        for name in cached:
            setattr(server_module, name, Mock())

        result = server_module.google_auth_revoke()

        assert "✅ Authentication revoked successfully" in result
        for name in cached:
            assert getattr(server_module, name) is None, f"{name} was not cleared"

    def test_revoke_failure_keeps_clients(self, mock_auth_manager):
        mock_auth_manager.revoke_credentials.return_value = False
        client = Mock()
        server_module.drive_client = client

        result = server_module.google_auth_revoke()

        assert "❌ Failed to revoke authentication" in result
        assert server_module.drive_client is client
        server_module.drive_client = None


class TestToolRegistration:
    """Tools are registered with FastMCP and remain callable directly."""

    @pytest.fixture
    def registered(self):
        return set(server_module.mcp._tool_manager._tools)

    @pytest.mark.parametrize(
        "tool_name",
        [
            "google_auth_status",
            "google_auth_revoke",
            "drive_list_files",
            "drive_get_file",
            "gmail_send_message",
            "calendar_create_event",
            "contacts_search",
            "prepare_send_email",
            "confirm_send_email",
            "cancel_operation",
            "unified_search",
        ],
    )
    def test_core_tool_is_registered(self, registered, tool_name):
        assert tool_name in registered

    @pytest.mark.parametrize(
        "tool_name",
        [
            "drive_get_file_chunked",
            "analyze_file_structure",
            "process_large_json",
            "extract_json_section",
            "get_file_sample",
            "search_in_large_file",
        ],
    )
    def test_large_file_tool_is_registered(self, registered, tool_name):
        assert tool_name in registered

    def test_every_registered_tool_has_a_description(self, registered):
        tools = server_module.mcp._tool_manager._tools
        undocumented = [name for name in registered if not tools[name].description]
        assert not undocumented, f"tools missing a docstring: {undocumented}"

    def test_cancel_operation_takes_no_action(self):
        assert "No action was taken" in server_module.cancel_operation()
