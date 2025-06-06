"""Smart tools that combine contact resolution with other Google services."""

import logging
from typing import Dict, List, Optional, Any

from .contacts_client import GoogleContactsClient
from .gmail_client import GmailClient
from .drive_client import GoogleDriveClient
from .calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)

class SmartGoogleTools:
    """Enhanced tools that use contact resolution for user-friendly interactions."""
    
    def __init__(self, contacts_client: GoogleContactsClient, 
                 gmail_client: GmailClient,
                 drive_client: GoogleDriveClient,
                 calendar_client: GoogleCalendarClient):
        """
        Initialize smart tools with all service clients.
        
        Args:
            contacts_client: Google Contacts client
            gmail_client: Gmail client
            drive_client: Google Drive client  
            calendar_client: Google Calendar client
        """
        self.contacts = contacts_client
        self.gmail = gmail_client
        self.drive = drive_client
        self.calendar = calendar_client
    
    def smart_send_email(self, to: str, subject: str, body: str, 
                        cc: str = "", bcc: str = "") -> Dict[str, Any]:
        """
        Send email with smart contact resolution.
        
        Args:
            to: Recipient name or email
            subject: Email subject
            body: Email body
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            
        Returns:
            Dictionary containing send result
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
            
            # Resolve CC if provided
            resolved_cc = ""
            if cc.strip():
                cc_result = self.contacts.smart_email_resolve(cc, "email") 
                if cc_result['success']:
                    resolved_cc = cc_result['email']
                else:
                    return {
                        'success': False,
                        'error': f"CC recipient issue: {cc_result['message']}"
                    }
            
            # Resolve BCC if provided
            resolved_bcc = ""
            if bcc.strip():
                bcc_result = self.contacts.smart_email_resolve(bcc, "email")
                if bcc_result['success']:
                    resolved_bcc = bcc_result['email']
                else:
                    return {
                        'success': False,
                        'error': f"BCC recipient issue: {bcc_result['message']}"
                    }
            
            # Send the email
            result = self.gmail.send_message(
                to=resolved_to,
                subject=subject,
                body=body,
                cc=resolved_cc if resolved_cc else None,
                bcc=resolved_bcc if resolved_bcc else None
            )
            
            if result['success']:
                result['message'] = f"Email sent to {to_result['message']}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in smart send email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def smart_share_file(self, file_id: str, recipient: str, role: str = "reader",
                        send_notification: bool = True, message: str = "") -> Dict[str, Any]:
        """
        Share a Drive file with smart contact resolution.
        
        Args:
            file_id: Google Drive file ID
            recipient: Recipient name or email
            role: Permission role (reader, writer, commenter)
            send_notification: Send email notification
            message: Optional message
            
        Returns:
            Dictionary containing share result
        """
        try:
            # Resolve recipient
            recipient_result = self.contacts.smart_email_resolve(recipient, "sharing")
            if not recipient_result['success']:
                return {
                    'success': False,
                    'error': recipient_result['message']
                }
            
            resolved_email = recipient_result['email']
            
            # Share the file
            result = self.drive.share_file(
                file_id=file_id,
                email_address=resolved_email,
                role=role,
                send_notification=send_notification,
                message=message
            )
            
            if result['success']:
                result['message'] = f"File shared with {recipient_result['message']}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in smart share file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def smart_create_event(self, summary: str, start_time: str, end_time: str,
                          attendees: str = "", calendar_id: str = "primary",
                          description: str = "", location: str = "") -> Dict[str, Any]:
        """
        Create calendar event with smart attendee resolution.
        
        Args:
            summary: Event title
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            attendees: Comma-separated list of attendee names/emails
            calendar_id: Calendar ID
            description: Event description
            location: Event location
            
        Returns:
            Dictionary containing event creation result
        """
        try:
            resolved_attendees = ""
            attendee_messages = []
            
            if attendees.strip():
                # Resolve attendees
                attendee_result = self.contacts.resolve_attendee_emails(attendees)
                
                if attendee_result['success']:
                    all_emails = attendee_result['resolved_emails']
                    
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
                    
                    resolved_attendees = ",".join(all_emails)
                    attendee_messages.append(f"Resolved {len(all_emails)} attendees")
                else:
                    return {
                        'success': False,
                        'error': f"Error resolving attendees: {attendee_result['error']}"
                    }
            
            # Create the event
            result = self.calendar.create_event(
                calendar_id=calendar_id,
                summary=summary,
                description=description,
                start_time=start_time,
                end_time=end_time,
                location=location,
                attendees=resolved_attendees if resolved_attendees else None
            )
            
            if result['success'] and attendee_messages:
                result['message'] = f"{result.get('message', 'Event created')}. {'. '.join(attendee_messages)}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in smart create event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def smart_forward_email(self, message_id: str, to: str, body: str = "") -> Dict[str, Any]:
        """
        Forward email with smart contact resolution.
        
        Args:
            message_id: Gmail message ID to forward
            to: Recipient name or email
            body: Additional message body
            
        Returns:
            Dictionary containing forward result
        """
        try:
            # Resolve recipient
            to_result = self.contacts.smart_email_resolve(to, "email")
            if not to_result['success']:
                return {
                    'success': False,
                    'error': to_result['message']
                }
            
            resolved_to = to_result['email']
            
            # Forward the email
            result = self.gmail.forward_message(
                message_id=message_id,
                to=resolved_to,
                body=body
            )
            
            if result['success']:
                result['message'] = f"Email forwarded to {to_result['message']}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error in smart forward email: {e}")
            return {
                'success': False,
                'error': str(e)
            }