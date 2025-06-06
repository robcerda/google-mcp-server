# Google MCP Server

A Model Context Protocol (MCP) server that provides Claude with comprehensive access to Google services including Drive, Gmail, and Calendar through OAuth2 authentication with local credential storage.

## Features

- **🔐 Secure OAuth2 Authentication**: Local credential storage with browser-based authentication flow
- **📁 Google Drive Integration**: Complete file management with shared drive support
  - Upload, download, search, copy, move, rename, and share files
  - Folder management and permission control
  - Full shared drive compatibility
- **📧 Gmail Operations**: Comprehensive email management
  - Send text/HTML emails, reply, forward messages
  - Draft management, label operations, archive/delete
  - Advanced message search and filtering
- **📅 Google Calendar**: Full calendar management
  - Create, search, duplicate, and manage events
  - Free/busy checking, invitation responses
  - Calendar creation/deletion, reminder setup
- **🔗 Cross-Service Integration**: Smart workflows across services
  - Create meetings from emails automatically
  - Save emails as Drive files
  - Share files with email notifications
  - Unified search across all Google services
- **🔑 Custom Scopes**: Configure additional OAuth2 scopes for extended functionality
- **🏠 Local Credential Management**: Keep your API keys and tokens on your local machine
- **🚀 50 Total Tools**: Most comprehensive Google MCP integration available
- **👥 Smart Contact Resolution**: Use contact names instead of email addresses

## Prerequisites

- Python 3.12 or higher
- `uv` for dependency management
- A Google Cloud Console account
- Claude Desktop or MCP-compatible client

## Google Cloud Console Setup

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project selector dropdown (top-left, next to "Google Cloud")
3. Click "New Project"
4. Enter a project name (e.g., "claude-google-integration")
5. Select your organization (if applicable)
6. Click "Create"
7. Wait for the project to be created and make sure it's selected

### Step 2: Enable Required APIs

1. In the Google Cloud Console, navigate to "APIs & Services" > "Library"
2. Search for and enable the following APIs (click on each, then click "Enable"):
   - **Google Drive API**
   - **Gmail API**
   - **Google Calendar API**
   - **People API** (for contacts and user profile information)

### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (unless you're using Google Workspace)
3. Click "Create"
4. Fill in the required information:
   - **App name**: Choose a name (e.g., "Claude Google Integration")
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
5. Click "Save and Continue"
6. On the "Scopes" page, click "Save and Continue" (we'll add scopes in our application)
7. On the "Test users" page, add your email address to test the integration
8. Click "Save and Continue"
9. Review and click "Back to Dashboard"

### Step 4: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application" as the application type
4. Enter a name (e.g., "Google MCP Server")
5. Click "Create"
6. A dialog will appear with your client ID and client secret
7. **Important**: Copy both the Client ID and Client Secret - you'll need these for the MCP server

### Step 5: Configure Authorized Redirect URIs (if needed)

1. In the Credentials page, click on your newly created OAuth client ID
2. Under "Authorized redirect URIs", add: `http://localhost:8080`
3. Click "Save"

**Note**: The default redirect URI is `http://localhost:8080`. If you need to use a different port, make sure to update both the Google Cloud Console configuration and your `.env` file.

## Installation

```bash
# Clone or download the repository
git clone https://github.com/robcerda/google-mcp-server
cd google-mcp-server

# Install dependencies with uv
uv sync

# Test the server works
uv run python test_cli.py
```

## Configuration

### 1. Create Environment File

Copy the example environment file and configure your Google OAuth2 credentials:

```bash
cp .env.example .env
```

Edit the `.env` file with your Google Cloud Console credentials:

```env
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here

# Optional: Custom redirect URI (defaults to http://localhost:8080)
# GOOGLE_REDIRECT_URI=http://localhost:8080

# Optional: Additional scopes (space-separated)
# GOOGLE_ADDITIONAL_SCOPES=https://www.googleapis.com/auth/spreadsheets
```

### 2. Configure Claude Desktop

Add the server to your Claude Desktop configuration file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\\Claude\\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-services": {
      "command": "/path/to/google-mcp-server/.venv/bin/mcp",
      "args": [
        "run",
        "/path/to/google-mcp-server/server.py"
      ]
    }
  }
}
```

**Example with full path:**
```json
{
  "mcpServers": {
    "google-services": {
      "command": "/Users/rob/Scripts/google-mcp-server/.venv/bin/mcp",
      "args": [
        "run",
        "/Users/rob/Scripts/google-mcp-server/server.py"
      ]
    }
  }
}
```

**Alternative using uv (if MCP path issues):**
```json
{
  "mcpServers": {
    "google-services": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/Users/rob/Scripts/google-mcp-server/server.py"
      ],
      "cwd": "/Users/rob/Scripts/google-mcp-server"
    }
  }
}
```

**Note**: Use the full path to `uv` (find yours with `which uv`) to ensure Claude Desktop can locate it.

### 3. Test the Server

Before using with Claude Desktop, test the server:

```bash
# Test authentication and API access
uv run python test_cli.py

# Test the MCP server directly 
uv run mcp run server.py
```

## Usage

### First Run Authentication

When you first use the server, it will automatically launch your browser for OAuth2 authentication:

1. The server will open your default browser
2. Sign in to your Google account
3. Grant the requested permissions
4. The browser will redirect to a success page
5. Return to Claude - you're now authenticated!

Your credentials will be securely stored locally in `~/.config/google-mcp-server/token.json`.

### Available Tools (50 Total)

#### Authentication Tools

- **google_auth_status**: Check current authentication status
- **google_auth_revoke**: Revoke authentication and clear stored credentials

#### Google Drive Tools (17 tools)

**Basic Operations:**
- **drive_list_files**: List files in Google Drive
  - Parameters: `query`, `folder_id`, `max_results`, `drive_id`, `include_team_drives`
- **drive_get_file**: Get file metadata and content
  - Parameters: `file_id`, `include_content`
- **drive_create_file**: Create a file in Google Drive
  - Parameters: `name`, `content`, `parent_folder_id`, `mime_type`, `drive_id`
- **drive_upload_file**: Upload a file to Google Drive
  - Parameters: `name`, `content`, `parent_folder_id`, `mime_type`, `drive_id`
- **drive_create_folder**: Create a folder in Google Drive
  - Parameters: `name`, `parent_folder_id`

**File Management:**
- **drive_copy_file**: Copy files within Drive
  - Parameters: `file_id`, `name`, `parent_folder_id`
- **drive_move_file**: Move files between folders
  - Parameters: `file_id`, `new_parent_folder_id`, `remove_from_current_parents`
- **drive_rename_file**: Rename files
  - Parameters: `file_id`, `new_name`
- **drive_update_file_content**: Update existing file content
  - Parameters: `file_id`, `content`, `mime_type`

**Sharing & Permissions:**
- **drive_get_file_permissions**: View file sharing permissions
  - Parameters: `file_id`
- **drive_share_file**: Share files with users
  - Parameters: `file_id`, `email_address`, `role`, `send_notification`, `message`

**🔗 Shared Drive Support**: All Drive functions support both personal and shared drives via `drive_id` parameter.

**Shared Drive Operations:**
- **drive_list_shared_drives**: List available shared drives to get drive IDs
  - Parameters: `max_results`

**Google Native Formats:**
- **drive_create_google_doc**: Create Google Docs (supports HTML content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`
- **drive_create_google_sheet**: Create Google Sheets (supports CSV content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`
- **drive_create_google_slide**: Create Google Slides (supports HTML content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`

#### Gmail Tools (12 tools)

**Basic Operations:**
- **gmail_list_messages**: List Gmail messages
  - Parameters: `query`, `max_results`, `include_spam_trash`
- **gmail_get_message**: Get a specific Gmail message
  - Parameters: `message_id`, `format`
- **gmail_send_message**: Send a Gmail message
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **gmail_send_html_message**: Send rich HTML emails
  - Parameters: `to`, `subject`, `html_body`, `text_body`, `cc`, `bcc`

**Message Management:**
- **gmail_reply_to_message**: Reply to emails with proper threading
  - Parameters: `message_id`, `body`, `include_original`
- **gmail_forward_message**: Forward emails
  - Parameters: `message_id`, `to`, `body`
- **gmail_archive_message**: Archive messages
  - Parameters: `message_id`
- **gmail_delete_message**: Move messages to trash
  - Parameters: `message_id`

**Label Management:**
- **gmail_add_label**: Add labels to messages
  - Parameters: `message_id`, `label_ids` (comma-separated)
- **gmail_remove_label**: Remove labels from messages
  - Parameters: `message_id`, `label_ids` (comma-separated)

**Draft Management:**
- **gmail_create_draft**: Create draft messages
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **gmail_list_drafts**: List draft messages
  - Parameters: `max_results`

#### Google Calendar Tools (10 tools)

**Basic Operations:**
- **calendar_list_calendars**: List available calendars
- **calendar_list_events**: List calendar events
  - Parameters: `calendar_id`, `time_min`, `time_max`, `max_results`
- **calendar_create_event**: Create calendar events
  - Parameters: `summary`, `start_time`, `end_time`, `description`, `location`, `attendees`
- **calendar_search_events**: Search events by content
  - Parameters: `query`, `calendar_id`, `time_min`, `time_max`, `max_results`

**Event Management:**
- **calendar_duplicate_event**: Copy events to other dates
  - Parameters: `calendar_id`, `event_id`, `new_start_time`, `new_end_time`, `new_summary`
- **calendar_respond_to_event**: Accept/decline invitations
  - Parameters: `calendar_id`, `event_id`, `response` (accepted/declined/tentative)
- **calendar_set_event_reminders**: Configure event notifications
  - Parameters: `calendar_id`, `event_id`, `reminders` (JSON format)

**Calendar Management:**
- **calendar_create_calendar**: Create new calendars
  - Parameters: `summary`, `description`, `time_zone`
- **calendar_delete_calendar**: Delete calendars
  - Parameters: `calendar_id`
- **calendar_get_free_busy_info**: Check availability
  - Parameters: `calendar_ids` (comma-separated), `time_min`, `time_max`

#### Cross-Service Integration Tools (4 tools)

- **create_meeting_from_email**: Parse emails to create calendar events
  - Parameters: `message_id`, `proposed_time`, `duration_minutes`, `calendar_id`
- **save_email_to_drive**: Export emails as files to Drive
  - Parameters: `message_id`, `folder_id`, `file_format` (txt/html)
- **share_drive_file_via_email**: Combine Drive sharing with email notifications
  - Parameters: `file_id`, `recipient_email`, `message`, `subject`, `permission_role`
- **unified_search**: Search across Gmail, Drive, and Calendar simultaneously
  - Parameters: `query`, `search_drive`, `search_gmail`, `search_calendar`, `max_results`

#### Contact Management Tools (4 tools)

- **contacts_search**: Search contacts by name or email
  - Parameters: `query`, `max_results`
- **contacts_list**: List all contacts
  - Parameters: `max_results`
- **contacts_get**: Get detailed contact information
  - Parameters: `resource_name`
- **contacts_resolve_email**: Resolve contact name to email address
  - Parameters: `name_or_email`

#### 🧠 Smart Tools with Contact Resolution (4 tools)

These tools automatically resolve contact names to email addresses, making them much more user-friendly:

- **smart_send_email**: Send email with automatic contact resolution
  - Parameters: `to` (name or email), `subject`, `body`, `cc`, `bcc`
  - Example: `smart_send_email('John Smith', 'Meeting Tomorrow', 'Hi John...')`
- **smart_share_file**: Share file with automatic contact resolution
  - Parameters: `file_id`, `recipient` (name or email), `role`, `send_notification`, `message`
  - Example: `smart_share_file('file123', 'John Smith', 'editor')`
- **smart_create_event**: Create calendar event with automatic attendee resolution
  - Parameters: `summary`, `start_time`, `end_time`, `attendees` (names or emails), `calendar_id`, `description`, `location`
  - Example: `smart_create_event('Team Meeting', '2024-01-15T14:00:00', '2024-01-15T15:00:00', 'John Smith, Jane Doe')`
- **smart_forward_email**: Forward email with automatic contact resolution
  - Parameters: `message_id`, `to` (name or email), `body`
  - Example: `smart_forward_email('msg123', 'John Smith', 'FYI - please review')`

### Example Commands

#### Basic Operations
```
# Check authentication status
What's my Google authentication status?

# List recent files in Google Drive
Show me my recent files in Google Drive

# Search for specific files in shared drives
Find files in my shared drives containing "presentation"

# List available shared drives
Show me all my shared drives

# Send an email
Send an email to john@example.com with subject "Meeting Tomorrow" and body "Hi John, Don't forget about our meeting tomorrow at 2 PM. Best regards!"

# Create a calendar event
Create a calendar event for "Team Meeting" tomorrow from 2:00 PM to 3:00 PM
```

#### Advanced File Management
```
# Copy a file to a different folder
Copy file [file_id] to folder [folder_id] with name "Copy of Document"

# Move files between shared drives
Move file [file_id] to the shared drive folder [folder_id]

# Update file content
Update the content of file [file_id] with new text content

# Share a file with specific permissions
Share file [file_id] with user@example.com as editor with notification

# Create file in shared drive
Create a file called "team-notes.txt" in shared drive [drive_id] with content "Team meeting notes"

# Create folder in shared drive  
Create a folder called "Project Files" in shared drive [drive_id]

# Create Google Docs/Sheets/Slides
Create a Google Doc called "Meeting Notes" with HTML content
Create a Google Sheet called "Budget" with CSV data: Name,Amount\nItem1,100\nItem2,200
Create a Google Slides presentation called "Project Overview"
```

#### Email Workflow
```
# Reply to an email
Reply to message [message_id] with "Thanks for the update! I'll review this."

# Forward an email with context
Forward message [message_id] to team@company.com with additional note "Please review this proposal"

# Send HTML email with formatting
Send an HTML email to client@company.com with rich formatting and embedded images

# Create and manage drafts
Create a draft email to manager@company.com about "Quarterly Report" 
```

#### Calendar Management
```
# Search for specific events
Search my calendar for events containing "standup"

# Duplicate a recurring meeting
Duplicate event [event_id] to next Tuesday at the same time

# Check availability for multiple calendars
Check free/busy time for calendars [cal1,cal2] between 9 AM and 5 PM tomorrow

# Respond to meeting invitations
Accept the meeting invitation for event [event_id]
```

#### 👥 Smart Contact Resolution
```
# Search your contacts
Search my contacts for "spencer"

# Send email using contact names (no need for email addresses!)
Send an email to Spencer Varney about "Project Update" with message "Hi Spencer, the project is on track..."

# Share files using names
Share file [file_id] with Spencer Varney as editor

# Create meetings with attendees by name
Create a team meeting tomorrow at 2 PM with Spencer Varney and John Smith

# The system will automatically:
# - Find matching contacts in your address book
# - Resolve names to email addresses  
# - Handle multiple matches by asking for clarification
# - Work seamlessly with existing Gmail, Drive, and Calendar tools
```

#### Cross-Service Integration
```
# Create meeting from email
Create a calendar meeting from email [message_id] for next Tuesday at 2 PM

# Save important emails to Drive
Save email [message_id] to my Drive folder as an HTML file

# Share files and notify via email
Share Drive file [file_id] with client@company.com and send them a notification email

# Search across all Google services
Search all my Google services for content related to "quarterly budget"
```

## Advanced Configuration

### Custom OAuth2 Scopes

You can add additional Google API scopes by setting the `GOOGLE_ADDITIONAL_SCOPES` environment variable:

```env
GOOGLE_ADDITIONAL_SCOPES=https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/contacts
```

### Custom Redirect URI

If you need to use a different port for the OAuth2 callback:

```env
GOOGLE_REDIRECT_URI=http://localhost:9000
```

Make sure to update the authorized redirect URIs in your Google Cloud Console accordingly.

## Troubleshooting

### MCP Issues

1. **"Failed to spawn: mcp"**: Use full path to `uv` in Claude Desktop config (e.g., `/opt/homebrew/bin/uv`)
2. **"command not found: mcp"**: Run `uv sync` to install dependencies including `mcp[cli]`
3. **"spawn google-mcp-server ENOENT"**: Use `mcp run server.py` instead of direct executable
4. **Server won't start**: Test with `uv run mcp run server.py` first

### Authentication Issues

1. **"Invalid redirect URI"**: Make sure the redirect URI in your `.env` file matches the one configured in Google Cloud Console
2. **"Access blocked"**: Ensure your app is published or add your email to test users
3. **"Invalid client"**: Verify your client ID and secret are correct in the `.env` file

### Permission Issues

1. **"Insufficient permissions"**: The app will request permissions during the OAuth flow. Make sure to grant all requested permissions
2. **"Token expired"**: The server automatically refreshes tokens, but if issues persist, revoke authentication and re-authenticate

### API Errors

1. **"API not enabled"**: Ensure all required APIs are enabled in Google Cloud Console
2. **"Quota exceeded"**: Check your API quotas in Google Cloud Console

### Testing Steps

1. **Test dependencies**: `uv sync`
2. **Test server directly**: `uv run mcp run server.py`
3. **Test authentication**: `uv run python test_cli.py`
4. **Check Claude Desktop logs**: Look for connection errors

### Re-authentication

If you need to re-authenticate (e.g., to grant additional permissions):

```
Revoke my Google authentication
```

Then use any Google service tool to trigger re-authentication.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=google_mcp_server
```

### Code Formatting

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/
```

## Security

- **Local Storage**: Credentials are stored locally in `~/.config/google-mcp-server/`
- **Token Refresh**: Access tokens are automatically refreshed using stored refresh tokens
- **Scope Limitation**: Only request the minimum required scopes for functionality
- **No Server Storage**: No credentials or tokens are sent to external servers

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please open an issue on the GitHub repository.

---

**Note**: This MCP server requires Google API credentials and follows Google's OAuth2 security practices. Never share your client secret or stored tokens.
