#!/usr/bin/env python3
"""Test Paperless-ngx integration manually."""

import sys
import tempfile
from pathlib import Path

# Add app to path
sys.path.insert(0, '/workspaces/Scan2Target')

from app.core.targets.manager import TargetManager
from app.core.targets.models import TargetConfig

def test_paperless_config():
    """Test a Paperless-ngx configuration."""
    
    print("=" * 60)
    print("Paperless-ngx Integration Test")
    print("=" * 60)
    
    # Get Paperless-ngx URL and token from user
    print("\nEnter your Paperless-ngx configuration:")
    url = input("URL (e.g., http://paperless.local:8000): ").strip()
    token = input("API Token: ").strip()
    
    if not url or not token:
        print("❌ URL and token are required!")
        return
    
    # Create test target config
    test_target = TargetConfig(
        id="test_paperless",
        type="Paperless-ngx",
        name="Test Paperless",
        config={
            "connection": url,
            "api_token": token
        },
        enabled=True
    )
    
    print("\n" + "=" * 60)
    print("Step 1: Testing Connection")
    print("=" * 60)
    
    manager = TargetManager()
    result = manager._validate_target_config(test_target)
    
    print(f"\nResult: {result}")
    
    if result['status'] != 'ok':
        print(f"❌ Connection test failed: {result.get('message', 'Unknown error')}")
        return
    
    print("✅ Connection test successful!")
    
    # Ask if user wants to test file upload
    test_upload = input("\nTest file upload? (y/n): ").strip().lower()
    
    if test_upload == 'y':
        print("\n" + "=" * 60)
        print("Step 2: Testing File Upload")
        print("=" * 60)
        
        # Create a test PDF file
        test_file = Path(tempfile.mktemp(suffix=".pdf"))
        test_file.write_text("%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 0\n/Kids []\n>>\nendobj\nxref\n0 3\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n108\n%%EOF")
        
        print(f"\nCreated test file: {test_file}")
        print(f"File size: {test_file.stat().st_size} bytes")
        
        try:
            manager._deliver_paperless(test_target, test_file, {"test": True})
            print("\n✅ File upload successful!")
        except Exception as e:
            print(f"\n❌ File upload failed: {e}")
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
                print(f"Cleaned up test file")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    test_paperless_config()
