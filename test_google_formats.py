#!/usr/bin/env python3
"""
Test script to verify Google native format handling.
Run this to test the Google Docs/Sheets/Slides implementation.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from google_mcp_server.drive_client import GoogleDriveClient

def test_google_format_detection():
    """Test the Google format detection logic."""
    
    print("🧪 Testing Google Native Format Detection")
    print("=" * 50)
    
    # Create a dummy client just to test the helper methods
    class MockDriveClient(GoogleDriveClient):
        def __init__(self):
            # Skip the parent __init__ to avoid needing credentials
            pass
    
    client = MockDriveClient()
    
    # Test cases for format detection
    test_cases = [
        {
            "mime_type": "application/vnd.google-apps.document",
            "expected_native": True,
            "expected_convertible": "text/html",
            "name": "Google Doc"
        },
        {
            "mime_type": "application/vnd.google-apps.spreadsheet", 
            "expected_native": True,
            "expected_convertible": "text/csv",
            "name": "Google Sheet"
        },
        {
            "mime_type": "application/vnd.google-apps.presentation",
            "expected_native": True,
            "expected_convertible": "text/html", 
            "name": "Google Slides"
        },
        {
            "mime_type": "text/plain",
            "expected_native": False,
            "expected_convertible": "text/plain",
            "name": "Plain Text"
        },
        {
            "mime_type": "application/pdf",
            "expected_native": False,
            "expected_convertible": "text/plain",
            "name": "PDF"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing {test_case['name']} ({test_case['mime_type']})")
        
        # Test native format detection
        is_native = client._is_google_native_format(test_case['mime_type'])
        convertible = client._get_convertible_mime_type(test_case['mime_type'])
        
        # Check results
        native_pass = is_native == test_case['expected_native']
        convertible_pass = convertible == test_case['expected_convertible']
        
        print(f"   Native format: {is_native} {'✅' if native_pass else '❌'}")
        print(f"   Convertible type: {convertible} {'✅' if convertible_pass else '❌'}")
        
        if not (native_pass and convertible_pass):
            print(f"   Expected: native={test_case['expected_native']}, convertible={test_case['expected_convertible']}")
        
        print()
    
    print("📝 API Call Logic Summary:")
    print("   📄 Google Docs (empty): Metadata-only API call")
    print("   📄 Google Docs (with content): Upload HTML → Convert to Doc")
    print("   📊 Google Sheets (empty): Metadata-only API call") 
    print("   📊 Google Sheets (with content): Upload CSV → Convert to Sheet")
    print("   📽️ Google Slides (empty): Metadata-only API call")
    print("   📽️ Google Slides (with content): Upload HTML → Convert to Slides")
    print("   📁 Regular files: Standard media upload")
    print()
    
    print("🔧 New Tools Available:")
    print("   • drive_create_google_doc(name, content, parent_folder_id, drive_id)")
    print("   • drive_create_google_sheet(name, content, parent_folder_id, drive_id)")
    print("   • drive_create_google_slide(name, content, parent_folder_id, drive_id)")
    print()
    
    print("💡 Usage Examples:")
    print("   # Create empty Google Doc")
    print("   drive_create_google_doc(name='My Document')")
    print()
    print("   # Create Google Doc with content")
    print("   drive_create_google_doc(name='My Document', content='<h1>Hello World</h1>')")
    print()
    print("   # Create Google Sheet with CSV data")
    print("   drive_create_google_sheet(name='My Sheet', content='Name,Age\\nJohn,30\\nJane,25')")
    print()
    print("   # Create in shared drive")
    print("   drive_create_google_doc(name='Team Doc', drive_id='shared_drive_123')")

if __name__ == "__main__":
    test_google_format_detection()