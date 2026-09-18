# Complete Setup Guide

This guide walks you through setting up the Google MCP Server with detailed Google Cloud Console configuration.

## Prerequisites

- Python 3.12 or higher
- `uv` for dependency management
- A Google account
- Claude Desktop or MCP-compatible client

## Choosing an Authentication Mode

The server supports two ways to authenticate. Pick one before you start.

| | **OAuth2** (default) | **Service Account** |
|---|---|---|
| Acts as | You | Its own robot identity |
| Setup | Browser consent screen, once | Drop a key file in place |
| Services | Drive, Gmail, Calendar, Contacts | Calendar and Drive only |
| Data it can see | Everything your account can | Only what you share with it |
| Needs a browser | Yes | No |
| Works under [Advanced Protection](https://landing.google.com/advancedprotection/) | No | Yes |

**Use OAuth2** unless you have a reason not to - it is the full-featured path and
gets you Gmail and contact resolution.

**Use a service account** if the consent screen is blocked for you (Advanced
Protection enrollment does this), or if you are running the server somewhere
without a browser, such as a remote VM. The trade-off is Gmail and Contacts:
reading a human's mailbox or address book as a service account requires
domain-wide delegation, which only a Google Workspace admin can grant. A
personal Gmail account cannot, so those tools will not work in this mode.

The server picks the mode automatically: if a service account key file is
present it is used, otherwise the OAuth2 flow runs.

If you need Gmail or Contacts on a machine with no browser, there is a third
path: OAuth2 completed manually, see
[Headless and Remote Machines](#headless-and-remote-machines).

## Option A: OAuth2 Setup (Google Cloud Console)

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

## Option B: Service Account Setup

No consent screen and no browser - the key signs a JWT directly, which is why
this path works under Advanced Protection.

### Step 1: Create the Service Account

1. In the [Google Cloud Console](https://console.cloud.google.com/), go to
   "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Give it a name (e.g. "google-mcp-server") and click "Create and Continue"
4. Skip the optional role and user grants - the service account needs no
   project roles, only the shares you grant it in Step 4
5. Click "Done"

### Step 2: Enable the APIs

On the *same project as the service account*, go to "APIs & Services" >
"Library" and enable:

- **Google Calendar API**
- **Google Drive API**

Gmail and People APIs are not used in this mode, so there is no need to enable
them.

### Step 3: Download and Install the Key

1. Click into the service account, open the "Keys" tab
2. "Add Key" > "Create new key" > **JSON** > "Create"
3. A `.json` file downloads - this is the only copy, Google will not show it again
4. Move it into place:

```bash
mkdir -p ~/.config/google-mcp-server
mv ~/Downloads/your-project-abc123.json ~/.config/google-mcp-server/service-account.json
chmod 600 ~/.config/google-mcp-server/service-account.json
```

To keep it somewhere else, point `GOOGLE_SERVICE_ACCOUNT_JSON` at it instead:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=/secure/path/to/key.json
```

`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not required in this mode.

### Step 4: Share Your Data With It

This is the step people miss. A service account is **its own identity** with its
own empty Drive and empty calendar. It cannot see your files or events until you
share them, exactly as you would share with a coworker.

Open the key file and copy the `client_email` value - it looks like
`google-mcp-server@your-project.iam.gserviceaccount.com`. Then:

**Calendar**: Google Calendar > hover your calendar > "Settings and sharing" >
"Share with specific people or groups" > "Add people" > paste the
`client_email`. For the server to create and edit events, choose
"Make changes to events".

**Drive**: right-click the folder or file > "Share" > paste the `client_email` >
pick "Viewer" or "Editor". Sharing a folder covers everything inside it.

Anything you do not share stays invisible to the server. That is the security
model - it is a narrower blast radius than OAuth2, not a wider one.

### Step 5: Verify

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from google_mcp_server.auth import GoogleAuthManager
m = GoogleAuthManager()
print('service account mode:', m.use_service_account)
print(m.get_user_info())
"
```

You should see `service account mode: True` and the service account's email. In
Claude, `google_auth_status` reports the same thing.

### Service Account Notes

- **Files the server creates are owned by the service account**, not by you. To
  keep ownership yourself, have it create files inside a folder you shared with
  it as Editor, or share the result back to your own address afterwards.
- **Service account keys do not expire.** `google_auth_revoke` has no token to
  clear in this mode; to cut off access, delete the key in the Cloud Console or
  remove the local file.
- **Gmail and contact tools will fail** in this mode. See the mode comparison
  above for why.

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

*Using a service account? `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are not
required - skip to the Claude Desktop config below.*

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

**Service account mode**: nothing happens on first run - the key authenticates
silently. If a tool reports it cannot find a calendar or file, revisit Step 4
above and confirm you shared it with the `client_email`.

**OAuth2 mode**: the server will automatically launch your browser for authentication:

1. The server will open your default browser
2. Sign in to your Google account
3. Grant the requested permissions
4. The browser will redirect to a success page
5. Return to Claude - you're now authenticated!

Your credentials will be securely stored locally in `~/.config/google-mcp-server/token.json`.

## Headless and Remote Machines

The OAuth2 flow above opens a browser and waits on `http://localhost:8080`. On a
remote VM, in a container, or over plain SSH there is no browser to open and no
way to reach that port, so it never completes.

Two ways around it, in order of preference:

**1. Use a service account** ([Option B](#option-b-service-account-setup)). No
browser is involved at any point. This is the better answer if Calendar and
Drive are all you need.

**2. Use `auth_setup.py`** if you need Gmail or Contacts, which service accounts
cannot reach. It splits the flow in two - it prints a URL you open on any machine
that *does* have a browser, then takes the redirect back from you:

```bash
python auth_setup.py
```

Approve the request in your browser. It will redirect to `http://localhost:8080`
and show a connection error - that is expected, nothing is listening there. Copy
the **entire URL** out of the address bar, including the `state` and `code`
parameters, and paste it back at the prompt. The token is written to
`~/.config/google-mcp-server/token.json`, exactly where the server reads it from.

```bash
python auth_setup.py --status   # check whether the stored token works
python auth_setup.py --force    # re-authenticate, replacing the token
```

The authorization code is single-use and expires within minutes. If the exchange
fails, just run the script again for a fresh URL.

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