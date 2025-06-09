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
            
            # Create the confirmation command for Claude to use
            confirm_command = f"confirm_send_email('{resolved_to}', '{subject}', '{body}'"
            if resolved_cc:
                confirm_command += f", cc='{resolved_cc}'"
            if resolved_bcc:
                confirm_command += f", bcc='{resolved_bcc}'"
            confirm_command += ")"
            
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

To proceed: {confirm_command}
To cancel: cancel_operation()
""",
                'confirmation_params': {
                    'to': resolved_to,
                    'subject': subject,
                    'body': body,
                    'cc': resolved_cc,
                    'bcc': resolved_bcc
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
            
            # Create the confirmation command
            confirm_command = f"confirm_share_file('{file_id}', '{resolved_email}', '{role}', {send_notification}"
            if message:
                confirm_command += f", '{message}'"
            confirm_command += ")"
            
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

To proceed: {confirm_command}
To cancel: cancel_operation()
""",
                'confirmation_params': {
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
            
            # Create the confirmation command
            attendee_str = ",".join(resolved_attendees) if resolved_attendees else ""
            confirm_command = f"confirm_create_event('{summary}', '{start_time}', '{end_time}'"
            if attendee_str:
                confirm_command += f", attendees='{attendee_str}'"
            if calendar_id != "primary":
                confirm_command += f", calendar_id='{calendar_id}'"
            if description:
                confirm_command += f", description='{description}'"
            if location:
                confirm_command += f", location='{location}'"
            confirm_command += ")"
            
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

To proceed: {confirm_command}
To cancel: cancel_operation()
""",
                'confirmation_params': {
                    'summary': summary,
                    'start_time': start_time,
                    'end_time': end_time,
                    'attendees': attendee_str,
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
    
    def prepare_bulk_modify(self, query: str, add_labels: str = "", remove_labels: str = "", max_messages: int = 1000) -> Dict[str, Any]:
        """
        Prepare bulk email operations - shows what will be affected and requires confirmation.
        
        Args:
            query: Gmail search query to select messages
            add_labels: Comma-separated label IDs to add
            remove_labels: Comma-separated label IDs to remove
            max_messages: Maximum number of messages to process
            
        Returns:
            Dictionary with operation details for user confirmation
        """
        try:
            if not query.strip():
                return {
                    'success': False,
                    'error': 'Query is required for bulk operations'
                }
                
            # Parse labels
            add_list = [label.strip() for label in add_labels.split(',') if label.strip()] if add_labels else []
            remove_list = [label.strip() for label in remove_labels.split(',') if label.strip()] if remove_labels else []
            
            if not add_list and not remove_list:
                return {
                    'success': False,
                    'error': 'At least one of add_labels or remove_labels must be specified'
                }
            
            # Get count of messages that would be affected (but don't process them yet)
            search_result = self.gmail.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(max_messages, 100)  # Get first 100 for preview
            ).execute()
            
            messages = search_result.get('messages', [])
            total_estimate = search_result.get('resultSizeEstimate', 0)
            
            if not messages:
                return {
                    'success': True,
                    'message': f'No messages found matching query: "{query}"',
                    'affected_count': 0
                }
            
            # Get sample message details for preview
            sample_messages = []
            for i, msg in enumerate(messages[:5]):  # Show first 5 as preview
                try:
                    message_details = self.gmail.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    headers = {h['name']: h['value'] for h in message_details['payload'].get('headers', [])}
                    sample_messages.append({
                        'from': headers.get('From', 'Unknown'),
                        'subject': headers.get('Subject', 'No Subject'),
                        'date': headers.get('Date', 'Unknown'),
                        'snippet': message_details.get('snippet', '')[:100] + '...'
                    })
                except Exception:
                    continue
            
            # Create operation description
            operations_desc = []
            if add_list:
                operations_desc.append(f"ADD labels: {', '.join(add_list)}")
            if remove_list:
                operations_desc.append(f"REMOVE labels: {', '.join(remove_list)}")
            
            operation_summary = " and ".join(operations_desc)
            
            # Create confirmation command
            confirm_command = f"confirm_bulk_modify('{query}'"
            if add_labels:
                confirm_command += f", add_labels='{add_labels}'"
            if remove_labels:
                confirm_command += f", remove_labels='{remove_labels}'"
            if max_messages != 1000:
                confirm_command += f", max_messages={max_messages}"
            confirm_command += ")"
            
            # Calculate if this will hit all messages or be limited
            will_be_limited = total_estimate > max_messages
            actual_count = min(total_estimate, max_messages)
            
            bulk_preview = {
                'action': 'BULK_MODIFY_EMAILS',
                'query': query,
                'total_found': total_estimate,
                'will_process': actual_count,
                'limited': will_be_limited,
                'operations': {
                    'add_labels': add_list,
                    'remove_labels': remove_list
                },
                'sample_messages': sample_messages
            }
            
            return {
                'success': True,
                'requires_confirmation': True,
                'preview': bulk_preview,
                'message': f"""
⚠️  BULK EMAIL OPERATION - CONFIRMATION REQUIRED

Query: "{query}"
Found: {total_estimate} messages
Will process: {actual_count} messages{'(limited by max_messages)' if will_be_limited else ''}

Operations: {operation_summary}

Sample messages that will be affected:
{chr(10).join([f"  • {msg['from']}: {msg['subject']}" for msg in sample_messages[:3]])}
{f"  ... and {len(sample_messages) - 3} more shown in preview" if len(sample_messages) > 3 else ""}
{f"  ... and {actual_count - len(sample_messages)} more will be processed" if actual_count > len(sample_messages) else ""}

🚨 This operation will modify {actual_count} emails immediately upon confirmation.
   This action cannot be easily undone for large numbers of messages.

To proceed: {confirm_command}
To cancel: cancel_operation()
""",
                'confirmation_params': {
                    'query': query,
                    'add_labels': add_labels,
                    'remove_labels': remove_labels,
                    'max_messages': max_messages
                }
            }
            
        except Exception as e:
            logger.error(f"Error preparing bulk modify: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def confirm_bulk_modify(self, confirmation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actually execute the bulk email operation after confirmation.
        """
        try:
            # Parse labels for bulk_modify call
            add_list = [label.strip() for label in confirmation_data.get('add_labels', '').split(',') if label.strip()] if confirmation_data.get('add_labels') else None
            remove_list = [label.strip() for label in confirmation_data.get('remove_labels', '').split(',') if label.strip()] if confirmation_data.get('remove_labels') else None
            
            result = self.gmail.bulk_modify(
                query=confirmation_data['query'],
                add_labels=add_list,
                remove_labels=remove_list,
                max_messages=confirmation_data.get('max_messages', 1000)
            )
            
            if result['success']:
                operations = []
                if add_list:
                    operations.append(f"added labels {add_list}")
                if remove_list:
                    operations.append(f"removed labels {remove_list}")
                operation_desc = " and ".join(operations)
                
                result['message'] = f"✅ Bulk operation completed: {operation_desc} for {result.get('processed', 0)} messages"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }