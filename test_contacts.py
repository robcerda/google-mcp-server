#!/usr/bin/env python3
"""
Test script to verify Google Contacts functionality.
Run this to test the People API integration.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from google_mcp_server.contacts_client import GoogleContactsClient

def test_contact_matching_logic():
    """Test the contact matching algorithms without API calls."""
    
    print("🧪 Testing Contact Matching Logic")
    print("=" * 50)
    
    # Create a dummy client just to test the helper methods
    class MockContactsClient(GoogleContactsClient):
        def __init__(self):
            # Skip the parent __init__ to avoid needing credentials
            pass
    
    client = MockContactsClient()
    
    # Test email validation
    print("📧 Email Validation Tests:")
    email_tests = [
        ("spencer.varney@example.com", True),
        ("spencer", False),
        ("spencer@", False),
        ("@example.com", False),
        ("user@domain", False),
        ("user@domain.co", True),
        ("user.name+tag@example.org", True)
    ]
    
    for email, expected in email_tests:
        result = client._is_valid_email(email)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{email}' -> {result} (expected {expected})")
    
    print("\n🔍 Contact Matching Score Tests:")
    
    # Mock contact data
    test_contact = {
        'names': [{
            'displayName': 'Spencer Varney',
            'givenName': 'Spencer',
            'familyName': 'Varney'
        }],
        'emailAddresses': [{
            'value': 'spencer.varney@company.com'
        }, {
            'value': 'spencer@personalmail.com'  
        }]
    }
    
    # Test queries
    test_queries = [
        ("spencer varney", "Full name match"),
        ("spencer", "First name match"),
        ("varney", "Last name match"),
        ("Spencer", "Capitalized first name"),
        ("spencer.varney@company.com", "Exact email match"),
        ("spencer.varney", "Email username match"),
        ("spence", "Partial name match"),
        ("john doe", "No match")
    ]
    
    for query, description in test_queries:
        score = client._calculate_match_score(test_contact, query.lower())
        status = "🎯" if score > 50 else "❌" if score == 0 else "⚠️"
        print(f"   {status} '{query}' -> Score: {score:.1f} ({description})")
    
    print("\n💡 Usage Examples:")
    print("   # Search for contacts")
    print("   contacts_search('spencer')")
    print() 
    print("   # Send email using contact name")
    print("   smart_send_email('spencer varney', 'Meeting Tomorrow', 'Hi Spencer, ...')")
    print()
    print("   # Share file using contact name")
    print("   smart_share_file('file_id_123', 'spencer varney', 'editor')")
    print()
    print("   # Create calendar event with attendees")
    print("   smart_create_event('Team Meeting', '2024-01-15T14:00:00', '2024-01-15T15:00:00', 'spencer varney, john smith')")
    print()
    print("🔧 New Tools Available:")
    print("   📋 Contact Management:")
    print("      • contacts_search(query, max_results)")
    print("      • contacts_list(max_results)")
    print("      • contacts_get(resource_name)")
    print("      • contacts_resolve_email(name_or_email)")
    print()
    print("   🧠 Smart Tools (with contact resolution):")
    print("      • smart_send_email(to, subject, body, cc, bcc)")
    print("      • smart_share_file(file_id, recipient, role, send_notification, message)")
    print("      • smart_create_event(summary, start_time, end_time, attendees, ...)")
    print("      • smart_forward_email(message_id, to, body)")
    print()
    print("📝 Key Features:")
    print("   • Fuzzy name matching with scoring algorithm")
    print("   • Automatic email address resolution")
    print("   • Multiple contact disambiguation")
    print("   • Works with existing tools seamlessly")

if __name__ == "__main__":
    test_contact_matching_logic()