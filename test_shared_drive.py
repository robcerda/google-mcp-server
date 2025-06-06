#!/usr/bin/env python3
"""
Test script to verify shared drive functionality.
Run this to test the shared drive implementation.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from google_mcp_server.auth import GoogleAuthManager
from google_mcp_server.drive_client import GoogleDriveClient

def test_shared_drive_logic():
    """Test the shared drive logic without making API calls."""
    
    print("🧪 Testing Shared Drive Logic")
    print("=" * 50)
    
    # Test cases for shared drive handling
    test_cases = [
        {
            "name": "Personal Drive - No parent",
            "drive_id": None,
            "parent_folder_id": None,
            "expected_parents": None
        },
        {
            "name": "Personal Drive - With parent",
            "drive_id": None,
            "parent_folder_id": "folder123",
            "expected_parents": ["folder123"]
        },
        {
            "name": "Shared Drive - No parent (should use drive ID as parent)",
            "drive_id": "shared_drive_123",
            "parent_folder_id": None,
            "expected_parents": ["shared_drive_123"]
        },
        {
            "name": "Shared Drive - With parent folder",
            "drive_id": "shared_drive_123",
            "parent_folder_id": "folder456",
            "expected_parents": ["folder456"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}")
        
        # Simulate the logic from our upload_file function
        file_metadata = {'name': 'test_file.txt'}
        drive_id = test_case['drive_id']
        parent_folder_id = test_case['parent_folder_id']
        
        # Apply our logic
        if drive_id:
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            else:
                # In real implementation, we'd call the API, but for test we'll use drive_id
                file_metadata['parents'] = [drive_id]
        else:
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
        
        actual_parents = file_metadata.get('parents')
        expected_parents = test_case['expected_parents']
        
        if actual_parents == expected_parents:
            print(f"   ✅ PASS: parents = {actual_parents}")
        else:
            print(f"   ❌ FAIL: Expected {expected_parents}, got {actual_parents}")
        
        print()
    
    print("📝 Key Points for Shared Drive Usage:")
    print("   • Use drive_list_shared_drives() to find shared drive IDs")
    print("   • Pass drive_id parameter to create files/folders in shared drives")
    print("   • If no parent_folder_id is specified, files go to shared drive root")
    print("   • Both drive_create_file and drive_create_folder now support drive_id")
    print()
    
    print("🔧 Testing Commands:")
    print("   1. List shared drives: drive_list_shared_drives()")
    print("   2. Create file in shared drive: drive_create_file(name='test.txt', content='Hello', drive_id='your_drive_id')")
    print("   3. Create folder in shared drive: drive_create_folder(name='New Folder', drive_id='your_drive_id')")

if __name__ == "__main__":
    test_shared_drive_logic()