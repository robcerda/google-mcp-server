"""Google Drive API client for MCP server."""

import json
import logging
from typing import Dict, List, Optional, Any
from io import BytesIO
import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Client for Google Drive API operations."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize the Google Drive client.
        
        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
        
    def list_files(self, query: Optional[str] = None, 
                   folder_id: Optional[str] = None,
                   max_results: int = 10) -> Dict[str, Any]:
        """
        List files in Google Drive.
        
        Args:
            query: Search query string
            folder_id: ID of folder to search in
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing file list and metadata
        """
        try:
            # Build query string
            query_parts = []
            if query:
                query_parts.append(f"name contains '{query}'")
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            # Add default filters (exclude trashed files)
            query_parts.append("trashed = false")
            
            search_query = " and ".join(query_parts) if query_parts else "trashed = false"
            
            # Execute search
            results = self.service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            # Format results
            formatted_files = []
            for file in files:
                formatted_file = {
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': file['mimeType'],
                    'size': file.get('size', 'N/A'),
                    'createdTime': file['createdTime'],
                    'modifiedTime': file['modifiedTime'],
                    'webViewLink': file.get('webViewLink', ''),
                    'isFolder': file['mimeType'] == 'application/vnd.google-apps.folder'
                }
                formatted_files.append(formatted_file)
            
            return {
                'success': True,
                'files': formatted_files,
                'totalFiles': len(formatted_files),
                'query': search_query,
                'hasMore': 'nextPageToken' in results
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing files: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file(self, file_id: str, include_content: bool = False) -> Dict[str, Any]:
        """
        Get file metadata and optionally content.
        
        Args:
            file_id: Google Drive file ID
            include_content: Whether to include file content
            
        Returns:
            Dictionary containing file metadata and optional content
        """
        try:
            # Get file metadata
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, description"
            ).execute()
            
            result = {
                'success': True,
                'file': {
                    'id': file['id'],
                    'name': file['name'],
                    'mimeType': file['mimeType'],
                    'size': file.get('size', 'N/A'),
                    'createdTime': file['createdTime'],
                    'modifiedTime': file['modifiedTime'],
                    'webViewLink': file.get('webViewLink', ''),
                    'description': file.get('description', ''),
                    'isFolder': file['mimeType'] == 'application/vnd.google-apps.folder'
                }
            }
            
            # Get file content if requested and it's a text file
            if include_content and not result['file']['isFolder']:
                content = self._get_file_content(file_id, file['mimeType'])
                result['file']['content'] = content
            
            return result
            
        except HttpError as e:
            logger.error(f"HTTP error getting file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_file_content(self, file_id: str, mime_type: str) -> str:
        """
        Get file content based on MIME type.
        
        Args:
            file_id: Google Drive file ID
            mime_type: File MIME type
            
        Returns:
            File content as string
        """
        try:
            # Handle Google Workspace documents
            if mime_type == 'application/vnd.google-apps.document':
                # Export as plain text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Export as CSV
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
            elif mime_type == 'application/vnd.google-apps.presentation':
                # Export as plain text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Get raw file content
                request = self.service.files().get_media(fileId=file_id)
            
            # Execute request
            content = request.execute()
            
            # Convert bytes to string
            if isinstance(content, bytes):
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    return f"[Binary content - {len(content)} bytes]"
            else:
                return str(content)
                
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return f"[Error reading content: {str(e)}]"
    
    def upload_file(self, name: str, content: str, 
                    parent_folder_id: Optional[str] = None,
                    mime_type: str = "text/plain") -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            name: File name
            content: File content
            parent_folder_id: Parent folder ID (optional)
            mime_type: MIME type
            
        Returns:
            Dictionary containing upload result
        """
        try:
            # Prepare file metadata
            file_metadata = {'name': name}
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Create media upload
            content_bytes = content.encode('utf-8')
            media = MediaIoBaseUpload(
                BytesIO(content_bytes),
                mimetype=mime_type,
                resumable=True
            )
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                'success': True,
                'file': {
                    'id': file['id'],
                    'name': file['name'],
                    'webViewLink': file.get('webViewLink', '')
                },
                'message': f"File '{name}' uploaded successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error uploading file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_file(self, name: str, content: str = "", 
                    parent_folder_id: Optional[str] = None,
                    mime_type: str = "text/plain") -> Dict[str, Any]:
        """
        Create a new file in Google Drive.
        
        Args:
            name: File name
            content: File content (default: empty string)
            parent_folder_id: Parent folder ID (optional)
            mime_type: MIME type (default: text/plain)
            
        Returns:
            Dictionary containing file creation result
        """
        return self.upload_file(name, content, parent_folder_id, mime_type)
    
    def create_folder(self, name: str, 
                      parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            name: Folder name
            parent_folder_id: Parent folder ID (optional)
            
        Returns:
            Dictionary containing folder creation result
        """
        try:
            # Prepare folder metadata
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Create folder
            folder = self.service.files().create(
                body=file_metadata,
                fields='id, name, webViewLink'
            ).execute()
            
            return {
                'success': True,
                'folder': {
                    'id': folder['id'],
                    'name': folder['name'],
                    'webViewLink': folder.get('webViewLink', '')
                },
                'message': f"Folder '{name}' created successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error creating folder: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def search_files(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for files in Google Drive.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            Dictionary containing search results
        """
        # Use the list_files method with query
        return self.list_files(query=query, max_results=max_results)
    
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary containing deletion result
        """
        try:
            # Get file name first
            file = self.service.files().get(fileId=file_id, fields='name').execute()
            file_name = file['name']
            
            # Delete file
            self.service.files().delete(fileId=file_id).execute()
            
            return {
                'success': True,
                'message': f"File '{file_name}' deleted successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error deleting file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {
                'success': False,
                'error': str(e)
            }