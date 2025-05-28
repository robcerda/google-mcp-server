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