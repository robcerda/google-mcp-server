# Usage Examples

Common workflows and advanced usage patterns for the Google MCP Server.

## Smart Contact Resolution Examples

### Basic Email Operations
```
# Send email using contact names (no need for email addresses!)
Send an email to Spencer Varney about "Project Update" with message "Hi Spencer, the project is on track..."

# Send with CC using names
Send an email to Spencer Varney with CC to John Smith about the quarterly report

# Forward email to someone by name
Forward email [message_id] to Spencer Varney with note "FYI - please review this proposal"
```

### File Sharing with Names
```
# Share files using contact names
Share file [file_id] with Spencer Varney as editor

# Share with notification message
Share the Q4 budget spreadsheet with the finance team as viewers with message "Please review by Friday"
```

### Calendar Events with Attendees
```
# Create meetings with attendees by name
Create a team meeting tomorrow at 2 PM with Spencer Varney and John Smith

# Create recurring standup
Create a daily standup at 9 AM Monday through Friday with the engineering team
```

## Safety Workflow Examples

### Safe Email Sending
```
# Step 1: Prepare (shows preview)
prepare_send_email('Spencer Varney', 'Meeting Tomorrow', 'Hi Spencer, don\'t forget about our meeting tomorrow at 2 PM.')

# Returns preview showing:
# 📧 EMAIL READY TO SEND - CONFIRMATION REQUIRED
# To: Spencer Varney (spencer.varney@company.com)
# Subject: Meeting Tomorrow
# Body: Hi Spencer, don't forget about our meeting...
# 
# To proceed: confirm_send_email('spencer.varney@company.com', 'Meeting Tomorrow', 'Hi Spencer...')

# Step 2: Confirm or cancel
confirm_send_email('spencer.varney@company.com', 'Meeting Tomorrow', 'Hi Spencer, don\'t forget about our meeting tomorrow at 2 PM.')
# OR
cancel_operation()
```

### Safe File Sharing
```
# Step 1: Prepare
prepare_share_file('1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms', 'Spencer Varney', 'editor')

# Shows preview with file details and recipient confirmation

# Step 2: Confirm
confirm_share_file('1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms', 'spencer.varney@company.com', 'editor', true)
```

## Google Drive Examples

### Basic File Operations
```
# List recent files
Show me my recent files in Google Drive

# Search for specific files
Find files in my Drive containing "budget"

# Create and share a document
Create a Google Doc called "Meeting Notes" and share it with the team as editors
```

### Shared Drive Operations
```
# List available shared drives
Show me all my shared drives

# Create file in shared drive
Create a file called "team-notes.txt" in shared drive [drive_id] with content "Team meeting notes from today"

# Search within shared drives
Find presentations in our Marketing shared drive
```

### Google Native Format Creation
```
# Create Google Docs with content
Create a Google Doc called "Project Proposal" with HTML content "<h1>Project Overview</h1><p>This project aims to...</p>"

# Create Google Sheets with CSV data
Create a Google Sheet called "Budget Tracker" with data: "Category,Amount\nMarketing,5000\nDevelopment,15000"

# Create Google Slides
Create a Google Slides presentation called "Q4 Results"
```

## Gmail Examples

### Advanced Email Management
```
# Search and organize emails
Find emails from last week about the project review

# Reply to specific emails
Reply to message [message_id] with "Thanks for the update! I'll review this by tomorrow."

# Create and manage drafts
Create a draft email to the board about quarterly results
List my current draft emails

# Manage labels and organization
Archive all emails in my inbox from last month
Add label "Important" to message [message_id]
```

### HTML Email Sending
```
# Send rich formatted emails
Send an HTML email to the marketing team with subject "Campaign Results" including charts and formatting
```

## Calendar Examples

### Event Management
```
# Search calendar events
Search my calendar for events containing "standup" in the next two weeks

# Duplicate recurring meetings
Duplicate event [event_id] to next Tuesday at the same time with title "Weekly Sync - Team B"

# Check availability
Check my free/busy time tomorrow between 9 AM and 5 PM

# Respond to invitations
Accept the meeting invitation for event [event_id]
Decline event [event_id] with response "Conflicting priority meeting"
```

### Calendar Creation and Management
```
# Create specialized calendars
Create a new calendar called "Personal Projects" for tracking side work

# Set custom reminders
Set email reminder 30 minutes before event [event_id] and popup reminder 10 minutes before
```

## Cross-Service Integration Examples

### Email to Calendar Workflow
```
# Create meetings from emails
Create a calendar meeting from email [message_id] scheduled for next Tuesday at 2 PM

# Extract action items from emails
Save important email [message_id] to my Drive folder as "Action Items - Q4 Planning"
```

### File and Email Integration
```
# Share and notify workflow
Share Drive file [file_id] with client@company.com and send them a notification email with project update

# Unified search across services
Search all my Google services for content related to "quarterly budget review"
```

## Advanced Contact Resolution

### Handling Multiple Matches
```
# When searching returns multiple contacts named "John"
contacts_search('john')

# Returns:
# 1. John Smith - john.smith@company.com (Engineering)
# 2. John Doe - john.doe@company.com (Marketing)

# Be more specific in your requests
Send email to John Smith from Engineering about the database optimization

# Or use the full email address
Send email to john.smith@company.com about the database optimization
```

### Directory vs Personal Contacts
```
# Search only personal contacts
contacts_search('spencer')

# Search only company directory (Workspace accounts)
contacts_search_directory('spencer')

# Search both personal and directory
contacts_search_all('spencer')
```

## Troubleshooting Examples

### Authentication Issues
```
# Check authentication status
What's my Google authentication status?

# Re-authenticate if needed
Revoke my Google authentication
# Then use any tool to trigger re-authentication
```

### Contact Resolution Debugging
```
# Debug contact API access
contacts_debug()

# Test contact resolution
contacts_resolve_email('spencer varney')

# Manually resolve if automatic fails
Send email to spencer.varney@company.com about the meeting
```

### Error Recovery
```
# If email fails to send
prepare_send_email('spencer', 'Test', 'Testing email functionality')
# Review the preview and confirm recipient is correct
# Then proceed with confirmation or cancel and try with full email address
```