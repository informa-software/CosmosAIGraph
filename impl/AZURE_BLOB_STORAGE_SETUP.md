# Azure Blob Storage Integration Setup

This document provides step-by-step instructions for integrating Azure Blob Storage for contract PDF management.

## Environment Configuration

### 1. PowerShell Environment Variables (set-caig-env-vars.ps1)

Add these lines to your `set-caig-env-vars.ps1` file:

```powershell
# Azure Blob Storage Configuration
echo 'setting CAIG_AZURE_STORAGE_CONNECTION_STRING'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=stfidev20;AccountKey=roEOP1LaD3cZVgvt6+BYMIPBSuJ+yOlYoF4lLnzzndpqMHyh/9Bg0P9Gc7PQkfjfNn06ksl6/gtIoOfssYrpzQ==;EndpointSuffix=core.windows.net", "User")

echo 'setting CAIG_AZURE_STORAGE_CONTAINER'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_CONTAINER", "tenant1-dev20", "User")

echo 'setting CAIG_AZURE_STORAGE_FOLDER_PREFIX'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_FOLDER_PREFIX", "system/contract-intelligence", "User")
```

**After adding, run the script to set the environment variables:**
```powershell
.\set-caig-env-vars.ps1
```

### 2. .env File Configuration (web_app/.env)

Add these lines to your `web_app/.env` file (create if it doesn't exist):

```bash
# Azure Blob Storage Configuration for Contract PDFs
CAIG_AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=stfidev20;AccountKey=roEOP1LaD3cZVgvt6+BYMIPBSuJ+yOlYoF4lLnzzndpqMHyh/9Bg0P9Gc7PQkfjfNn06ksl6/gtIoOfssYrpzQ==;EndpointSuffix=core.windows.net"
CAIG_AZURE_STORAGE_CONTAINER="tenant1-dev20"
CAIG_AZURE_STORAGE_FOLDER_PREFIX="system/contract-intelligence"

# Optional: SAS URL expiry duration (in hours)
CAIG_BLOB_SAS_EXPIRY_HOURS=1
```

### 3. Python Requirements

Add the Azure Storage SDK to `web_app/requirements.in`:

```bash
azure-storage-blob>=12.19.0
```

Then regenerate requirements.txt:
```bash
cd web_app
pip-compile requirements.in
pip install -r requirements.txt
```

---

## Configuration Service Integration

The blob storage service needs to be initialized in your application. Here's how it integrates with your existing `ConfigService`:

### Add to web_app/src/services/config_service.py

Add these properties to the `ConfigService` class:

```python
@property
def azure_storage_connection_string(self) -> str:
    """Azure Storage connection string for blob storage"""
    return self.get_env_var("CAIG_AZURE_STORAGE_CONNECTION_STRING")

@property
def azure_storage_container(self) -> str:
    """Azure Storage container name"""
    return self.get_env_var("CAIG_AZURE_STORAGE_CONTAINER", "tenant1-dev20")

@property
def azure_storage_folder_prefix(self) -> str:
    """Azure Storage folder prefix for contract PDFs"""
    return self.get_env_var("CAIG_AZURE_STORAGE_FOLDER_PREFIX", "system/contract-intelligence")

@property
def blob_sas_expiry_hours(self) -> int:
    """Hours until blob SAS URLs expire"""
    return int(self.get_env_var("CAIG_BLOB_SAS_EXPIRY_HOURS", "1"))
```

---

## Testing the Configuration

### Test Script

Create `web_app/test_blob_storage.py`:

```python
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
    print(f"   Container: {config.azure_storage_container}")
    print(f"   Folder Prefix: {config.azure_storage_folder_prefix}")
    print(f"   SAS Expiry: {config.blob_sas_expiry_hours} hours")

    # Test connection string
    conn_str = config.azure_storage_connection_string
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
            container_name=config.azure_storage_container,
            folder_prefix=config.azure_storage_folder_prefix
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
```

**Run the test:**
```bash
cd web_app
python test_blob_storage.py
```

Expected output:
```
============================================================
Azure Blob Storage Configuration Test
============================================================

1. Configuration:
   Container: tenant1-dev20
   Folder Prefix: system/contract-intelligence
   SAS Expiry: 1 hours
   Connection String: ...core.windows.net (truncated)

2. Initializing Blob Storage Service...
   ✅ Service initialized successfully

3. Testing file listing...
   ✅ Found 15 PDF files in blob storage
   First 5 files:
      - ALABAMA FIRE SPRINKLER CONTRACTORS LLC 30518.pdf
      - ATTACK-ONE FIRE MANAGEMENT SERVICES, INC. 26277.pdf
      - C S BRITTON INC 30515.pdf
      - CAMERON D WILLIAMS DBA C&Y TRANSPORTATION LLC 31360.pdf
      - GADDY ELECTRIC & PLUMBING COMPANY, LLC 8202.pdf

4. Testing SAS URL generation...
   ✅ Generated SAS URL for: ALABAMA FIRE SPRINKLER CONTRACTORS LLC 30518.pdf
   URL: https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-... (truncated)

5. Testing file existence check...
   ✅ File existence check: ALABAMA FIRE SPRINKLER CONTRACTORS LLC 30518.pdf exists = True

============================================================
✅ All tests passed! Blob storage is configured correctly.
============================================================
```

---

## Security Best Practices

### For Development (Current Setup)
✅ Connection string in environment variables
✅ Connection string in .env file (excluded from git)
✅ SAS tokens with short expiry (1 hour default)

### For Production (Recommended)
- [ ] Store connection string in Azure Key Vault
- [ ] Use Managed Identity instead of connection string
- [ ] Enable blob soft delete (7-30 day retention)
- [ ] Enable container-level immutability policies
- [ ] Monitor access with Azure Monitor

### Azure Key Vault Integration (Optional)

If you want to use Key Vault for production:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Get connection string from Key Vault
credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://your-keyvault.vault.azure.net/", credential=credential)
connection_string = client.get_secret("blob-storage-connection-string").value
```

---

## Troubleshooting

### Issue: "Connection string not found"
**Solution:** Ensure you've run `set-caig-env-vars.ps1` or restart your terminal after setting environment variables.

### Issue: "Container not found"
**Solution:** Verify the container name is correct: `tenant1-dev20`

### Issue: "Blob not found"
**Solution:** Check that files are uploaded to the correct path: `system/contract-intelligence/filename.pdf`

### Issue: "Authentication failed"
**Solution:** Verify the account key in the connection string is correct and hasn't been rotated.

### Issue: "SAS URL returns 403 Forbidden"
**Solution:**
- Check that SAS token hasn't expired
- Verify permissions include READ
- Ensure blob path is correct (case-sensitive)

---

## Next Steps

After verifying the configuration:

1. ✅ Test blob storage connectivity (run test script above)
2. ⏭️ Implement API endpoints for PDF access
3. ⏭️ Update Angular frontend to use new endpoints
4. ⏭️ Migrate existing PDFs from local disk to blob storage
5. ⏭️ Remove local static files after validation period
