#!/usr/bin/env python3
"""Test SMB connection parsing and connectivity."""

import sys
sys.path.insert(0, '/workspaces/Scan2Target')

from app.core.targets.manager import TargetManager

def test_parsing():
    """Test SMB connection string parsing."""
    print("=" * 70)
    print("SMB Connection String Parsing Tests")
    print("=" * 70)
    
    test_cases = [
        "//192.168.1.100/documents",
        "\\\\192.168.1.100\\documents",
        "192.168.1.100/documents",
        "nas.local/scans",
        "//nas.local/scans/inbox",
        "\\\\nas\\share\\folder\\subfolder",
        "10.0.0.5/backup/scans",
    ]
    
    manager = TargetManager()
    
    for connection in test_cases:
        print(f"\nInput: {connection}")
        try:
            server, share, path = manager._parse_smb_connection(connection)
            print(f"  ✅ Server: {server}")
            print(f"     Share:  {share}")
            print(f"     Path:   {path if path else '(root)'}")
            print(f"     Result: //{server}/{share}" + (f"/{path}" if path else ""))
        except ValueError as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 70)

def test_connection():
    """Test actual SMB connection."""
    print("\n" + "=" * 70)
    print("SMB Connection Test")
    print("=" * 70)
    
    from app.core.targets.models import TargetConfig
    
    print("\nEnter SMB connection details:")
    connection = input("Connection (e.g., 192.168.1.100/documents): ").strip()
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    
    if not connection or not username:
        print("❌ Connection and username are required!")
        return
    
    # Create test target
    test_target = TargetConfig(
        id="test_smb",
        type="SMB",
        name="Test SMB",
        config={
            "connection": connection,
            "username": username,
            "password": password
        },
        enabled=True
    )
    
    print("\n" + "=" * 70)
    print("Testing Connection...")
    print("=" * 70)
    
    manager = TargetManager()
    
    # Parse first
    try:
        server, share, path = manager._parse_smb_connection(connection)
        print(f"\nParsed connection:")
        print(f"  Server: {server}")
        print(f"  Share:  {share}")
        print(f"  Path:   {path if path else '(root)'}")
    except ValueError as e:
        print(f"❌ Invalid connection format: {e}")
        return
    
    # Test connection
    print("\nTesting connectivity...")
    result = manager._validate_target_config(test_target)
    
    print(f"\nResult: {result}")
    
    if result['status'] == 'ok':
        print("✅ Connection successful!")
        
        # Ask if user wants to test file upload
        test_upload = input("\nTest file upload? (y/n): ").strip().lower()
        if test_upload == 'y':
            from pathlib import Path
            import tempfile
            
            # Create test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('Scan2Target test file\n')
                test_file = Path(f.name)
            
            try:
                print(f"\nUploading test file: {test_file.name}")
                manager._deliver_smb(test_target, test_file)
                print("✅ File upload successful!")
                print(f"Check the share for file: {test_file.name}")
            except Exception as e:
                print(f"❌ File upload failed: {e}")
            finally:
                test_file.unlink(missing_ok=True)
    else:
        print(f"❌ Connection failed: {result.get('message', 'Unknown error')}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    # Run parsing tests
    test_parsing()
    
    # Ask if user wants to test actual connection
    test_conn = input("\nTest actual SMB connection? (y/n): ").strip().lower()
    if test_conn == 'y':
        test_connection()
