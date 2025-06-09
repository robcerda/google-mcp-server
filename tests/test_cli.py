#!/usr/bin/env python3
"""
Simple CLI test script for Google MCP Server.
This script allows you to test the authentication and basic functionality
outside of the MCP protocol.
"""

import os
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from google_mcp_server.auth import GoogleAuthManager
from google_mcp_server.drive_client import GoogleDriveClient
from google_mcp_server.gmail_client import GmailClient
from google_mcp_server.calendar_client import GoogleCalendarClient

def main():
    """Main CLI test function."""
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env file")
        print("Please copy .env.example to .env and configure your credentials")
        return 1
    
    print("🔧 Google MCP Server CLI Test")
    print("=" * 40)
    
    # Initialize auth manager
    try:
        auth_manager = GoogleAuthManager(
            client_id=client_id,
            client_secret=client_secret
        )
        print("✅ Auth manager initialized")
    except Exception as e:
        print(f"❌ Error initializing auth manager: {e}")
        return 1
    
    # Test authentication
    print("\n🔐 Testing Authentication...")
    try:
        creds = auth_manager.get_credentials()
        if creds:
            print("✅ Successfully authenticated")
            
            # Get user info
            user_info = auth_manager.get_user_info()
            if user_info:
                print(f"   User: {user_info.get('name', 'Unknown')} ({user_info.get('email', 'Unknown')})")
            
        else:
            print("❌ Authentication failed")
            return 1
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return 1
    
    # Test Drive client
    print("\n📁 Testing Google Drive...")
    try:
        drive_client = GoogleDriveClient(creds)
        result = drive_client.list_files(max_results=5)
        if result.get('success'):
            print(f"✅ Drive test successful - found {result['totalFiles']} files")
        else:
            print(f"❌ Drive test failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Drive test error: {e}")
    
    # Test Gmail client
    print("\n📧 Testing Gmail...")
    try:
        gmail_client = GmailClient(creds)
        result = gmail_client.list_messages(max_results=5)
        if result.get('success'):
            print(f"✅ Gmail test successful - found {result['totalMessages']} messages")
        else:
            print(f"❌ Gmail test failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Gmail test error: {e}")
    
    # Test Calendar client
    print("\n📅 Testing Google Calendar...")
    try:
        calendar_client = GoogleCalendarClient(creds)
        result = calendar_client.list_calendars()
        if result.get('success'):
            print(f"✅ Calendar test successful - found {result['totalCalendars']} calendars")
        else:
            print(f"❌ Calendar test failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Calendar test error: {e}")
    
    print("\n🎉 All tests completed!")
    print("\nYou can now use this server with Claude Desktop.")
    print("See README.md for Claude Desktop configuration instructions.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())