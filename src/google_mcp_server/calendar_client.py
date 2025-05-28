"""Google Calendar API client for MCP server."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleCalendarClient:
    """Client for Google Calendar API operations."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize the Google Calendar client.
        
        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = build('calendar', 'v3', credentials=credentials)
        
    def list_calendars(self) -> Dict[str, Any]:
        """
        List available calendars.
        
        Returns:
            Dictionary containing calendar list
        """
        try:
            # Get calendar list
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            formatted_calendars = []
            for calendar in calendars:
                formatted_calendar = {
                    'id': calendar['id'],
                    'summary': calendar.get('summary', ''),
                    'description': calendar.get('description', ''),
                    'primary': calendar.get('primary', False),
                    'accessRole': calendar.get('accessRole', ''),
                    'timeZone': calendar.get('timeZone', ''),
                    'backgroundColor': calendar.get('backgroundColor', ''),
                    'foregroundColor': calendar.get('foregroundColor', ''),
                    'selected': calendar.get('selected', False)
                }
                formatted_calendars.append(formatted_calendar)
            
            return {
                'success': True,
                'calendars': formatted_calendars,
                'totalCalendars': len(formatted_calendars)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing calendars: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_events(self, calendar_id: str = 'primary',
                    time_min: Optional[str] = None,
                    time_max: Optional[str] = None,
                    max_results: int = 10) -> Dict[str, Any]:
        """
        List events from a calendar.
        
        Args:
            calendar_id: Calendar ID
            time_min: Start time filter (ISO format)
            time_max: End time filter (ISO format)
            max_results: Maximum number of results
            
        Returns:
            Dictionary containing event list
        """
        try:
            # Prepare parameters
            params = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if time_min:
                params['timeMin'] = time_min
            if time_max:
                params['timeMax'] = time_max
            
            # Get events
            events_result = self.service.events().list(**params).execute()
            events = events_result.get('items', [])
            
            formatted_events = []
            for event in events:
                # Extract start and end times
                start = event.get('start', {})
                end = event.get('end', {})
                
                formatted_event = {
                    'id': event['id'],
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'status': event.get('status', ''),
                    'created': event.get('created', ''),
                    'updated': event.get('updated', ''),
                    'start': {
                        'dateTime': start.get('dateTime'),
                        'date': start.get('date'),
                        'timeZone': start.get('timeZone')
                    },
                    'end': {
                        'dateTime': end.get('dateTime'),
                        'date': end.get('date'),
                        'timeZone': end.get('timeZone')
                    },
                    'attendees': [
                        {
                            'email': attendee.get('email', ''),
                            'displayName': attendee.get('displayName', ''),
                            'responseStatus': attendee.get('responseStatus', '')
                        }
                        for attendee in event.get('attendees', [])
                    ],
                    'organizer': event.get('organizer', {}),
                    'recurrence': event.get('recurrence', []),
                    'htmlLink': event.get('htmlLink', ''),
                    'hangoutLink': event.get('hangoutLink', ''),
                    'isAllDay': 'date' in start
                }
                formatted_events.append(formatted_event)
            
            return {
                'success': True,
                'events': formatted_events,
                'totalEvents': len(formatted_events),
                'calendarId': calendar_id,
                'timeMin': time_min,
                'timeMax': time_max
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing events: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_event(self, calendar_id: str = 'primary',
                     summary: str = '',
                     description: Optional[str] = None,
                     start_time: str = '',
                     end_time: str = '',
                     location: Optional[str] = None,
                     attendees: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            calendar_id: Calendar ID
            summary: Event title
            description: Event description
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            location: Event location
            attendees: Attendee email addresses (comma-separated)
            
        Returns:
            Dictionary containing event creation result
        """
        try:
            # Prepare event data
            event_data = {
                'summary': summary,
                'start': {'dateTime': start_time},
                'end': {'dateTime': end_time}
            }
            
            if description:
                event_data['description'] = description
            if location:
                event_data['location'] = location
            
            # Add attendees
            if attendees:
                attendee_list = []
                for email in attendees.split(','):
                    email = email.strip()
                    if email:
                        attendee_list.append({'email': email})
                event_data['attendees'] = attendee_list
            
            # Create event
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()
            
            return {
                'success': True,
                'event': {
                    'id': created_event['id'],
                    'summary': created_event.get('summary', ''),
                    'htmlLink': created_event.get('htmlLink', ''),
                    'start': created_event.get('start', {}),
                    'end': created_event.get('end', {}),
                    'location': created_event.get('location', ''),
                    'attendees': created_event.get('attendees', [])
                },
                'message': f"Event '{summary}' created successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error creating event: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_event(self, calendar_id: str = 'primary',
                  event_id: str = '') -> Dict[str, Any]:
        """
        Get a specific calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            
        Returns:
            Dictionary containing event details
        """
        try:
            # Get event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Extract start and end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            formatted_event = {
                'id': event['id'],
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'status': event.get('status', ''),
                'created': event.get('created', ''),
                'updated': event.get('updated', ''),
                'start': {
                    'dateTime': start.get('dateTime'),
                    'date': start.get('date'),
                    'timeZone': start.get('timeZone')
                },
                'end': {
                    'dateTime': end.get('dateTime'),
                    'date': end.get('date'),
                    'timeZone': end.get('timeZone')
                },
                'attendees': [
                    {
                        'email': attendee.get('email', ''),
                        'displayName': attendee.get('displayName', ''),
                        'responseStatus': attendee.get('responseStatus', '')
                    }
                    for attendee in event.get('attendees', [])
                ],
                'organizer': event.get('organizer', {}),
                'recurrence': event.get('recurrence', []),
                'htmlLink': event.get('htmlLink', ''),
                'hangoutLink': event.get('hangoutLink', ''),
                'isAllDay': 'date' in start
            }
            
            return {
                'success': True,
                'event': formatted_event
            }
            
        except HttpError as e:
            logger.error(f"HTTP error getting event: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_event(self, calendar_id: str = 'primary',
                     event_id: str = '',
                     summary: Optional[str] = None,
                     description: Optional[str] = None,
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None,
                     location: Optional[str] = None) -> Dict[str, Any]:
        """
        Update a calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            summary: Event title
            description: Event description
            start_time: Start time (ISO format)
            end_time: End time (ISO format)
            location: Event location
            
        Returns:
            Dictionary containing update result
        """
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if start_time is not None:
                event['start'] = {'dateTime': start_time}
            if end_time is not None:
                event['end'] = {'dateTime': end_time}
            if location is not None:
                event['location'] = location
            
            # Update event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'success': True,
                'event': {
                    'id': updated_event['id'],
                    'summary': updated_event.get('summary', ''),
                    'htmlLink': updated_event.get('htmlLink', ''),
                    'updated': updated_event.get('updated', '')
                },
                'message': f"Event updated successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error updating event: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_event(self, calendar_id: str = 'primary',
                     event_id: str = '') -> Dict[str, Any]:
        """
        Delete a calendar event.
        
        Args:
            calendar_id: Calendar ID
            event_id: Event ID
            
        Returns:
            Dictionary containing deletion result
        """
        try:
            # Get event summary before deleting
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            event_summary = event.get('summary', 'Unknown Event')
            
            # Delete event
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {
                'success': True,
                'message': f"Event '{event_summary}' deleted successfully"
            }
            
        except HttpError as e:
            logger.error(f"HTTP error deleting event: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {
                'success': False,
                'error': str(e)
            }