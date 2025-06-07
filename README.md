# Google MCP Server

> Connect Claude to your Google Workspace with intelligent contact resolution and secure OAuth2 authentication

Transform Claude into your Google productivity assistant. Send emails to "John Smith" instead of john.smith@company.com, share files by name, and create calendar events with automatic attendee resolution.

## ✨ Key Features

- **🧠 Smart Contact Resolution**: `send email to Spencer Varney about the meeting` → automatically finds spencer.varney@company.com
- **🔒 Secure by Default**: Uses [restricted scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) compatible with [Google Advanced Protection](https://landing.google.com/advancedprotection/)
- **📱 50+ Tools**: Complete Gmail, Drive, Calendar integration with shared drive support
- **⚡ Safety First**: All send/share operations require explicit confirmation

## 🚀 Quick Start

### 1. Install
```bash
git clone https://github.com/robcerda/google-mcp-server
cd google-mcp-server
uv sync
```

### 2. Configure Google
1. [Create a Google Cloud project](https://console.cloud.google.com) and enable APIs (Drive, Gmail, Calendar, People)
2. Create OAuth2 credentials (Desktop application type)  
3. Copy your credentials to `.env`:
```bash
cp .env.example .env
# Edit .env with your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
```

### 3. Add to Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "google-services": {
      "command": "/path/to/google-mcp-server/.venv/bin/mcp",
      "args": ["run", "/path/to/google-mcp-server/server.py"]
    }
  }
}
```

## 💡 Examples

**Smart Email** (resolves contacts automatically):
```
Send an email to Spencer Varney about tomorrow's meeting
```

**Safe File Sharing** (shows preview, requires confirmation):
```
Share the Q4 report with the marketing team as editors
```

**Calendar with Attendees** (resolves multiple contacts):
```
Create a meeting tomorrow 2-3pm with Spencer, John, and Sarah
```

## 🔐 Security & Scopes

**Default Scopes** (Advanced Protection compatible):
- `drive.file` - Access only files created by this app
- `gmail.send` + `gmail.readonly` - Send emails and read (no modify)
- `contacts.readonly` - Read contacts for name resolution
- `calendar` - Full calendar access (Google doesn't offer restricted scopes)

**Custom Scopes**: Add any additional scopes via `GOOGLE_ADDITIONAL_SCOPES` environment variable.

## 📚 Documentation

- **[Complete Setup Guide](docs/setup.md)** - Detailed Google Cloud Console configuration
- **[All Tools Reference](docs/tools.md)** - Complete list of 50+ available tools
- **[Usage Examples](docs/examples.md)** - Common workflows and advanced usage
- **[Troubleshooting](docs/troubleshooting.md)** - Solutions for common issues

## 🛡️ Safety Features

All potentially dangerous operations use a **two-step confirmation process**:

1. **Prepare**: `prepare_send_email()` → Shows preview, resolves contacts
2. **Confirm**: `confirm_send_email()` → Actually sends after your approval

No emails, file shares, or calendar invites are sent without explicit confirmation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Questions?** Check the [documentation](docs/) or [open an issue](https://github.com/robcerda/google-mcp-server/issues).