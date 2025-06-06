"""Cross-client integration functions for Google MCP server."""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from email.mime.text import MIMEText
import base64

from .drive_client import GoogleDriveClient
from .gmail_client import GmailClient
from .calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)

class GoogleIntegrationClient:
    """Client for cross-service Google API integrations."""
    
    def __init__(self, drive_client: GoogleDriveClient, 
                 gmail_client: GmailClient, 
                 calendar_client: GoogleCalendarClient):
        """
        Initialize the integration client.
        
        Args:
            drive_client: Google Drive client instance
            gmail_client: Gmail client instance
            calendar_client: Google Calendar client instance
        """
        self.drive_client = drive_client
        self.gmail_client = gmail_client
        self.calendar_client = calendar_client
    
    def create_meeting_from_email(self, message_id: str, 
                                 proposed_time: str = "",
                                 duration_minutes: int = 60,
                                 calendar_id: str = "primary") -> Dict[str, Any]:
        """
        Parse an email and create a calendar event from it.
        
        Args:
            message_id: Gmail message ID to parse
            proposed_time: Proposed meeting time (ISO format, optional)
            duration_minutes: Meeting duration in minutes
            calendar_id: Calendar to create event in
            
        Returns:
            Dictionary containing meeting creation result
        """
        try:
            # Get email content
            email_result = self.gmail_client.get_message(message_id)
            if not email_result.get('success'):
                return email_result
            
            email_data = email_result['message']
            subject = email_data.get('subject', '')
            sender = email_data.get('from', '')
            body = email_data.get('body', {}).get('text', '')
            
            # Extract potential meeting details
            meeting_summary = f"Meeting: {subject}"
            if 'meeting' not in subject.lower():
                meeting_summary = f"Follow-up: {subject}"
            
            # Use proposed time or default to next business day
            if not proposed_time:
                tomorrow = datetime.now() + timedelta(days=1)
                # Set to 2 PM if tomorrow is a weekday
                if tomorrow.weekday() < 5:  # Monday = 0, Sunday = 6
                    meeting_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
                else:
                    # Next Monday if weekend
                    days_ahead = 7 - tomorrow.weekday()
                    meeting_time = tomorrow + timedelta(days=days_ahead)
                    meeting_time = meeting_time.replace(hour=14, minute=0, second=0, microsecond=0)
                
                start_time = meeting_time.isoformat()
                end_time = (meeting_time + timedelta(minutes=duration_minutes)).isoformat()
            else:
                start_time = proposed_time
                proposed_dt = datetime.fromisoformat(proposed_time.replace('Z', '+00:00'))
                end_time = (proposed_dt + timedelta(minutes=duration_minutes)).isoformat()
            
            # Extract email addresses for attendees
            attendees = []
            if sender:
                # Extract email from "Name <email>" format
                email_match = re.search(r'<([^>]+)>', sender)
                if email_match:
                    attendees.append(email_match.group(1))
                else:
                    attendees.append(sender)
            
            # Create calendar event
            event_result = self.calendar_client.create_event(
                calendar_id=calendar_id,
                summary=meeting_summary,
                description=f"Meeting created from email:\n\nOriginal Subject: {subject}\nFrom: {sender}\n\n{body[:500]}...",
                start_time=start_time,
                end_time=end_time,
                attendees=','.join(attendees) if attendees else None
            )
            
            return {
                'success': True,
                'email': {
                    'id': message_id,
                    'subject': subject,
                    'from': sender
                },
                'event': event_result.get('event', {}),
                'message': f"Meeting '{meeting_summary}' created from email"
            }
            
        except Exception as e:
            logger.error(f"Error creating meeting from email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_email_to_drive(self, message_id: str, 
                           folder_id: Optional[str] = None,
                           file_format: str = "txt") -> Dict[str, Any]:
        """
        Save an email as a file in Google Drive.
        
        Args:
            message_id: Gmail message ID to save
            folder_id: Drive folder ID to save in (optional)
            file_format: File format (txt, html)
            
        Returns:
            Dictionary containing save result
        """
        try:
            # Get email content
            email_result = self.gmail_client.get_message(message_id, format='full')
            if not email_result.get('success'):
                return email_result
            
            email_data = email_result['message']
            
            # Format email content
            subject = email_data.get('subject', 'No Subject')
            sender = email_data.get('from', 'Unknown Sender')
            date = email_data.get('date', '')
            body = email_data.get('body', {})
            
            # Create filename
            safe_subject = re.sub(r'[^\w\s-]', '', subject).strip()
            safe_subject = re.sub(r'[-\s]+', '-', safe_subject)
            filename = f"Email_{safe_subject}_{message_id}.{file_format}"
            
            # Format content based on file type
            if file_format.lower() == 'html':
                content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{subject}</title>
    <meta charset="UTF-8">
</head>
<body>
    <h2>{subject}</h2>
    <p><strong>From:</strong> {sender}</p>
    <p><strong>Date:</strong> {date}</p>
    <p><strong>To:</strong> {email_data.get('to', '')}</p>
    <hr>
    <div>
        {body.get('html', body.get('text', 'No content'))}
    </div>
</body>
</html>"""
                mime_type = "text/html"
            else:
                content = f"""Subject: {subject}
From: {sender}
Date: {date}
To: {email_data.get('to', '')}

{'-' * 50}

{body.get('text', body.get('html', 'No content'))}
"""
                mime_type = "text/plain"
            
            # Save to Drive
            drive_result = self.drive_client.create_file(
                name=filename,
                content=content,
                parent_folder_id=folder_id,
                mime_type=mime_type
            )
            
            return {
                'success': True,
                'email': {
                    'id': message_id,
                    'subject': subject
                },
                'file': drive_result.get('file', {}),
                'message': f"Email saved as '{filename}' in Google Drive"
            }
            
        except Exception as e:
            logger.error(f"Error saving email to drive: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def share_drive_file_via_email(self, file_id: str, recipient_email: str,
                                  message: str = "", subject: str = "",
                                  permission_role: str = "reader") -> Dict[str, Any]:
        """
        Share a Drive file and send email notification.
        
        Args:
            file_id: Google Drive file ID to share
            recipient_email: Email address to share with
            message: Email message body
            subject: Email subject (optional)
            permission_role: Drive permission role (reader, writer, commenter)
            
        Returns:
            Dictionary containing sharing and email result
        """
        try:
            # Get file metadata
            file_result = self.drive_client.get_file(file_id)
            if not file_result.get('success'):
                return file_result
            
            file_info = file_result['file']
            file_name = file_info.get('name', 'Untitled')
            
            # Share the file
            share_result = self.drive_client.share_file(
                file_id=file_id,
                email_address=recipient_email,
                role=permission_role,
                send_notification=False  # We'll send our own email
            )
            
            if not share_result.get('success'):
                return share_result
            
            # Prepare email
            if not subject:
                subject = f"Shared file: {file_name}"
            
            email_body = f"""Hello,

I've shared a file with you on Google Drive:

File: {file_name}
Access Level: {permission_role}
Link: {file_info.get('webViewLink', 'Link not available')}

{message}

Best regards
"""
            
            # Send email notification
            email_result = self.gmail_client.send_message(
                to=recipient_email,
                subject=subject,
                body=email_body
            )
            
            return {
                'success': True,
                'file': {
                    'id': file_id,
                    'name': file_name,
                    'webViewLink': file_info.get('webViewLink', '')
                },
                'sharing': share_result.get('permission', {}),
                'email': email_result.get('message', {}),
                'message': f"File '{file_name}' shared with {recipient_email} and email sent"
            }
            
        except Exception as e:
            logger.error(f"Error sharing file via email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def unified_search(self, query: str, search_drive: bool = True,
                      search_gmail: bool = True, search_calendar: bool = True,
                      max_results: int = 5) -> Dict[str, Any]:
        """
        Search across Gmail, Drive, and Calendar with a single query.
        
        Args:
            query: Search query string
            search_drive: Include Drive results
            search_gmail: Include Gmail results  
            search_calendar: Include Calendar results
            max_results: Maximum results per service
            
        Returns:
            Dictionary containing unified search results
        """
        try:
            results = {
                'success': True,
                'query': query,
                'drive': {'files': [], 'totalFiles': 0},
                'gmail': {'messages': [], 'totalMessages': 0},
                'calendar': {'events': [], 'totalEvents': 0}
            }
            
            # Search Drive
            if search_drive:
                drive_result = self.drive_client.search_files(
                    query=query,
                    max_results=max_results
                )
                if drive_result.get('success'):
                    results['drive'] = {
                        'files': drive_result.get('files', []),
                        'totalFiles': drive_result.get('totalFiles', 0)
                    }
            
            # Search Gmail
            if search_gmail:
                gmail_result = self.gmail_client.search_messages(
                    query=query,
                    max_results=max_results
                )
                if gmail_result.get('success'):
                    results['gmail'] = {
                        'messages': gmail_result.get('messages', []),
                        'totalMessages': gmail_result.get('totalMessages', 0)
                    }
            
            # Search Calendar
            if search_calendar:
                calendar_result = self.calendar_client.search_events(
                    query=query,
                    max_results=max_results
                )
                if calendar_result.get('success'):
                    results['calendar'] = {
                        'events': calendar_result.get('events', []),
                        'totalEvents': calendar_result.get('totalEvents', 0)
                    }
            
            # Calculate total results
            total_results = (results['drive']['totalFiles'] + 
                           results['gmail']['totalMessages'] + 
                           results['calendar']['totalEvents'])
            
            results['totalResults'] = total_results
            results['message'] = f"Found {total_results} results across Google services"
            
            return results
            
        except Exception as e:
            logger.error(f"Error in unified search: {e}")
            return {
                'success': False,
                'error': str(e)
            }