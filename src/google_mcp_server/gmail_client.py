"""Gmail API client for MCP server."""

import base64
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
import email
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailClient:
    """Client for Gmail API operations."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize the Gmail client.
        
        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = build('gmail', 'v1', credentials=credentials)
        
    def list_messages(self, query: Optional[str] = None,
                      max_results: int = 10,
                      include_spam_trash: bool = False) -> Dict[str, Any]:
        """
        List Gmail messages.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            include_spam_trash: Include spam and trash folders
            
        Returns:
            Dictionary containing message list
        """
        try:
            # Execute search
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results,
                includeSpamTrash=include_spam_trash
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get basic info for each message
            message_list = []
            for msg in messages:
                try:
                    # Get message metadata
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'To', 'Subject', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = {}
                    for header in message['payload'].get('headers', []):
                        headers[header['name']] = header['value']
                    
                    message_info = {
                        'id': message['id'],
                        'threadId': message['threadId'],
                        'labelIds': message.get('labelIds', []),
                        'snippet': message.get('snippet', ''),
                        'from': headers.get('From', ''),
                        'to': headers.get('To', ''),
                        'subject': headers.get('Subject', ''),
                        'date': headers.get('Date', ''),
                        'internalDate': message.get('internalDate', ''),
                        'unread': 'UNREAD' in message.get('labelIds', [])
                    }
                    message_list.append(message_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting message {msg['id']}: {e}")
                    continue
            
            return {
                'success': True,
                'messages': message_list,
                'totalMessages': len(message_list),
                'query': query or 'all messages',
                'resultSizeEstimate': results.get('resultSizeEstimate', 0)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing messages: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_message(self, message_id: str, format: str = 'full') -> Dict[str, Any]:
        """
        Get a specific Gmail message.
        
        Args:
            message_id: Gmail message ID
            format: Message format (minimal, raw, full, metadata)
            
        Returns:
            Dictionary containing message details
        """
        try:
            # Get message
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            
            # Extract headers
            headers = {}
            if 'payload' in message and 'headers' in message['payload']:
                for header in message['payload']['headers']:
                    headers[header['name']] = header['value']
            
            result = {
                'success': True,
                'message': {
                    'id': message['id'],
                    'threadId': message['threadId'],
                    'labelIds': message.get('labelIds', []),
                    'snippet': message.get('snippet', ''),
                    'historyId': message.get('historyId', ''),
                    'internalDate': message.get('internalDate', ''),
                    'headers': headers,
                    'unread': 'UNREAD' in message.get('labelIds', [])
                }
            }
            
            # Extract body based on format
            if format in ['full', 'raw']:
                body = self._extract_message_body(message)
                result['message']['body'] = body
            
            return result
            
        except HttpError as e:
            logger.error(f"HTTP error getting message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_message_body(self, message: Dict) -> Dict[str, str]:
        """
        Extract message body from Gmail message payload.
        
        Args:
            message: Gmail message object
            
        Returns:
            Dictionary with text and/or html body
        """
        body = {'text': '', 'html': ''}
        
        def extract_parts(parts):
            for part in parts:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body['text'] += base64.urlsafe_b64decode(data).decode('utf-8')
                        
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body['html'] += base64.urlsafe_b64decode(data).decode('utf-8')
                        
                elif 'parts' in part:
                    extract_parts(part['parts'])
        
        payload = message.get('payload', {})
        
        # Single part message
        if 'parts' not in payload:
            mime_type = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data', '')
            
            if data:
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                if mime_type == 'text/plain':
                    body['text'] = decoded_data
                elif mime_type == 'text/html':
                    body['html'] = decoded_data
                else:
                    body['text'] = decoded_data
        else:
            # Multi-part message
            extract_parts(payload['parts'])
        
        return body
    
    def send_message(self, to: str, subject: str, body: str,
                     cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a Gmail message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC email addresses (comma-separated)
            bcc: BCC email addresses (comma-separated)
            
        Returns:
            Dictionary containing send result
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'message': {
                    'id': sent_message['id'],
                    'threadId': sent_message['threadId'],
                    'labelIds': sent_message.get('labelIds', [])
                },
                'result': f"Message sent successfully to {to}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error sending message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_messages(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search Gmail messages.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            Dictionary containing search results
        """
        return self.list_messages(query=query, max_results=max_results)
    
    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing result
        """
        try:
            # Remove UNREAD label
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                'success': True,
                'message': f"Message {message_id} marked as read"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error marking message as read: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as unread.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing result
        """
        try:
            # Add UNREAD label
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                'success': True,
                'message': f"Message {message_id} marked as unread"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error marking message as unread: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error marking message as unread: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_labels(self) -> Dict[str, Any]:
        """
        Get Gmail labels.
        
        Returns:
            Dictionary containing labels
        """
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            formatted_labels = []
            for label in labels:
                formatted_label = {
                    'id': label['id'],
                    'name': label['name'],
                    'type': label['type'],
                    'messagesTotal': label.get('messagesTotal', 0),
                    'messagesUnread': label.get('messagesUnread', 0),
                    'threadsTotal': label.get('threadsTotal', 0),
                    'threadsUnread': label.get('threadsUnread', 0)
                }
                formatted_labels.append(formatted_label)
            
            return {
                'success': True,
                'labels': formatted_labels,
                'totalLabels': len(formatted_labels)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error getting labels: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting labels: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def reply_to_message(self, message_id: str, body: str, 
                        include_original: bool = True) -> Dict[str, Any]:
        """
        Reply to a Gmail message.
        
        Args:
            message_id: Original message ID to reply to
            body: Reply body text
            include_original: Include original message in reply
            
        Returns:
            Dictionary containing reply result
        """
        try:
            # Get original message
            original_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata',
                metadataHeaders=['Message-ID', 'Subject', 'From', 'To', 'References', 'In-Reply-To']
            ).execute()
            
            headers = {h['name']: h['value'] for h in original_message['payload']['headers']}
            
            # Create reply message
            reply = MIMEText(body)
            reply['to'] = headers.get('From', '')
            reply['subject'] = f"Re: {headers.get('Subject', '').replace('Re: ', '')}"
            reply['in-reply-to'] = headers.get('Message-ID', '')
            reply['references'] = f"{headers.get('References', '')} {headers.get('Message-ID', '')}".strip()
            
            # Encode and send
            raw_reply = base64.urlsafe_b64encode(reply.as_bytes()).decode()
            
            sent_reply = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_reply, 'threadId': original_message['threadId']}
            ).execute()
            
            return {
                'success': True,
                'message': {
                    'id': sent_reply['id'],
                    'threadId': sent_reply['threadId']
                },
                'result': f"Reply sent successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error replying to message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error replying to message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def forward_message(self, message_id: str, to: str, body: str = "") -> Dict[str, Any]:
        """
        Forward a Gmail message.
        
        Args:
            message_id: Message ID to forward
            to: Recipient email address
            body: Additional message body
            
        Returns:
            Dictionary containing forward result
        """
        try:
            # Get original message
            original_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in original_message['payload']['headers']}
            original_body = self._extract_message_body(original_message)
            
            # Create forward message
            forward_text = f"{body}\n\n---------- Forwarded message ---------\n"
            forward_text += f"From: {headers.get('From', '')}\n"
            forward_text += f"Date: {headers.get('Date', '')}\n"
            forward_text += f"Subject: {headers.get('Subject', '')}\n"
            forward_text += f"To: {headers.get('To', '')}\n\n"
            forward_text += original_body.get('text', original_body.get('html', ''))
            
            forward = MIMEText(forward_text)
            forward['to'] = to
            forward['subject'] = f"Fwd: {headers.get('Subject', '')}"
            
            # Encode and send
            raw_forward = base64.urlsafe_b64encode(forward.as_bytes()).decode()
            
            sent_forward = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_forward}
            ).execute()
            
            return {
                'success': True,
                'message': {
                    'id': sent_forward['id'],
                    'threadId': sent_forward['threadId']
                },
                'result': f"Message forwarded successfully to {to}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error forwarding message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_html_message(self, to: str, subject: str, html_body: str,
                         text_body: str = "", cc: Optional[str] = None, 
                         bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an HTML Gmail message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback body
            cc: CC email addresses (comma-separated)
            bcc: BCC email addresses (comma-separated)
            
        Returns:
            Dictionary containing send result
        """
        try:
            # Create multipart message
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Add text and HTML parts
            if text_body:
                text_part = MIMEText(text_body, 'plain')
                message.attach(text_part)
            
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'message': {
                    'id': sent_message['id'],
                    'threadId': sent_message['threadId']
                },
                'result': f"HTML message sent successfully to {to}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error sending HTML message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error sending HTML message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def archive_message(self, message_id: str) -> Dict[str, Any]:
        """
        Archive a Gmail message.
        
        Args:
            message_id: Gmail message ID to archive
            
        Returns:
            Dictionary containing archive result
        """
        try:
            # Remove INBOX label to archive
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            
            return {
                'success': True,
                'message': f"Message {message_id} archived successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error archiving message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error archiving message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_message(self, message_id: str) -> Dict[str, Any]:
        """
        Delete a Gmail message (move to trash).
        
        Args:
            message_id: Gmail message ID to delete
            
        Returns:
            Dictionary containing delete result
        """
        try:
            # Move to trash
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            
            return {
                'success': True,
                'message': f"Message {message_id} moved to trash successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error deleting message: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_label(self, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
        """
        Add labels to a Gmail message.
        
        Args:
            message_id: Gmail message ID
            label_ids: List of label IDs to add
            
        Returns:
            Dictionary containing result
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()
            
            return {
                'success': True,
                'message': f"Labels {label_ids} added to message {message_id}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error adding labels: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error adding labels: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def remove_label(self, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
        """
        Remove labels from a Gmail message.
        
        Args:
            message_id: Gmail message ID
            label_ids: List of label IDs to remove
            
        Returns:
            Dictionary containing result
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': label_ids}
            ).execute()
            
            return {
                'success': True,
                'message': f"Labels {label_ids} removed from message {message_id}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error removing labels: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error removing labels: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_draft(self, to: str, subject: str, body: str,
                    cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Gmail draft.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC email addresses (comma-separated)
            bcc: BCC email addresses (comma-separated)
            
        Returns:
            Dictionary containing draft creation result
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {
                'success': True,
                'draft': {
                    'id': draft['id'],
                    'message': {
                        'id': draft['message']['id'],
                        'threadId': draft['message']['threadId']
                    }
                },
                'result': f"Draft created successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error creating draft: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_drafts(self, max_results: int = 10) -> Dict[str, Any]:
        """
        List Gmail drafts.
        
        Args:
            max_results: Maximum number of drafts to return
            
        Returns:
            Dictionary containing drafts list
        """
        try:
            results = self.service.users().drafts().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            drafts = results.get('drafts', [])
            
            formatted_drafts = []
            for draft in drafts:
                # Get draft details
                draft_details = self.service.users().drafts().get(
                    userId='me',
                    id=draft['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'To', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in draft_details['message']['payload']['headers']}
                
                formatted_draft = {
                    'id': draft['id'],
                    'messageId': draft_details['message']['id'],
                    'threadId': draft_details['message']['threadId'],
                    'subject': headers.get('Subject', ''),
                    'to': headers.get('To', ''),
                    'date': headers.get('Date', '')
                }
                formatted_drafts.append(formatted_draft)
            
            return {
                'success': True,
                'drafts': formatted_drafts,
                'totalDrafts': len(formatted_drafts)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing drafts: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing drafts: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def bulk_modify(self, query: str, add_labels: List[str] = None, remove_labels: List[str] = None, max_messages: int = 1000) -> Dict[str, Any]:
        """
        Universal bulk modify messages using query-based selection and batch operations.
        
        Args:
            query: Gmail search query to select messages
            add_labels: List of label IDs to add (optional)
            remove_labels: List of label IDs to remove (optional) 
            max_messages: Maximum number of messages to process
            
        Returns:
            Dictionary containing bulk operation result
            
        Examples:
            # Mark all unread as read
            bulk_modify("is:unread", remove_labels=["UNREAD"])
            
            # Archive all emails from notifications
            bulk_modify("from:notifications", remove_labels=["INBOX"])
            
            # Add important label to CEO emails
            bulk_modify("from:ceo@company.com", add_labels=["IMPORTANT"])
            
            # Mark inbox emails as unread
            bulk_modify("in:inbox -is:unread", add_labels=["UNREAD"])
        """
        try:
            if not query.strip():
                return {
                    'success': False,
                    'error': 'Query is required for bulk operations'
                }
                
            if not add_labels and not remove_labels:
                return {
                    'success': False,
                    'error': 'At least one of add_labels or remove_labels must be specified'
                }
            
            # Get message IDs matching the query
            search_result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_messages
            ).execute()
            
            message_ids = [msg['id'] for msg in search_result.get('messages', [])]
            
            if not message_ids:
                return {
                    'success': True,
                    'message': 'No messages found matching the query',
                    'query': query,
                    'processed': 0
                }
            
            # Process in batches of 100 (Gmail API limit)
            batch_size = 100
            total_processed = 0
            batch_results = []
            
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                
                # Build batch request
                batch_request = {'ids': batch_ids}
                
                if add_labels:
                    batch_request['addLabelIds'] = add_labels
                if remove_labels:
                    batch_request['removeLabelIds'] = remove_labels
                
                # Execute batch modification
                self.service.users().messages().batchModify(
                    userId='me',
                    body=batch_request
                ).execute()
                
                total_processed += len(batch_ids)
                batch_results.append({
                    'batch': i // batch_size + 1,
                    'processed': len(batch_ids)
                })
                
                logger.info(f"Processed batch {len(batch_results)}: {len(batch_ids)} messages")
            
            # Create descriptive message
            operations = []
            if add_labels:
                operations.append(f"added labels {add_labels}")
            if remove_labels:
                operations.append(f"removed labels {remove_labels}")
            operation_desc = " and ".join(operations)
            
            return {
                'success': True,
                'message': f'Successfully {operation_desc} for {total_processed} messages',
                'query': query,
                'total_found': len(message_ids),
                'processed': total_processed,
                'batches': batch_results,
                'operations': {
                    'added_labels': add_labels or [],
                    'removed_labels': remove_labels or []
                }
            }
            
        except HttpError as e:
            logger.error(f"HTTP error in bulk modify: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error in bulk modify: {e}")
            return {
                'success': False,
                'error': str(e)
            }