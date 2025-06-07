# Complete Setup Guide

This guide walks you through setting up the Google MCP Server with detailed Google Cloud Console configuration.

## Prerequisites

- Python 3.12 or higher
- `uv` for dependency management
- A Google account
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

## First Run Authentication

When you first use the server, it will automatically launch your browser for OAuth2 authentication:

1. The server will open your default browser
2. Sign in to your Google account
3. Grant the requested permissions
4. The browser will redirect to a success page
5. Return to Claude - you're now authenticated!

Your credentials will be securely stored locally in `~/.config/google-mcp-server/token.json`.

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

## Security

- **Local Storage**: Credentials are stored locally in `~/.config/google-mcp-server/`
- **Token Refresh**: Access tokens are automatically refreshed using stored refresh tokens
- **Scope Limitation**: Only request the minimum required scopes for functionality
- **No Server Storage**: No credentials or tokens are sent to external servers