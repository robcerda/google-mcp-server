"""Safe tools that require explicit confirmation before executing actions."""

import logging
from typing import Dict, List, Optional, Any

from .contacts_client import GoogleContactsClient
from .gmail_client import GmailClient
from .drive_client import GoogleDriveClient
from .calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)

class SafeGoogleTools:
    """Safe tools that require explicit confirmation before performing actions."""
    
    def __init__(self, contacts_client: GoogleContactsClient, 
                 gmail_client: GmailClient,
                 drive_client: GoogleDriveClient,
                 calendar_client: GoogleCalendarClient):
        """
        Initialize safe tools with all service clients.
        """
        self.contacts = contacts_client
        self.gmail = gmail_client
        self.drive = drive_client
        self.calendar = calendar_client
    
    def prepare_email(self, to: str, subject: str, body: str, 
                     cc: str = "", bcc: str = "") -> Dict[str, Any]:
        """
        Prepare email for sending - shows what will be sent and requires confirmation.
        
        Args:
            to: Recipient name or email
            subject: Email subject
            body: Email body
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            
        Returns:
            Dictionary with email details for user confirmation
        """
        try:
            # Resolve primary recipient
            to_result = self.contacts.smart_email_resolve(to, "email")
            if not to_result['success']:
                return {
                    'success': False,
                    'error': to_result['message']
                }
            
            resolved_to = to_result['email']
            to_info = to_result.get('message', f"Resolved to {resolved_to}")
            
            # Resolve CC if provided
            resolved_cc = ""
            cc_info = ""
            if cc.strip():
                cc_result = self.contacts.smart_email_resolve(cc, "email") 
                if cc_result['success']:
                    resolved_cc = cc_result['email']
                    cc_info = cc_result.get('message', f"Resolved to {resolved_cc}")
                else:
                    return {
                        'success': False,
                        'error': f"CC recipient issue: {cc_result['message']}"
                    }
            
            # Resolve BCC if provided
            resolved_bcc = ""
            bcc_info = ""
            if bcc.strip():
                bcc_result = self.contacts.smart_email_resolve(bcc, "email")
                if bcc_result['success']:
                    resolved_bcc = bcc_result['email']
                    bcc_info = bcc_result.get('message', f"Resolved to {resolved_bcc}")
                else:
                    return {
                        'success': False,
                        'error': f"BCC recipient issue: {bcc_result['message']}"
                    }
            
            # Return preparation details for confirmation
            email_preview = {
                'action': 'SEND_EMAIL',
                'to': {
                    'original': to,
                    'resolved': resolved_to,
                    'info': to_info
                },
                'subject': subject,
                'body': body,
                'body_preview': body[:200] + "..." if len(body) > 200 else body
            }
            
            if resolved_cc:
                email_preview['cc'] = {
                    'original': cc,
                    'resolved': resolved_cc,
                    'info': cc_info
                }
            
            if resolved_bcc:
                email_preview['bcc'] = {
                    'original': bcc,
                    'resolved': resolved_bcc,
                    'info': bcc_info
                }
            
            return {
                'success': True,
                'requires_confirmation': True,
                'preview': email_preview,
                'message': f"""
📧 EMAIL READY TO SEND - CONFIRMATION REQUIRED

To: {to_info}
Subject: {subject}
Body: {email_preview['body_preview']}
{f"CC: {cc_info}" if resolved_cc else ""}
{f"BCC: {bcc_info}" if resolved_bcc else ""}

⚠️  This email will be sent immediately upon confirmation.
Please use 'confirm_send_email()' to proceed or 'cancel_email()' to abort.
""",
                'confirmation_data': {
                    'to': resolved_to,
                    'subject': subject,
                    'body': body,
                    'cc': resolved_cc if resolved_cc else None,
                    'bcc': resolved_bcc if resolved_bcc else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def prepare_file_share(self, file_id: str, recipient: str, role: str = "reader",
                          send_notification: bool = True, message: str = "") -> Dict[str, Any]:
        """
        Prepare file sharing - shows what will be shared and requires confirmation.
        """
        try:
            # Get file info
            file_info = self.drive.get_file(file_id, include_content=False)
            if not file_info['success']:
                return {
                    'success': False,
                    'error': f"Could not get file info: {file_info['error']}"
                }
            
            file_details = file_info['file']
            
            # Resolve recipient
            recipient_result = self.contacts.smart_email_resolve(recipient, "sharing")
            if not recipient_result['success']:
                return {
                    'success': False,
                    'error': recipient_result['message']
                }
            
            resolved_email = recipient_result['email']
            recipient_info = recipient_result.get('message', f"Resolved to {resolved_email}")
            
            share_preview = {
                'action': 'SHARE_FILE',
                'file': {
                    'name': file_details['name'],
                    'id': file_id,
                    'type': file_details['mimeType'],
                    'size': file_details.get('size', 'Unknown'),
                    'link': file_details.get('webViewLink', '')
                },
                'recipient': {
                    'original': recipient,
                    'resolved': resolved_email,
                    'info': recipient_info
                },
                'permission': role,
                'notification': send_notification,
                'message': message
            }
            
            return {
                'success': True,
                'requires_confirmation': True,
                'preview': share_preview,
                'message': f"""
📁 FILE SHARE READY - CONFIRMATION REQUIRED

File: {file_details['name']} ({file_details.get('size', 'Unknown size')})
Recipient: {recipient_info}
Permission: {role}
Email notification: {'Yes' if send_notification else 'No'}
{f"Message: {message}" if message else ""}

⚠️  This will grant {role} access immediately upon confirmation.
Please use 'confirm_share_file()' to proceed or 'cancel_share()' to abort.
""",
                'confirmation_data': {
                    'file_id': file_id,
                    'recipient_email': resolved_email,
                    'role': role,
                    'send_notification': send_notification,
                    'message': message
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing file share: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def prepare_calendar_event(self, summary: str, start_time: str, end_time: str,
                              attendees: str = "", calendar_id: str = "primary",
                              description: str = "", location: str = "") -> Dict[str, Any]:
        """
        Prepare calendar event creation - shows what will be created and requires confirmation.
        """
        try:
            resolved_attendees = []
            attendee_info = []
            
            if attendees.strip():
                # Resolve attendees
                attendee_result = self.contacts.resolve_attendee_emails(attendees)
                
                if attendee_result['success']:
                    resolved_attendees = attendee_result['resolved_emails']
                    
                    # Handle unresolved attendees
                    if attendee_result['unresolved']:
                        return {
                            'success': False,
                            'error': f"Could not resolve these attendees: {', '.join(attendee_result['unresolved'])}. Please provide email addresses or add them to contacts."
                        }
                    
                    # Handle attendees requiring confirmation
                    if attendee_result['requires_confirmation']:
                        conf_msgs = []
                        for conf in attendee_result['requires_confirmation']:
                            conf_msgs.append(f"'{conf['original_query']}': {conf['message']}")
                        return {
                            'success': False,
                            'error': "Some attendees need clarification:\n" + "\n".join(conf_msgs)
                        }
                    
                    attendee_info = [f"✓ {email}" for email in resolved_attendees]
                else:
                    return {
                        'success': False,
                        'error': f"Error resolving attendees: {attendee_result['error']}"
                    }
            
            event_preview = {
                'action': 'CREATE_CALENDAR_EVENT',
                'summary': summary,
                'start_time': start_time,
                'end_time': end_time,
                'location': location,
                'description': description,
                'calendar_id': calendar_id,
                'attendees': resolved_attendees,
                'attendee_count': len(resolved_attendees)
            }
            
            return {
                'success': True,
                'requires_confirmation': True,
                'preview': event_preview,
                'message': f"""
📅 CALENDAR EVENT READY - CONFIRMATION REQUIRED

Event: {summary}
Time: {start_time} to {end_time}
{f"Location: {location}" if location else ""}
{f"Description: {description}" if description else ""}
Calendar: {calendar_id}
Attendees ({len(resolved_attendees)}):
{chr(10).join(attendee_info) if attendee_info else "  No attendees"}

⚠️  Invitations will be sent to all attendees immediately upon confirmation.
Please use 'confirm_create_event()' to proceed or 'cancel_event()' to abort.
""",
                'confirmation_data': {
                    'summary': summary,
                    'start_time': start_time,
                    'end_time': end_time,
                    'attendees': ",".join(resolved_attendees) if resolved_attendees else None,
                    'calendar_id': calendar_id,
                    'description': description,
                    'location': location
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing calendar event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_send_email(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actually send the email after confirmation.
        """
        try:
            result = self.gmail.send_message(
                to=confirmation_data['to'],
                subject=confirmation_data['subject'],
                body=confirmation_data['body'],
                cc=confirmation_data.get('cc'),
                bcc=confirmation_data.get('bcc')
            )
            
            if result['success']:
                result['message'] = f"✅ Email sent successfully to {confirmation_data['to']}"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_share_file(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actually share the file after confirmation.
        """
        try:
            result = self.drive.share_file(
                file_id=confirmation_data['file_id'],
                email_address=confirmation_data['recipient_email'],
                role=confirmation_data['role'],
                send_notification=confirmation_data['send_notification'],
                message=confirmation_data['message']
            )
            
            if result['success']:
                result['message'] = f"✅ File shared successfully with {confirmation_data['recipient_email']}"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_create_event(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actually create the calendar event after confirmation.
        """
        try:
            result = self.calendar.create_event(
                calendar_id=confirmation_data['calendar_id'],
                summary=confirmation_data['summary'],
                description=confirmation_data.get('description'),
                start_time=confirmation_data['start_time'],
                end_time=confirmation_data['end_time'],
                location=confirmation_data.get('location'),
                attendees=confirmation_data.get('attendees')
            )
            
            if result['success']:
                attendee_count = len(confirmation_data.get('attendees', '').split(',')) if confirmation_data.get('attendees') else 0
                result['message'] = f"✅ Calendar event created successfully with {attendee_count} attendees"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }