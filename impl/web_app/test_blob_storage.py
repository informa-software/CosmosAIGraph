"""
Test script to verify Azure Blob Storage configuration and connectivity.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.services.blob_storage_service import BlobStorageService
from src.services.config_service import ConfigService


def test_blob_storage():
    """Test blob storage connectivity and operations."""

    print("=" * 60)
    print("Azure Blob Storage Configuration Test")
    print("=" * 60)

    # Initialize config service
    config = ConfigService()

    # Display configuration
    print("\n1. Configuration:")
    print(f"   Container: {config.azure_storage_container()}")
    print(f"   Folder Prefix: {config.azure_storage_folder_prefix()}")
    print(f"   SAS Expiry: {config.blob_sas_expiry_hours()} hours")

    # Test connection string
    conn_str = config.azure_storage_connection_string()
    if not conn_str or conn_str == "":
        print("\n❌ ERROR: Connection string not configured!")
        print("   Please set CAIG_AZURE_STORAGE_CONNECTION_STRING environment variable")
        return False

    print(f"   Connection String: ...{conn_str[-20:]} (truncated)")

    # Initialize blob storage service
    print("\n2. Initializing Blob Storage Service...")
    try:
        blob_service = BlobStorageService(
            connection_string=conn_str,
            container_name=config.azure_storage_container(),
            folder_prefix=config.azure_storage_folder_prefix()
        )
        print("   ✅ Service initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize service: {e}")
        return False

    # Test listing files
    print("\n3. Testing file listing...")
    try:
        files = blob_service.list_files()
        print(f"   ✅ Found {len(files)} PDF files in blob storage")
        if len(files) > 0:
            print(f"   First 5 files:")
            for f in files[:5]:
                print(f"      - {f}")
    except Exception as e:
        print(f"   ❌ Failed to list files: {e}")
        return False

    # Test SAS URL generation (if files exist)
    if len(files) > 0:
        print("\n4. Testing SAS URL generation...")
        try:
            test_file = files[0]
            sas_url = blob_service.generate_sas_url(test_file, expiry_hours=1)
            print(f"   ✅ Generated SAS URL for: {test_file}")
            print(f"   URL: {sas_url[:80]}... (truncated)")
        except Exception as e:
            print(f"   ❌ Failed to generate SAS URL: {e}")
            return False

    # Test file existence check
    if len(files) > 0:
        print("\n5. Testing file existence check...")
        try:
            test_file = files[0]
            exists = blob_service.file_exists(test_file)
            print(f"   ✅ File existence check: {test_file} exists = {exists}")
        except Exception as e:
            print(f"   ❌ Failed to check file existence: {e}")
            return False

    print("\n" + "=" * 60)
    print("✅ All tests passed! Blob storage is configured correctly.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_blob_storage()
    sys.exit(0 if success else 1)
