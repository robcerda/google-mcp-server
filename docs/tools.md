# All Tools Reference

Complete reference for all 70 tools available in the Google MCP Server.

| Category | Count |
|---|---|
| [Authentication](#authentication-tools-2-tools) | 2 |
| [Google Drive](#google-drive-tools-15-tools) | 15 |
| [Large File Handling](#large-file-handling-tools-6-tools) | 6 |
| [Gmail](#gmail-tools-13-tools) | 13 |
| [Google Calendar](#google-calendar-tools-10-tools) | 10 |
| [Contacts](#contact-management-tools-7-tools) | 7 |
| [Safe Tools (prepare)](#safe-tools-with-contact-resolution-4-tools) | 4 |
| [Confirmation](#confirmation-tools-5-tools) | 5 |
| [Unsafe Tools](#unsafe-tools-4-tools) | 4 |
| [Cross-Service Integration](#cross-service-integration-tools-4-tools) | 4 |

**Note on service account mode**: if you authenticate with a service account
rather than OAuth2, only the Drive and Calendar tools work. Gmail and Contacts
tools require domain-wide delegation. See the
[setup guide](setup.md#choosing-an-authentication-mode).

## Authentication Tools (2 tools)

- **google_auth_status**: Check current authentication status
- **google_auth_revoke**: Revoke authentication and clear stored credentials
  - In service account mode there is no stored token; this reports where the key lives instead

## Google Drive Tools (15 tools)

### Basic Operations
- **drive_list_files**: List files in Google Drive
  - Parameters: `query`, `folder_id`, `max_results`, `drive_id`, `include_team_drives`
- **drive_get_file**: Get file metadata and content
  - Parameters: `file_id`, `include_content`, `max_content_size`
  - Content beyond `max_content_size` (default 1,000,000 characters) is truncated with a notice. For anything larger, see [Large File Handling](#large-file-handling-tools-6-tools).
- **drive_create_file**: Create a file in Google Drive
  - Parameters: `name`, `content`, `parent_folder_id`, `mime_type`, `drive_id`
- **drive_upload_file**: Upload a file to Google Drive
  - Parameters: `name`, `content`, `parent_folder_id`, `mime_type`, `drive_id`
- **drive_create_folder**: Create a folder in Google Drive
  - Parameters: `name`, `parent_folder_id`, `drive_id`

### File Management
- **drive_copy_file**: Copy files within Drive
  - Parameters: `file_id`, `name`, `parent_folder_id`
- **drive_move_file**: Move files between folders
  - Parameters: `file_id`, `new_parent_folder_id`, `remove_from_current_parents`
- **drive_rename_file**: Rename files
  - Parameters: `file_id`, `new_name`
- **drive_update_file_content**: Update existing file content
  - Parameters: `file_id`, `content`, `mime_type`

### Sharing & Permissions
- **drive_get_file_permissions**: View file sharing permissions
  - Parameters: `file_id`
- **drive_share_file**: Share files with users
  - Parameters: `file_id`, `email_address`, `role`, `send_notification`, `message`

### Shared Drive Support
- **drive_list_shared_drives**: List available shared drives to get drive IDs
  - Parameters: `max_results`

**Note**: All Drive functions support both personal and shared drives via `drive_id` parameter.

### Google Native Formats
- **drive_create_google_doc**: Create Google Docs (supports HTML content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`
- **drive_create_google_sheet**: Create Google Sheets (supports CSV content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`
- **drive_create_google_slide**: Create Google Slides (supports HTML content)
  - Parameters: `name`, `content`, `parent_folder_id`, `drive_id`

## Large File Handling Tools (6 tools)

For Drive files too big to read in one pass without blowing the context window.
Start with `analyze_file_structure` - it sizes the file up and tells you which
of the others to reach for.

- **analyze_file_structure**: Inspect a file before processing and recommend a strategy
  - Parameters: `file_id`
  - Reports size, MIME type, detected format (json/csv/xml/text/binary), and processing recommendations
- **drive_get_file_chunked**: Read content one fixed-size chunk at a time
  - Parameters: `file_id`, `chunk_size` (default 50,000 chars), `chunk_number` (0-based)
  - Each response reports the current chunk number and the total, so you can page through
- **get_file_sample**: Pull a representative slice from anywhere in a file
  - Parameters: `file_id`, `sample_size` (default 1,000 chars), `offset`
- **search_in_large_file**: Find a pattern without loading the whole file
  - Parameters: `file_id`, `pattern` (regex supported), `max_results` (default 100)
- **process_large_json**: Handle large JSON with a mode suited to its size
  - Parameters: `file_id`, `processing_mode`
  - Modes: `smart` (default, picks an approach from the file size), `summary` (structure and key overview), `streaming` (chunk-by-chunk), `targeted` (points you at `extract_json_section`)
- **extract_json_section**: Pull one section out without parsing the entire document
  - Parameters: `file_id`, `json_path` (dotted path, e.g. `healthData.workoutData`)

## Gmail Tools (13 tools)

### Basic Operations
- **gmail_list_messages**: List Gmail messages
  - Parameters: `query`, `max_results`, `include_spam_trash`
- **gmail_get_message**: Get a specific Gmail message
  - Parameters: `message_id`, `format`
- **gmail_send_message**: Send a Gmail message
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **gmail_send_html_message**: Send rich HTML emails
  - Parameters: `to`, `subject`, `html_body`, `text_body`, `cc`, `bcc`

### Message Management
- **gmail_reply_to_message**: Reply to emails with proper threading
  - Parameters: `message_id`, `body`, `include_original`
- **gmail_forward_message**: Forward emails
  - Parameters: `message_id`, `to`, `body`
- **gmail_archive_message**: Archive messages
  - Parameters: `message_id`
- **gmail_delete_message**: Move messages to trash
  - Parameters: `message_id`

### Label Management
- **gmail_add_label**: Add labels to messages
  - Parameters: `message_id`, `label_ids` (comma-separated)
- **gmail_remove_label**: Remove labels from messages
  - Parameters: `message_id`, `label_ids` (comma-separated)

### Draft Management
- **gmail_create_draft**: Create draft messages
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **gmail_list_drafts**: List draft messages
  - Parameters: `max_results`

### Bulk Operations
- **gmail_bulk_modify**: ⚠️ Add or remove labels across every message matching a query
  - Parameters: `query`, `add_labels`, `remove_labels`, `max_messages` (default 1000)
  - Executes immediately. Use **prepare_bulk_modify** to see a preview and confirm first.

## Google Calendar Tools (10 tools)

### Basic Operations
- **calendar_list_calendars**: List available calendars
- **calendar_list_events**: List calendar events
  - Parameters: `calendar_id`, `time_min`, `time_max`, `max_results`
- **calendar_create_event**: Create calendar events
  - Parameters: `summary`, `start_time`, `end_time`, `calendar_id`, `description`, `location`, `attendees`
- **calendar_search_events**: Search events by content
  - Parameters: `query`, `calendar_id`, `time_min`, `time_max`, `max_results`

### Event Management
- **calendar_duplicate_event**: Copy events to other dates
  - Parameters: `calendar_id`, `event_id`, `new_start_time`, `new_end_time`, `new_summary`
- **calendar_respond_to_event**: Accept/decline invitations
  - Parameters: `calendar_id`, `event_id`, `response` (accepted/declined/tentative)
- **calendar_set_event_reminders**: Configure event notifications
  - Parameters: `calendar_id`, `event_id`, `reminders` (JSON format)

### Calendar Management
- **calendar_create_calendar**: Create new calendars
  - Parameters: `summary`, `description`, `time_zone`
- **calendar_delete_calendar**: Delete calendars
  - Parameters: `calendar_id`
- **calendar_get_free_busy_info**: Check availability
  - Parameters: `calendar_ids` (comma-separated), `time_min`, `time_max`

## Contact Management Tools (7 tools)

- **contacts_search**: Search contacts by name or email using improved searchContacts API
  - Parameters: `query`, `max_results`
- **contacts_search_directory**: Search organization directory (Google Workspace accounts only)
  - Parameters: `query`, `max_results`
- **contacts_search_all**: Search both personal contacts and directory (comprehensive search)
  - Parameters: `query`, `max_results`
- **contacts_list**: List all contacts
  - Parameters: `max_results`
- **contacts_get**: Get detailed contact information
  - Parameters: `resource_name`
- **contacts_resolve_email**: Resolve contact name to email address
  - Parameters: `name_or_email`
- **contacts_debug**: Debug contacts API connection and permissions

## Safe Tools with Contact Resolution (4 tools)

These tools automatically resolve contact names to email addresses and require explicit confirmation:

- **prepare_send_email**: ✅ SAFE: Prepare email for sending - shows preview and requires confirmation
  - Parameters: `to` (name or email), `subject`, `body`, `cc`, `bcc`
- **prepare_share_file**: ✅ SAFE: Prepare file sharing - shows preview and requires confirmation
  - Parameters: `file_id`, `recipient` (name or email), `role`, `send_notification`, `message`
- **prepare_create_event**: ✅ SAFE: Prepare calendar event - shows preview and requires confirmation
  - Parameters: `summary`, `start_time`, `end_time`, `attendees` (names or emails), `calendar_id`, `description`, `location`
- **prepare_bulk_modify**: ✅ SAFE: Preview a bulk label change before it runs
  - Parameters: `query`, `add_labels`, `remove_labels`, `max_messages`
  - Shows how many messages match and a sample of them

## Confirmation Tools (5 tools)

- **confirm_send_email**: ✅ Confirm and send the prepared email
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **confirm_share_file**: ✅ Confirm and share the prepared file
  - Parameters: `file_id`, `recipient_email`, `role`, `send_notification`, `message`
- **confirm_create_event**: ✅ Confirm and create the prepared calendar event
  - Parameters: `summary`, `start_time`, `end_time`, `attendees`, `calendar_id`, `description`, `location`
- **confirm_bulk_modify**: ✅ Confirm and run the prepared bulk label change
  - Parameters: `query`, `add_labels`, `remove_labels`, `max_messages`
- **cancel_operation**: ❌ Cancel any pending operation

## Unsafe Tools (4 tools)

These tools execute immediately without confirmation (use with caution):

- **smart_send_email_unsafe**: ⚠️ UNSAFE: Send email immediately without confirmation
  - Parameters: `to`, `subject`, `body`, `cc`, `bcc`
- **smart_share_file_unsafe**: ⚠️ UNSAFE: Share file immediately without confirmation
  - Parameters: `file_id`, `recipient`, `role`, `send_notification`, `message`
- **smart_create_event_unsafe**: ⚠️ UNSAFE: Create calendar event immediately without confirmation
  - Parameters: `summary`, `start_time`, `end_time`, `attendees`, `calendar_id`, `description`, `location`
- **smart_forward_email_unsafe**: ⚠️ UNSAFE: Forward email immediately without confirmation
  - Parameters: `message_id`, `to`, `body`

## Cross-Service Integration Tools (4 tools)

- **create_meeting_from_email**: Parse emails to create calendar events
  - Parameters: `message_id`, `proposed_time`, `duration_minutes`, `calendar_id`
- **save_email_to_drive**: Export emails as files to Drive
  - Parameters: `message_id`, `folder_id`, `file_format` (txt/html)
- **share_drive_file_via_email**: Combine Drive sharing with email notifications
  - Parameters: `file_id`, `recipient_email`, `message`, `subject`, `permission_role`
- **unified_search**: Search across Gmail, Drive, and Calendar simultaneously
  - Parameters: `query`, `search_drive`, `search_gmail`, `search_calendar`, `max_results`
