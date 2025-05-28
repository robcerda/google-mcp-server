"""Google MCP Server - Main server implementation."""

import os
import logging
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mcp.types as types

from .auth import GoogleAuthManager
from .drive_client import GoogleDriveClient
from .gmail_client import GmailClient
from .calendar_client import GoogleCalendarClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get configuration from environment
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080")

# Parse additional scopes
additional_scopes_str = os.getenv("GOOGLE_ADDITIONAL_SCOPES", "")
additional_scopes = additional_scopes_str.split() if additional_scopes_str else None

# Validate required configuration
if not client_id or not client_secret:
    raise ValueError(
        "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables. "
        "See README.md for setup instructions."
    )

# Initialize auth manager
auth_manager = GoogleAuthManager(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    additional_scopes=additional_scopes
)

# Initialize service clients (will be created when first needed)
drive_client: Optional[GoogleDriveClient] = None
gmail_client: Optional[GmailClient] = None
calendar_client: Optional[GoogleCalendarClient] = None

# Create FastMCP server
mcp = FastMCP("google-mcp-server")

def get_credentials():
    """Get valid Google credentials, handling authentication flow if needed."""
    creds = auth_manager.get_credentials()
    if not creds:
        raise RuntimeError("Failed to authenticate with Google. Please check your configuration.")
    return creds

def get_drive_client() -> GoogleDriveClient:
    """Get or create Google Drive client."""
    global drive_client
    if not drive_client:
        drive_client = GoogleDriveClient(get_credentials())
    return drive_client

def get_gmail_client() -> GmailClient:
    """Get or create Gmail client."""
    global gmail_client
    if not gmail_client:
        gmail_client = GmailClient(get_credentials())
    return gmail_client

def get_calendar_client() -> GoogleCalendarClient:
    """Get or create Google Calendar client."""
    global calendar_client
    if not calendar_client:
        calendar_client = GoogleCalendarClient(get_credentials())
    return calendar_client

# Authentication tools
@mcp.tool()
def google_auth_status() -> str:
    """Check Google authentication status and user info"""
    try:
        user_info = auth_manager.get_user_info()
        if user_info:
            return f"✅ Authenticated as: {user_info.get('name', 'Unknown')} ({user_info.get('email', 'Unknown')})"
        else:
            return "❌ Not authenticated"
    except Exception as e:
        return f"Authentication check failed: {str(e)}"

@mcp.tool()
def google_auth_revoke() -> str:
    """Revoke Google authentication and clear stored credentials"""
    try:
        global drive_client, gmail_client, calendar_client
        success = auth_manager.revoke_credentials()
        if success:
            # Clear cached clients
            drive_client = None
            gmail_client = None
            calendar_client = None
            return "✅ Authentication revoked successfully"
        else:
            return "❌ Failed to revoke authentication"
    except Exception as e:
        return f"Error revoking authentication: {str(e)}"

# Google Drive tools
@mcp.tool()
def drive_list_files(query: str = "", folder_id: str = "", max_results: int = 10) -> str:
    """List files in Google Drive"""
    try:
        client = get_drive_client()
        result = client.list_files(
            query=query if query else None,
            folder_id=folder_id if folder_id else None,
            max_results=max_results
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_get_file(file_id: str, include_content: bool = False) -> str:
    """Get file metadata and content from Google Drive"""
    try:
        client = get_drive_client()
        result = client.get_file(file_id=file_id, include_content=include_content)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_upload_file(name: str, content: str, parent_folder_id: str = "", mime_type: str = "text/plain") -> str:
    """Upload a file to Google Drive"""
    try:
        client = get_drive_client()
        result = client.upload_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            mime_type=mime_type
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_folder(name: str, parent_folder_id: str = "") -> str:
    """Create a folder in Google Drive"""
    try:
        client = get_drive_client()
        result = client.create_folder(
            name=name,
            parent_folder_id=parent_folder_id if parent_folder_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Gmail tools
@mcp.tool()
def gmail_list_messages(query: str = "", max_results: int = 10, include_spam_trash: bool = False) -> str:
    """List Gmail messages"""
    try:
        client = get_gmail_client()
        result = client.list_messages(
            query=query if query else None,
            max_results=max_results,
            include_spam_trash=include_spam_trash
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_get_message(message_id: str, format: str = "full") -> str:
    """Get a specific Gmail message"""
    try:
        client = get_gmail_client()
        result = client.get_message(message_id=message_id, format=format)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_send_message(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Send a Gmail message"""
    try:
        client = get_gmail_client()
        result = client.send_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc if cc else None,
            bcc=bcc if bcc else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Google Calendar tools
@mcp.tool()
def calendar_list_calendars() -> str:
    """List available Google Calendars"""
    try:
        client = get_calendar_client()
        result = client.list_calendars()
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_list_events(calendar_id: str = "primary", time_min: str = "", time_max: str = "", max_results: int = 10) -> str:
    """List Google Calendar events"""
    try:
        client = get_calendar_client()
        result = client.list_events(
            calendar_id=calendar_id,
            time_min=time_min if time_min else None,
            time_max=time_max if time_max else None,
            max_results=max_results
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_create_event(
    summary: str, 
    start_time: str, 
    end_time: str, 
    calendar_id: str = "primary",
    description: str = "",
    location: str = "",
    attendees: str = ""
) -> str:
    """Create a Google Calendar event"""
    try:
        client = get_calendar_client()
        result = client.create_event(
            calendar_id=calendar_id,
            summary=summary,
            description=description if description else None,
            start_time=start_time,
            end_time=end_time,
            location=location if location else None,
            attendees=attendees if attendees else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Export for mcp run
app = mcp