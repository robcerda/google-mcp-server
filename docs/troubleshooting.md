# Troubleshooting

Solutions for common issues when setting up and using the Google MCP Server.

## MCP Connection Issues

### "Failed to spawn: mcp"
**Problem**: Claude Desktop can't find the MCP binary.

**Solutions**:
1. Use full path to `uv` in Claude Desktop config:
   ```json
   {
     "mcpServers": {
       "google-services": {
         "command": "/opt/homebrew/bin/uv",
         "args": ["run", "--with", "mcp[cli]", "mcp", "run", "/path/to/server.py"],
         "cwd": "/path/to/google-mcp-server"
       }
     }
   }
   ```

2. Find your `uv` path: `which uv`

3. Ensure dependencies are installed: `uv sync`

### "command not found: mcp"
**Problem**: MCP CLI not installed in the virtual environment.

**Solution**: 
```bash
cd google-mcp-server
uv sync  # This installs mcp[cli] dependency
```

### "spawn google-mcp-server ENOENT"
**Problem**: Incorrect path configuration.

**Solution**: Use `mcp run server.py` instead of trying to run the server directly:
```json
{
  "command": "/path/to/.venv/bin/mcp",
  "args": ["run", "/path/to/server.py"]
}
```

### Server Won't Start
**Problem**: Server fails to initialize.

**Testing Steps**:
1. Test server directly: `uv run mcp run server.py`
2. Check for import errors: `uv run python -c "from google_mcp_server.server import mcp; print('OK')"`
3. Verify environment variables: `cat .env`

## Authentication Issues

### "Invalid redirect URI"
**Problem**: Mismatch between `.env` and Google Cloud Console configuration.

**Solution**: 
1. Check your `.env` file: `GOOGLE_REDIRECT_URI=http://localhost:8080`
2. Verify Google Cloud Console > Credentials > OAuth 2.0 Client IDs > Authorized redirect URIs
3. Ensure both match exactly

### "Access blocked: This app's request is invalid"
**Problem**: OAuth consent screen not properly configured.

**Solutions**:
1. Complete OAuth consent screen setup in Google Cloud Console
2. Add your email to "Test users" if app is in testing mode
3. Ensure all required fields are filled in consent screen

### "Invalid client: no application name"
**Problem**: OAuth consent screen missing required information.

**Solution**: 
1. Go to Google Cloud Console > APIs & Services > OAuth consent screen
2. Fill in "App name" and other required fields
3. Save configuration

### "Token expired" or "Invalid credentials"
**Problem**: Stored credentials are invalid or expired.

**Solutions**:
1. Revoke and re-authenticate:
   ```
   Revoke my Google authentication
   ```
   Then use any Google tool to trigger re-authentication

2. Manually delete token file:
   ```bash
   rm ~/.config/google-mcp-server/token.json
   ```

3. Check system clock synchronization (tokens are time-sensitive)

## API Permission Issues

### "Insufficient permissions" 
**Problem**: Missing required OAuth scopes.

**Solution**:
1. Check current scopes in `auth.py`
2. Add additional scopes if needed:
   ```env
   GOOGLE_ADDITIONAL_SCOPES=https://www.googleapis.com/auth/spreadsheets
   ```
3. Re-authenticate to grant new permissions

### "API not enabled"
**Problem**: Required APIs not enabled in Google Cloud Console.

**Solution**: Enable these APIs in Google Cloud Console > APIs & Services > Library:
- Google Drive API
- Gmail API
- Google Calendar API
- People API

### "Quota exceeded"
**Problem**: API usage limits reached.

**Solutions**:
1. Check quotas in Google Cloud Console > APIs & Services > Quotas
2. Request quota increases if needed
3. Implement rate limiting in your usage

## Contact Resolution Issues

### "No contacts found"
**Problem**: Contact search returns empty results.

**Debugging Steps**:
1. Check API access: `contacts_debug()`
2. Verify contacts exist in Google Contacts: https://contacts.google.com
3. Try different search terms: full name, partial name, email

**Common Causes**:
- Personal Gmail accounts may have limited contacts
- Contacts stored locally on phone but not synced to Google
- Google Workspace directory access requires proper permissions

### "Multiple contacts found"
**Problem**: Contact name matches multiple people.

**Solutions**:
1. Be more specific: "John Smith from Engineering" instead of "John"
2. Use full email address: `john.smith@company.com`
3. Add person to your personal contacts with a unique name

### "Directory search not available"
**Problem**: Can't search company directory.

**Causes**:
- Personal Gmail account (no directory)
- Google Workspace admin restrictions
- Missing directory permissions

**Solutions**:
1. Use personal contacts instead of directory
2. Contact your Google Workspace admin
3. Add colleagues to personal contacts manually

## Email Issues

### "Email failed to send"
**Problem**: Email sending fails after confirmation.

**Debugging**:
1. Check Gmail API quotas
2. Verify recipient email address is valid
3. Check for content that might be flagged as spam

### "HTML email not formatting correctly"
**Problem**: Rich text emails display as plain text.

**Solution**: Use `gmail_send_html_message` instead of `gmail_send_message`:
```
gmail_send_html_message('recipient@example.com', 'Subject', '<h1>HTML Content</h1>', 'Plain text fallback')
```

## Drive Issues

### "File not found" or "Access denied"
**Problem**: Can't access or modify files.

**Causes**:
- File doesn't exist or was deleted
- Insufficient permissions (using `drive.file` scope)
- File is in a shared drive without proper access

**Solutions**:
1. Verify file ID is correct
2. Check file permissions: `drive_get_file_permissions(file_id)`
3. For broader access, add scope: `https://www.googleapis.com/auth/drive`

### "Shared drive access issues"
**Problem**: Can't create files in shared drives.

**Solutions**:
1. List available shared drives: `drive_list_shared_drives()`
2. Use correct `drive_id` parameter
3. Verify you have contributor access to the shared drive

### "Google Docs creation fails"
**Problem**: Can't create Google native formats.

**Solution**: The server automatically handles Google native formats. Ensure you're using:
- `drive_create_google_doc()` for Google Docs
- `drive_create_google_sheet()` for Google Sheets  
- `drive_create_google_slide()` for Google Slides

## Calendar Issues

### "Calendar not found"
**Problem**: Can't access specified calendar.

**Solutions**:
1. List available calendars: `calendar_list_calendars()`
2. Use correct calendar ID (usually email address)
3. Check calendar sharing permissions

### "Event creation fails"
**Problem**: Calendar events fail to create.

**Common Issues**:
- Invalid time format (use ISO 8601: `2024-01-15T14:00:00`)
- Timezone issues (specify timezone in time strings)
- Invalid attendee email addresses

### "Attendee resolution fails"
**Problem**: Can't resolve attendee names to emails.

**Solutions**:
1. Use `contacts_resolve_email()` to test individual names
2. Provide full email addresses instead of names
3. Add attendees to your contacts first

## Environment Issues

### "Module not found" errors
**Problem**: Python can't import required modules.

**Solutions**:
1. Ensure virtual environment is activated: `uv sync`
2. Check Python version: `python --version` (requires 3.12+)
3. Reinstall dependencies: `uv sync --reinstall`

### ".env file not found"
**Problem**: Environment variables not loaded.

**Solution**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### "Permission denied" errors
**Problem**: File system permission issues.

**Solutions**:
1. Check file permissions: `ls -la`
2. Ensure config directory is writable: `chmod 755 ~/.config`
3. Run with appropriate user permissions

## Network Issues

### "Connection timeout" or "Network error"
**Problem**: Can't reach Google APIs.

**Solutions**:
1. Check internet connection
2. Verify firewall settings allow HTTPS traffic
3. Check if corporate proxy is interfering
4. Try different network (mobile hotspot) to isolate network issues

### "SSL/TLS errors"
**Problem**: Certificate verification failures.

**Solutions**:
1. Update system certificates
2. Check system date/time
3. Temporarily disable antivirus SSL scanning
4. Update Python and requests library

## Getting Help

### Enable Debug Logging
Add to your environment:
```env
PYTHONPATH=src python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Then run your problematic command
"
```

### Collect Diagnostic Information
```bash
# Test authentication
contacts_debug()
google_auth_status()

# Test basic functionality
uv run python test_cli.py

# Check server startup
uv run mcp run server.py
```

### Report Issues
When reporting issues, include:
1. Operating system and version
2. Python version: `python --version`
3. uv version: `uv --version`
4. Error messages (full stack trace)
5. Steps to reproduce
6. Your `.env` configuration (without secrets)

Open issues at: https://github.com/robcerda/google-mcp-server/issues