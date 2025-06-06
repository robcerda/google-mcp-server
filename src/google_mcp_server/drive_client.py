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
        
    def _is_google_native_format(self, mime_type: str) -> bool:
        """Check if the MIME type is a Google native format."""
        google_native_types = {
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet', 
            'application/vnd.google-apps.presentation',
            'application/vnd.google-apps.drawing',
            'application/vnd.google-apps.form',
            'application/vnd.google-apps.site'
        }
        return mime_type in google_native_types
    
    def _get_convertible_mime_type(self, target_google_type: str) -> str:
        """Get the convertible MIME type for a Google native format."""
        conversion_map = {
            'application/vnd.google-apps.document': 'text/html',
            'application/vnd.google-apps.spreadsheet': 'text/csv',
            'application/vnd.google-apps.presentation': 'text/html'
        }
        return conversion_map.get(target_google_type, 'text/plain')
        
    def list_files(self, query: Optional[str] = None, 
                   folder_id: Optional[str] = None,
                   max_results: int = 10,
                   drive_id: Optional[str] = None,
                   include_team_drives: bool = True) -> Dict[str, Any]:
        """
        List files in Google Drive.
        
        Args:
            query: Search query string
            folder_id: ID of folder to search in
            max_results: Maximum number of results to return
            drive_id: Shared drive ID to search in (optional)
            include_team_drives: Include shared drives in search
            
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
            
            # Execute search with shared drive support
            request_params = {
                'q': search_query,
                'pageSize': max_results,
                'fields': "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, driveId)",
                'includeItemsFromAllDrives': include_team_drives,
                'supportsAllDrives': True
            }
            
            if drive_id:
                request_params['driveId'] = drive_id
                request_params['corpora'] = 'drive'
            
            results = self.service.files().list(**request_params).execute()
            
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
                    'driveId': file.get('driveId', ''),
                    'isFolder': file['mimeType'] == 'application/vnd.google-apps.folder',
                    'isInSharedDrive': bool(file.get('driveId'))
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
                    mime_type: str = "text/plain",
                    drive_id: Optional[str] = None,
                    convert_to_google_format: bool = False) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            name: File name
            content: File content
            parent_folder_id: Parent folder ID (optional)
            mime_type: MIME type
            drive_id: Shared drive ID (optional)
            convert_to_google_format: Convert to Google format (Docs/Sheets/Slides)
            
        Returns:
            Dictionary containing upload result
        """
        try:
            # Prepare file metadata
            file_metadata = {'name': name}
            
            # Handle shared drive vs personal drive logic
            if drive_id:
                # For shared drives, we need to handle parents differently
                if parent_folder_id:
                    # Use the specified folder within the shared drive
                    file_metadata['parents'] = [parent_folder_id]
                else:
                    # Use the shared drive root - need to get the drive's root folder
                    try:
                        drive_info = self.service.drives().get(driveId=drive_id).execute()
                        # For shared drives, the drive ID is also the root folder ID
                        file_metadata['parents'] = [drive_id]
                    except HttpError:
                        # Fallback: try using drive_id directly as parent
                        file_metadata['parents'] = [drive_id]
            else:
                # Personal drive logic
                if parent_folder_id:
                    file_metadata['parents'] = [parent_folder_id]
                # If no parent_folder_id, file goes to root (no parents needed)
            
            # Check if this is a Google native format
            is_google_native = self._is_google_native_format(mime_type)
            
            # Prepare request parameters
            request_params = {
                'body': file_metadata,
                'fields': 'id, name, webViewLink, driveId',
                'supportsAllDrives': True
            }
            
            if drive_id:
                request_params['supportsTeamDrives'] = True  # Legacy parameter for compatibility
            
            if is_google_native:
                # For Google native formats, create metadata-only file
                if content.strip():
                    # If content is provided, we need to upload in a convertible format
                    # and let Google convert it
                    convertible_mime = self._get_convertible_mime_type(mime_type)
                    content_bytes = content.encode('utf-8')
                    media = MediaIoBaseUpload(
                        BytesIO(content_bytes),
                        mimetype=convertible_mime,
                        resumable=True
                    )
                    request_params['media_body'] = media
                    
                    # Set the target Google format in metadata
                    file_metadata['mimeType'] = mime_type
                else:
                    # Create empty Google native file (metadata only)
                    file_metadata['mimeType'] = mime_type
                    # No media_body for empty Google native files
            else:
                # Regular file upload with content
                if content:
                    content_bytes = content.encode('utf-8')
                    media = MediaIoBaseUpload(
                        BytesIO(content_bytes),
                        mimetype=mime_type,
                        resumable=True
                    )
                    request_params['media_body'] = media
            
            file = self.service.files().create(**request_params).execute()
            
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
                    mime_type: str = "text/plain",
                    drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new file in Google Drive.
        
        Args:
            name: File name
            content: File content (default: empty string)
            parent_folder_id: Parent folder ID (optional)
            mime_type: MIME type (default: text/plain)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Dictionary containing file creation result
        """
        return self.upload_file(name, content, parent_folder_id, mime_type, drive_id)
    
    def create_folder(self, name: str, 
                      parent_folder_id: Optional[str] = None,
                      drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            name: Folder name
            parent_folder_id: Parent folder ID (optional)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Dictionary containing folder creation result
        """
        try:
            # Prepare folder metadata
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # Handle shared drive vs personal drive logic
            if drive_id:
                # For shared drives, we need to handle parents differently
                if parent_folder_id:
                    # Use the specified folder within the shared drive
                    file_metadata['parents'] = [parent_folder_id]
                else:
                    # Use the shared drive root
                    try:
                        drive_info = self.service.drives().get(driveId=drive_id).execute()
                        # For shared drives, the drive ID is also the root folder ID
                        file_metadata['parents'] = [drive_id]
                    except HttpError:
                        # Fallback: try using drive_id directly as parent
                        file_metadata['parents'] = [drive_id]
            else:
                # Personal drive logic
                if parent_folder_id:
                    file_metadata['parents'] = [parent_folder_id]
                # If no parent_folder_id, folder goes to root (no parents needed)
            
            # Create folder with shared drive support
            request_params = {
                'body': file_metadata,
                'fields': 'id, name, webViewLink, driveId',
                'supportsAllDrives': True
            }
            
            # Add legacy parameter for compatibility
            if drive_id:
                request_params['supportsTeamDrives'] = True
            
            folder = self.service.files().create(**request_params).execute()
            
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
    
    def copy_file(self, file_id: str, name: Optional[str] = None,
                  parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Copy a file in Google Drive.
        
        Args:
            file_id: Google Drive file ID to copy
            name: New file name (optional, defaults to "Copy of [original name]")
            parent_folder_id: Parent folder ID for the copy (optional)
            
        Returns:
            Dictionary containing copy result
        """
        try:
            # Get original file metadata if name not provided
            if not name:
                original_file = self.service.files().get(
                    fileId=file_id, 
                    fields='name',
                    supportsAllDrives=True
                ).execute()
                name = f"Copy of {original_file['name']}"
            
            # Prepare copy metadata
            copy_metadata = {'name': name}
            if parent_folder_id:
                copy_metadata['parents'] = [parent_folder_id]
            
            # Copy file
            copied_file = self.service.files().copy(
                fileId=file_id,
                body=copy_metadata,
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return {
                'success': True,
                'file': {
                    'id': copied_file['id'],
                    'name': copied_file['name'],
                    'webViewLink': copied_file.get('webViewLink', '')
                },
                'message': f"File copied successfully as '{name}'"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error copying file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def move_file(self, file_id: str, new_parent_folder_id: str,
                  remove_from_current_parents: bool = True) -> Dict[str, Any]:
        """
        Move a file to a different folder in Google Drive.
        
        Args:
            file_id: Google Drive file ID to move
            new_parent_folder_id: New parent folder ID
            remove_from_current_parents: Remove from current parents (default: True)
            
        Returns:
            Dictionary containing move result
        """
        try:
            # Get current parents if we need to remove them
            previous_parents = ""
            if remove_from_current_parents:
                file = self.service.files().get(
                    fileId=file_id,
                    fields='parents',
                    supportsAllDrives=True
                ).execute()
                previous_parents = ",".join(file.get('parents', []))
            
            # Move file
            moved_file = self.service.files().update(
                fileId=file_id,
                addParents=new_parent_folder_id,
                removeParents=previous_parents,
                fields='id, name, parents',
                supportsAllDrives=True
            ).execute()
            
            return {
                'success': True,
                'file': {
                    'id': moved_file['id'],
                    'name': moved_file['name'],
                    'parents': moved_file.get('parents', [])
                },
                'message': f"File '{moved_file['name']}' moved successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error moving file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file in Google Drive.
        
        Args:
            file_id: Google Drive file ID to rename
            new_name: New file name
            
        Returns:
            Dictionary containing rename result
        """
        try:
            # Update file name
            updated_file = self.service.files().update(
                fileId=file_id,
                body={'name': new_name},
                fields='id, name, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            return {
                'success': True,
                'file': {
                    'id': updated_file['id'],
                    'name': updated_file['name'],
                    'webViewLink': updated_file.get('webViewLink', '')
                },
                'message': f"File renamed to '{new_name}' successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error renaming file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_file_content(self, file_id: str, content: str,
                           mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Update the content of an existing file in Google Drive.
        
        Args:
            file_id: Google Drive file ID to update
            content: New file content
            mime_type: MIME type (optional, will be detected if not provided)
            
        Returns:
            Dictionary containing update result
        """
        try:
            # Get current file metadata if mime_type not provided
            if not mime_type:
                file_metadata = self.service.files().get(
                    fileId=file_id,
                    fields='mimeType',
                    supportsAllDrives=True
                ).execute()
                mime_type = file_metadata['mimeType']
            
            # Create media upload
            content_bytes = content.encode('utf-8')
            media = MediaIoBaseUpload(
                BytesIO(content_bytes),
                mimetype=mime_type,
                resumable=True
            )
            
            # Update file
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, name, modifiedTime',
                supportsAllDrives=True
            ).execute()
            
            return {
                'success': True,
                'file': {
                    'id': updated_file['id'],
                    'name': updated_file['name'],
                    'modifiedTime': updated_file['modifiedTime']
                },
                'message': f"File '{updated_file['name']}' content updated successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error updating file content: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error updating file content: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file_permissions(self, file_id: str) -> Dict[str, Any]:
        """
        Get file sharing permissions.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            Dictionary containing permissions information
        """
        try:
            # Get file permissions
            permissions = self.service.permissions().list(
                fileId=file_id,
                fields='permissions(id, type, role, emailAddress, displayName)',
                supportsAllDrives=True
            ).execute()
            
            # Format permissions
            formatted_permissions = []
            for perm in permissions.get('permissions', []):
                formatted_perm = {
                    'id': perm['id'],
                    'type': perm['type'],
                    'role': perm['role'],
                    'emailAddress': perm.get('emailAddress', ''),
                    'displayName': perm.get('displayName', '')
                }
                formatted_permissions.append(formatted_perm)
            
            return {
                'success': True,
                'permissions': formatted_permissions,
                'totalPermissions': len(formatted_permissions)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error getting file permissions: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting file permissions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def share_file(self, file_id: str, email_address: str, role: str = "reader",
                   send_notification: bool = True, message: str = "") -> Dict[str, Any]:
        """
        Share a file with a user (limited by drive.file scope).
        
        Args:
            file_id: Google Drive file ID to share
            email_address: Email address to share with
            role: Permission role (reader, writer, commenter)
            send_notification: Send email notification
            message: Optional message to include
            
        Returns:
            Dictionary containing share result
        """
        try:
            # Create permission
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email_address
            }
            
            # Share file
            created_permission = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=send_notification,
                emailMessage=message if message else None,
                fields='id, type, role, emailAddress',
                supportsAllDrives=True
            ).execute()
            
            return {
                'success': True,
                'permission': {
                    'id': created_permission['id'],
                    'type': created_permission['type'],
                    'role': created_permission['role'],
                    'emailAddress': created_permission['emailAddress']
                },
                'message': f"File shared with {email_address} as {role}"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error sharing file: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_shared_drives(self, max_results: int = 10) -> Dict[str, Any]:
        """
        List available shared drives.
        
        Args:
            max_results: Maximum number of shared drives to return
            
        Returns:
            Dictionary containing shared drives list
        """
        try:
            # Get shared drives list
            results = self.service.drives().list(
                pageSize=max_results,
                fields="nextPageToken, drives(id, name, createdTime, capabilities, restrictions)"
            ).execute()
            
            drives = results.get('drives', [])
            
            # Format results
            formatted_drives = []
            for drive in drives:
                formatted_drive = {
                    'id': drive['id'],
                    'name': drive['name'],
                    'createdTime': drive.get('createdTime', ''),
                    'capabilities': drive.get('capabilities', {}),
                    'restrictions': drive.get('restrictions', {})
                }
                formatted_drives.append(formatted_drive)
            
            return {
                'success': True,
                'drives': formatted_drives,
                'totalDrives': len(formatted_drives),
                'hasMore': 'nextPageToken' in results
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing shared drives: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing shared drives: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_google_doc(self, name: str, content: str = "",
                         parent_folder_id: Optional[str] = None,
                         drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Google Doc.
        
        Args:
            name: Document name
            content: Initial content (HTML or plain text)
            parent_folder_id: Parent folder ID (optional)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Dictionary containing document creation result
        """
        return self.upload_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id,
            mime_type='application/vnd.google-apps.document',
            drive_id=drive_id
        )
    
    def create_google_sheet(self, name: str, content: str = "",
                           parent_folder_id: Optional[str] = None,
                           drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Google Sheet.
        
        Args:
            name: Spreadsheet name
            content: Initial content (CSV format)
            parent_folder_id: Parent folder ID (optional)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Dictionary containing spreadsheet creation result
        """
        return self.upload_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id,
            mime_type='application/vnd.google-apps.spreadsheet',
            drive_id=drive_id
        )
    
    def create_google_slide(self, name: str, content: str = "",
                           parent_folder_id: Optional[str] = None,
                           drive_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Google Slides presentation.
        
        Args:
            name: Presentation name
            content: Initial content (HTML format)
            parent_folder_id: Parent folder ID (optional)
            drive_id: Shared drive ID (optional)
            
        Returns:
            Dictionary containing presentation creation result
        """
        return self.upload_file(
            name=name,
            content=content,
            parent_folder_id=parent_folder_id,
            mime_type='application/vnd.google-apps.presentation',
            drive_id=drive_id
        )