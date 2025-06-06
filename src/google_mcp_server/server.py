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
from .integration_client import GoogleIntegrationClient
from .contacts_client import GoogleContactsClient
from .smart_tools import SmartGoogleTools

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
integration_client: Optional[GoogleIntegrationClient] = None
contacts_client: Optional[GoogleContactsClient] = None
smart_tools: Optional[SmartGoogleTools] = None

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

def get_integration_client() -> GoogleIntegrationClient:
    """Get or create Google Integration client."""
    global integration_client
    if not integration_client:
        integration_client = GoogleIntegrationClient(
            get_drive_client(),
            get_gmail_client(),
            get_calendar_client()
        )
    return integration_client

def get_contacts_client() -> GoogleContactsClient:
    """Get or create Google Contacts client."""
    global contacts_client
    if not contacts_client:
        contacts_client = GoogleContactsClient(get_credentials())
    return contacts_client

def get_smart_tools() -> SmartGoogleTools:
    """Get or create Smart Google Tools."""
    global smart_tools
    if not smart_tools:
        smart_tools = SmartGoogleTools(
            get_contacts_client(),
            get_gmail_client(),
            get_drive_client(),
            get_calendar_client()
        )
    return smart_tools

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
        global drive_client, gmail_client, calendar_client, integration_client, contacts_client, smart_tools
        success = auth_manager.revoke_credentials()
        if success:
            # Clear cached clients
            drive_client = None
            gmail_client = None
            calendar_client = None
            integration_client = None
            contacts_client = None
            smart_tools = None
            return "✅ Authentication revoked successfully"
        else:
            return "❌ Failed to revoke authentication"
    except Exception as e:
        return f"Error revoking authentication: {str(e)}"

# Google Drive tools
@mcp.tool()
def drive_list_files(query: str = "", folder_id: str = "", max_results: int = 10, drive_id: str = "", include_team_drives: bool = True) -> str:
    """List files in Google Drive"""
    try:
        client = get_drive_client()
        result = client.list_files(
            query=query if query else None,
            folder_id=folder_id if folder_id else None,
            max_results=max_results,
            drive_id=drive_id if drive_id else None,
            include_team_drives=include_team_drives
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
def drive_upload_file(name: str, content: str, parent_folder_id: str = "", mime_type: str = "text/plain", drive_id: str = "") -> str:
    """Upload a file to Google Drive"""
    try:
        client = get_drive_client()
        result = client.upload_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            mime_type=mime_type,
            drive_id=drive_id if drive_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_file(name: str, content: str = "", parent_folder_id: str = "", mime_type: str = "text/plain", drive_id: str = "") -> str:
    """Create a file in Google Drive"""
    try:
        client = get_drive_client()
        result = client.create_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            mime_type=mime_type,
            drive_id=drive_id if drive_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_folder(name: str, parent_folder_id: str = "", drive_id: str = "") -> str:
    """Create a folder in Google Drive"""
    try:
        client = get_drive_client()
        result = client.create_folder(
            name=name,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            drive_id=drive_id if drive_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_copy_file(file_id: str, name: str = "", parent_folder_id: str = "") -> str:
    """Copy a file in Google Drive"""
    try:
        client = get_drive_client()
        result = client.copy_file(
            file_id=file_id,
            name=name if name else None,
            parent_folder_id=parent_folder_id if parent_folder_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_move_file(file_id: str, new_parent_folder_id: str, remove_from_current_parents: bool = True) -> str:
    """Move a file to a different folder in Google Drive"""
    try:
        client = get_drive_client()
        result = client.move_file(
            file_id=file_id,
            new_parent_folder_id=new_parent_folder_id,
            remove_from_current_parents=remove_from_current_parents
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_rename_file(file_id: str, new_name: str) -> str:
    """Rename a file in Google Drive"""
    try:
        client = get_drive_client()
        result = client.rename_file(file_id=file_id, new_name=new_name)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_update_file_content(file_id: str, content: str, mime_type: str = "") -> str:
    """Update the content of an existing file in Google Drive"""
    try:
        client = get_drive_client()
        result = client.update_file_content(
            file_id=file_id,
            content=content,
            mime_type=mime_type if mime_type else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_get_file_permissions(file_id: str) -> str:
    """Get file sharing permissions"""
    try:
        client = get_drive_client()
        result = client.get_file_permissions(file_id=file_id)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_share_file(file_id: str, email_address: str, role: str = "reader", send_notification: bool = True, message: str = "") -> str:
    """Share a file with a user"""
    try:
        client = get_drive_client()
        result = client.share_file(
            file_id=file_id,
            email_address=email_address,
            role=role,
            send_notification=send_notification,
            message=message if message else ""
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_list_shared_drives(max_results: int = 10) -> str:
    """List available shared drives"""
    try:
        client = get_drive_client()
        result = client.list_shared_drives(max_results=max_results)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_google_doc(name: str, content: str = "", parent_folder_id: str = "", drive_id: str = "") -> str:
    """Create a Google Doc"""
    try:
        client = get_drive_client()
        result = client.create_google_doc(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            drive_id=drive_id if drive_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_google_sheet(name: str, content: str = "", parent_folder_id: str = "", drive_id: str = "") -> str:
    """Create a Google Sheet"""
    try:
        client = get_drive_client()
        result = client.create_google_sheet(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            drive_id=drive_id if drive_id else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def drive_create_google_slide(name: str, content: str = "", parent_folder_id: str = "", drive_id: str = "") -> str:
    """Create a Google Slides presentation"""
    try:
        client = get_drive_client()
        result = client.create_google_slide(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id if parent_folder_id else None,
            drive_id=drive_id if drive_id else None
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

@mcp.tool()
def gmail_reply_to_message(message_id: str, body: str, include_original: bool = True) -> str:
    """Reply to a Gmail message"""
    try:
        client = get_gmail_client()
        result = client.reply_to_message(
            message_id=message_id,
            body=body,
            include_original=include_original
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_forward_message(message_id: str, to: str, body: str = "") -> str:
    """Forward a Gmail message"""
    try:
        client = get_gmail_client()
        result = client.forward_message(
            message_id=message_id,
            to=to,
            body=body
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_send_html_message(to: str, subject: str, html_body: str, text_body: str = "", cc: str = "", bcc: str = "") -> str:
    """Send an HTML Gmail message"""
    try:
        client = get_gmail_client()
        result = client.send_html_message(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body if text_body else "",
            cc=cc if cc else None,
            bcc=bcc if bcc else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_archive_message(message_id: str) -> str:
    """Archive a Gmail message"""
    try:
        client = get_gmail_client()
        result = client.archive_message(message_id=message_id)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_delete_message(message_id: str) -> str:
    """Delete a Gmail message (move to trash)"""
    try:
        client = get_gmail_client()
        result = client.delete_message(message_id=message_id)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_add_label(message_id: str, label_ids: str) -> str:
    """Add labels to a Gmail message (comma-separated label IDs)"""
    try:
        client = get_gmail_client()
        label_list = [label.strip() for label in label_ids.split(',') if label.strip()]
        result = client.add_label(message_id=message_id, label_ids=label_list)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_remove_label(message_id: str, label_ids: str) -> str:
    """Remove labels from a Gmail message (comma-separated label IDs)"""
    try:
        client = get_gmail_client()
        label_list = [label.strip() for label in label_ids.split(',') if label.strip()]
        result = client.remove_label(message_id=message_id, label_ids=label_list)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_create_draft(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Create a Gmail draft"""
    try:
        client = get_gmail_client()
        result = client.create_draft(
            to=to,
            subject=subject,
            body=body,
            cc=cc if cc else None,
            bcc=bcc if bcc else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def gmail_list_drafts(max_results: int = 10) -> str:
    """List Gmail drafts"""
    try:
        client = get_gmail_client()
        result = client.list_drafts(max_results=max_results)
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

@mcp.tool()
def calendar_search_events(query: str, calendar_id: str = "primary", time_min: str = "", time_max: str = "", max_results: int = 10) -> str:
    """Search events by text content"""
    try:
        client = get_calendar_client()
        result = client.search_events(
            query=query,
            calendar_id=calendar_id,
            time_min=time_min if time_min else None,
            time_max=time_max if time_max else None,
            max_results=max_results
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_duplicate_event(calendar_id: str, event_id: str, new_start_time: str, new_end_time: str, new_summary: str = "") -> str:
    """Duplicate an event to a new date/time"""
    try:
        client = get_calendar_client()
        result = client.duplicate_event(
            calendar_id=calendar_id,
            event_id=event_id,
            new_start_time=new_start_time,
            new_end_time=new_end_time,
            new_summary=new_summary if new_summary else None
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_respond_to_event(calendar_id: str, event_id: str, response: str) -> str:
    """Respond to an event invitation (accepted, declined, tentative)"""
    try:
        client = get_calendar_client()
        result = client.respond_to_event(
            calendar_id=calendar_id,
            event_id=event_id,
            response=response
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_get_free_busy_info(calendar_ids: str, time_min: str, time_max: str) -> str:
    """Check free/busy information for calendars (comma-separated calendar IDs)"""
    try:
        client = get_calendar_client()
        calendar_list = [cal_id.strip() for cal_id in calendar_ids.split(',') if cal_id.strip()]
        result = client.get_free_busy_info(
            calendar_ids=calendar_list,
            time_min=time_min,
            time_max=time_max
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_create_calendar(summary: str, description: str = "", time_zone: str = "UTC") -> str:
    """Create a new calendar"""
    try:
        client = get_calendar_client()
        result = client.create_calendar(
            summary=summary,
            description=description,
            time_zone=time_zone
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_delete_calendar(calendar_id: str) -> str:
    """Delete a calendar"""
    try:
        client = get_calendar_client()
        result = client.delete_calendar(calendar_id=calendar_id)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def calendar_set_event_reminders(calendar_id: str, event_id: str, reminders: str) -> str:
    """Set reminders for an event (JSON format: [{"method": "email", "minutes": 30}])"""
    try:
        import json
        client = get_calendar_client()
        reminder_list = json.loads(reminders)
        result = client.set_event_reminders(
            calendar_id=calendar_id,
            event_id=event_id,
            reminders=reminder_list
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Integration tools
@mcp.tool()
def create_meeting_from_email(message_id: str, proposed_time: str = "", duration_minutes: int = 60, calendar_id: str = "primary") -> str:
    """Parse an email and create a calendar event from it"""
    try:
        client = get_integration_client()
        result = client.create_meeting_from_email(
            message_id=message_id,
            proposed_time=proposed_time if proposed_time else "",
            duration_minutes=duration_minutes,
            calendar_id=calendar_id
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def save_email_to_drive(message_id: str, folder_id: str = "", file_format: str = "txt") -> str:
    """Save an email as a file in Google Drive"""
    try:
        client = get_integration_client()
        result = client.save_email_to_drive(
            message_id=message_id,
            folder_id=folder_id if folder_id else None,
            file_format=file_format
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def share_drive_file_via_email(file_id: str, recipient_email: str, message: str = "", subject: str = "", permission_role: str = "reader") -> str:
    """Share a Drive file and send email notification"""
    try:
        client = get_integration_client()
        result = client.share_drive_file_via_email(
            file_id=file_id,
            recipient_email=recipient_email,
            message=message,
            subject=subject if subject else "",
            permission_role=permission_role
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def unified_search(query: str, search_drive: bool = True, search_gmail: bool = True, search_calendar: bool = True, max_results: int = 5) -> str:
    """Search across Gmail, Drive, and Calendar with a single query"""
    try:
        client = get_integration_client()
        result = client.unified_search(
            query=query,
            search_drive=search_drive,
            search_gmail=search_gmail,
            search_calendar=search_calendar,
            max_results=max_results
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Contact management tools
@mcp.tool()
def contacts_debug() -> str:
    """Debug contacts API connection and permissions"""
    try:
        client = get_contacts_client()
        
        # Test basic API access
        try:
            result = client.service.people().connections().list(
                resourceName='people/me',
                pageSize=1,
                personFields='names'
            ).execute()
            
            connections = result.get('connections', [])
            total_size = result.get('totalSize', 0)
            
            debug_info = {
                'api_access': 'SUCCESS',
                'total_contacts': total_size,
                'sample_returned': len(connections),
                'next_page_token': result.get('nextPageToken', 'None'),
                'sync_token': result.get('syncToken', 'None')
            }
            
            if connections:
                sample_contact = connections[0]
                debug_info['sample_contact_fields'] = list(sample_contact.keys())
                if 'names' in sample_contact:
                    debug_info['sample_contact_name'] = sample_contact['names'][0].get('displayName', 'No display name')
            
            return str({
                'success': True,
                'debug_info': debug_info,
                'suggestion': 'API access working. If total_contacts is 0, you may need to add contacts to your Google account first.'
            })
            
        except Exception as api_error:
            return str({
                'success': False,
                'api_error': str(api_error),
                'suggestion': 'API access failed. You may need to re-authenticate with the contacts scope.'
            })
            
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def contacts_search(query: str, max_results: int = 10) -> str:
    """Search contacts by name or email"""
    try:
        client = get_contacts_client()
        result = client.search_contacts(query=query, max_results=max_results)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def contacts_list(max_results: int = 50) -> str:
    """List all contacts"""
    try:
        client = get_contacts_client()
        result = client.list_contacts(max_results=max_results)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def contacts_get(resource_name: str) -> str:
    """Get detailed contact information"""
    try:
        client = get_contacts_client()
        result = client.get_contact(resource_name=resource_name)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def contacts_resolve_email(name_or_email: str) -> str:
    """Resolve a contact name to email address"""
    try:
        client = get_contacts_client()
        result = client.resolve_contact_email(name_or_email=name_or_email)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Smart tools with contact resolution
@mcp.tool()
def smart_send_email(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> str:
    """Send email with automatic contact resolution (use names or emails)"""
    try:
        tools = get_smart_tools()
        result = tools.smart_send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc if cc else "",
            bcc=bcc if bcc else ""
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def smart_share_file(file_id: str, recipient: str, role: str = "reader", send_notification: bool = True, message: str = "") -> str:
    """Share file with automatic contact resolution (use names or emails)"""
    try:
        tools = get_smart_tools()
        result = tools.smart_share_file(
            file_id=file_id,
            recipient=recipient,
            role=role,
            send_notification=send_notification,
            message=message
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def smart_create_event(summary: str, start_time: str, end_time: str, attendees: str = "", calendar_id: str = "primary", description: str = "", location: str = "") -> str:
    """Create calendar event with automatic attendee resolution (use names or emails)"""
    try:
        tools = get_smart_tools()
        result = tools.smart_create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            calendar_id=calendar_id,
            description=description,
            location=location
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def smart_forward_email(message_id: str, to: str, body: str = "") -> str:
    """Forward email with automatic contact resolution (use names or emails)"""
    try:
        tools = get_smart_tools()
        result = tools.smart_forward_email(
            message_id=message_id,
            to=to,
            body=body
        )
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Export for mcp run
app = mcp