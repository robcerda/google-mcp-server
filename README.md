# Google MCP Server

A Model Context Protocol (MCP) server that provides Claude with comprehensive access to Google services including Drive, Gmail, and Calendar through OAuth2 authentication with local credential storage.

## Features

- **🔐 Secure OAuth2 Authentication**: Local credential storage with browser-based authentication flow
- **📁 Google Drive Integration**: Upload, download, search, and manage files and folders
- **📧 Gmail Operations**: Send, receive, search, and manage emails
- **📅 Google Calendar**: Create, read, update, and delete calendar events
- **🔑 Custom Scopes**: Configure additional OAuth2 scopes for extended functionality
- **🏠 Local Credential Management**: Keep your API keys and tokens on your local machine

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
      "command": "/opt/homebrew/bin/uv",
      "args": ["run", "mcp", "run", "server.py"],
      "cwd": "/path/to/google-mcp-server"
    }
  }
}
```

**Example with full path:**
```json
{
  "mcpServers": {
    "google-services": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["run", "mcp", "run", "server.py"],
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

### Available Tools

#### Authentication Tools

- **google_auth_status**: Check current authentication status
- **google_auth_revoke**: Revoke authentication and clear stored credentials

#### Google Drive Tools

- **drive_list_files**: List files in Google Drive
  - Parameters: `query` (search term), `folder_id`, `max_results`
- **drive_get_file**: Get file metadata and content
  - Parameters: `file_id`, `include_content`
- **drive_upload_file**: Upload a file to Google Drive
  - Parameters: `name`, `content`, `parent_folder_id`, `mime_type`
- **drive_create_folder**: Create a folder in Google Drive
  - Parameters: `name`, `parent_folder_id`

#### Gmail Tools

- **gmail_list_messages**: List Gmail messages
  - Parameters: `query`, `max_results`, `include_spam_trash`
- **gmail_get_message**: Get a specific Gmail message
  - Parameters: `message_id`, `format`
- **gmail_send_message**: Send a Gmail message
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`

#### Google Calendar Tools

- **calendar_list_calendars**: List available calendars
- **calendar_list_events**: List calendar events
  - Parameters: `calendar_id`, `time_min`, `time_max`, `max_results`
- **calendar_create_event**: Create a calendar event
  - Parameters: `summary`, `start_time`, `end_time`, `description`, `location`, `attendees`

### Example Commands

```
# Check authentication status
What's my Google authentication status?

# List recent files in Google Drive
Show me my recent files in Google Drive

# Search for specific files
Find files in my Google Drive containing "presentation"

# Send an email
Send an email to john@example.com with subject "Meeting Tomorrow" and body "Hi John, Don't forget about our meeting tomorrow at 2 PM. Best regards!"

# Create a calendar event
Create a calendar event for "Team Meeting" tomorrow from 2:00 PM to 3:00 PM

# List upcoming calendar events
Show me my calendar events for the next week
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
