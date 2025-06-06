"""Google People API client for contact management."""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GoogleContactsClient:
    """Client for Google People API operations."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize the Google Contacts client.
        
        Args:
            credentials: Valid Google OAuth2 credentials
        """
        self.credentials = credentials
        self.service = build('people', 'v1', credentials=credentials)
        
    def search_contacts(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search contacts by name or email.
        
        Args:
            query: Search query (name or email)
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary containing search results
        """
        try:
            # Get all contacts
            contacts_result = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=min(max_results * 3, 1000),  # Get more to filter locally
                personFields='names,emailAddresses,phoneNumbers,organizations'
            ).execute()
            
            # Debug logging
            total_contacts = contacts_result.get('totalSize', 0)
            logger.info(f"People API returned {total_contacts} total contacts")
            
            contacts = contacts_result.get('connections', [])
            
            # Filter contacts based on query
            matching_contacts = []
            query_lower = query.lower().strip()
            
            for contact in contacts:
                match_score = self._calculate_match_score(contact, query_lower)
                if match_score > 0:
                    formatted_contact = self._format_contact(contact)
                    formatted_contact['match_score'] = match_score
                    matching_contacts.append(formatted_contact)
            
            # Sort by match score (higher is better)
            matching_contacts.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Limit results
            matching_contacts = matching_contacts[:max_results]
            
            return {
                'success': True,
                'contacts': matching_contacts,
                'totalMatches': len(matching_contacts),
                'query': query,
                'debug': {
                    'total_contacts_in_account': total_contacts,
                    'contacts_fetched': len(contacts),
                    'contacts_after_filtering': len(matching_contacts)
                }
            }
            
        except HttpError as e:
            logger.error(f"HTTP error searching contacts: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_match_score(self, contact: Dict[str, Any], query: str) -> float:
        """
        Calculate how well a contact matches the search query.
        
        Args:
            contact: Contact data from People API
            query: Search query (lowercase)
            
        Returns:
            Match score (0 = no match, higher = better match)
        """
        score = 0.0
        
        # Check names
        names = contact.get('names', [])
        for name_info in names:
            display_name = name_info.get('displayName', '').lower()
            given_name = name_info.get('givenName', '').lower()
            family_name = name_info.get('familyName', '').lower()
            
            # Exact display name match
            if query == display_name:
                score += 100
            # Display name contains query
            elif query in display_name:
                score += 80
            # Query contains display name (for partial matches)
            elif display_name in query:
                score += 70
            
            # Check individual name parts
            if query == given_name or query == family_name:
                score += 90
            elif query in given_name or query in family_name:
                score += 60
            
            # Check if query matches "first last" format
            full_name = f"{given_name} {family_name}".strip()
            if query == full_name:
                score += 95
            elif query in full_name:
                score += 75
        
        # Check email addresses
        emails = contact.get('emailAddresses', [])
        for email_info in emails:
            email = email_info.get('value', '').lower()
            if query == email:
                score += 100
            elif query in email:
                score += 85
            # Check email username part
            email_username = email.split('@')[0] if '@' in email else email
            if query == email_username:
                score += 90
            elif query in email_username:
                score += 65
        
        return score
    
    def _format_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a contact from People API response.
        
        Args:
            contact: Raw contact data from People API
            
        Returns:
            Formatted contact data
        """
        # Get primary name
        names = contact.get('names', [])
        primary_name = names[0] if names else {}
        display_name = primary_name.get('displayName', 'Unknown')
        given_name = primary_name.get('givenName', '')
        family_name = primary_name.get('familyName', '')
        
        # Get email addresses
        emails = contact.get('emailAddresses', [])
        primary_email = emails[0].get('value', '') if emails else ''
        all_emails = [email.get('value', '') for email in emails]
        
        # Get phone numbers
        phones = contact.get('phoneNumbers', [])
        phone_numbers = [phone.get('value', '') for phone in phones]
        
        # Get organization
        organizations = contact.get('organizations', [])
        organization = organizations[0].get('name', '') if organizations else ''
        
        return {
            'resourceName': contact.get('resourceName', ''),
            'displayName': display_name,
            'givenName': given_name,
            'familyName': family_name,
            'primaryEmail': primary_email,
            'emails': all_emails,
            'phoneNumbers': phone_numbers,
            'organization': organization
        }
    
    def resolve_contact_email(self, name_or_email: str) -> Dict[str, Any]:
        """
        Resolve a name or partial email to a full email address.
        
        Args:
            name_or_email: Contact name or email to resolve
            
        Returns:
            Dictionary with resolved email and contact info
        """
        try:
            # If it's already a valid email, return as-is
            if self._is_valid_email(name_or_email):
                return {
                    'success': True,
                    'resolved_email': name_or_email,
                    'contact_info': None,
                    'confidence': 'high',
                    'message': 'Email address provided directly'
                }
            
            # Search for contacts
            search_result = self.search_contacts(name_or_email, max_results=5)
            
            if not search_result['success']:
                return search_result
            
            contacts = search_result['contacts']
            
            if not contacts:
                return {
                    'success': False,
                    'error': f"No contacts found matching '{name_or_email}'"
                }
            
            # If we have a clear winner (high score), return it
            best_match = contacts[0]
            if best_match['match_score'] > 80 and best_match['primaryEmail']:
                return {
                    'success': True,
                    'resolved_email': best_match['primaryEmail'],
                    'contact_info': best_match,
                    'confidence': 'high',
                    'message': f"Resolved to {best_match['displayName']} ({best_match['primaryEmail']})"
                }
            
            # Multiple potential matches - return options for user to choose
            options = []
            for contact in contacts[:3]:  # Top 3 matches
                if contact['primaryEmail']:
                    options.append({
                        'name': contact['displayName'],
                        'email': contact['primaryEmail'],
                        'organization': contact['organization']
                    })
            
            if not options:
                return {
                    'success': False,
                    'error': f"Found contacts matching '{name_or_email}' but none have email addresses"
                }
            
            return {
                'success': True,
                'requires_confirmation': True,
                'options': options,
                'message': f"Multiple contacts found for '{name_or_email}'. Please specify which one:",
                'original_query': name_or_email
            }
            
        except Exception as e:
            logger.error(f"Error resolving contact email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Check if a string is a valid email address.
        
        Args:
            email: String to check
            
        Returns:
            True if valid email format
        """
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))
    
    def list_contacts(self, max_results: int = 50) -> Dict[str, Any]:
        """
        List all contacts.
        
        Args:
            max_results: Maximum number of contacts to return
            
        Returns:
            Dictionary containing contacts list
        """
        try:
            result = self.service.people().connections().list(
                resourceName='people/me',
                pageSize=max_results,
                personFields='names,emailAddresses,phoneNumbers,organizations'
            ).execute()
            
            contacts = result.get('connections', [])
            
            # Format contacts
            formatted_contacts = []
            for contact in contacts:
                formatted_contact = self._format_contact(contact)
                # Only include contacts with names or emails
                if formatted_contact['displayName'] != 'Unknown' or formatted_contact['primaryEmail']:
                    formatted_contacts.append(formatted_contact)
            
            return {
                'success': True,
                'contacts': formatted_contacts,
                'totalContacts': len(formatted_contacts)
            }
            
        except HttpError as e:
            logger.error(f"HTTP error listing contacts: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error listing contacts: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_contact(self, resource_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific contact.
        
        Args:
            resource_name: Contact resource name (from search results)
            
        Returns:
            Dictionary containing contact details
        """
        try:
            contact = self.service.people().get(
                resourceName=resource_name,
                personFields='names,emailAddresses,phoneNumbers,organizations,addresses,birthdays,urls'
            ).execute()
            
            formatted_contact = self._format_contact(contact)
            
            # Add additional fields
            addresses = contact.get('addresses', [])
            if addresses:
                formatted_contact['addresses'] = [
                    {
                        'type': addr.get('type', ''),
                        'formattedValue': addr.get('formattedValue', '')
                    }
                    for addr in addresses
                ]
            
            birthdays = contact.get('birthdays', [])
            if birthdays:
                formatted_contact['birthdays'] = [
                    {
                        'date': bday.get('date', {}),
                        'text': bday.get('text', '')
                    }
                    for bday in birthdays
                ]
            
            urls = contact.get('urls', [])
            if urls:
                formatted_contact['urls'] = [url.get('value', '') for url in urls]
            
            return {
                'success': True,
                'contact': formatted_contact
            }
            
        except HttpError as e:
            logger.error(f"HTTP error getting contact: {e}")
            return {
                'success': False,
                'error': f"HTTP error: {e.resp.status} - {e.content.decode()}"
            }
        except Exception as e:
            logger.error(f"Error getting contact: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def resolve_attendee_emails(self, attendee_list: str) -> Dict[str, Any]:
        """
        Resolve a comma-separated list of attendee names/emails.
        
        Args:
            attendee_list: Comma-separated list of names or emails
            
        Returns:
            Dictionary with resolved emails and any issues
        """
        try:
            attendees = [attendee.strip() for attendee in attendee_list.split(',') if attendee.strip()]
            resolved_emails = []
            unresolved = []
            requires_confirmation = []
            
            for attendee in attendees:
                result = self.resolve_contact_email(attendee)
                
                if result['success']:
                    if result.get('requires_confirmation'):
                        requires_confirmation.append(result)
                    else:
                        resolved_emails.append(result['resolved_email'])
                else:
                    unresolved.append(attendee)
            
            return {
                'success': True,
                'resolved_emails': resolved_emails,
                'unresolved': unresolved,
                'requires_confirmation': requires_confirmation,
                'total_processed': len(attendees)
            }
            
        except Exception as e:
            logger.error(f"Error resolving attendee emails: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def smart_email_resolve(self, recipient: str, context: str = "email") -> Dict[str, Any]:
        """
        Smart email resolution with user-friendly responses.
        
        Args:
            recipient: Name or email to resolve
            context: Context for the resolution (email, calendar, sharing)
            
        Returns:
            Dictionary with resolved email or user-friendly guidance
        """
        try:
            result = self.resolve_contact_email(recipient)
            
            if result['success'] and not result.get('requires_confirmation'):
                # Clean resolution
                return {
                    'success': True,
                    'email': result['resolved_email'],
                    'message': result['message']
                }
            elif result['success'] and result.get('requires_confirmation'):
                # Multiple options - format for user
                options_text = []
                for i, option in enumerate(result['options'], 1):
                    org_text = f" ({option['organization']})" if option['organization'] else ""
                    options_text.append(f"{i}. {option['name']} - {option['email']}{org_text}")
                
                return {
                    'success': False,
                    'requires_user_choice': True,
                    'message': f"Multiple contacts found for '{recipient}'. Please be more specific or choose:\n" + "\n".join(options_text),
                    'options': result['options']
                }
            else:
                # No matches found
                return {
                    'success': False,
                    'message': f"Could not find a contact for '{recipient}'. Please provide a full email address or add them to your contacts first."
                }
                
        except Exception as e:
            logger.error(f"Error in smart email resolve: {e}")
            return {
                'success': False,
                'error': str(e)
            }