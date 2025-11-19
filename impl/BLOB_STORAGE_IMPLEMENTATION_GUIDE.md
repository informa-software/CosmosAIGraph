# Azure Blob Storage Implementation Guide - Step by Step

This comprehensive guide walks you through implementing Azure Blob Storage for contract PDF management.

**Container**: tenant1-dev20
**Folder Path**: system/contract-intelligence
**Connection**: Existing storage account (stfidev20)

---

## Phase 1: Setup and Configuration (30 minutes)

### Step 1.1: Install Python Dependencies

```bash
cd web_app

# Add to requirements.in
echo "azure-storage-blob>=12.19.0" >> requirements.in

# Regenerate requirements.txt and install
pip-compile requirements.in
pip install -r requirements.txt
```

### Step 1.2: Configure Environment Variables

**Option A: PowerShell (Persistent)**

Add these lines to your `set-caig-env-vars.ps1`:

```powershell
echo 'setting CAIG_AZURE_STORAGE_CONNECTION_STRING'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_CONNECTION_STRING", "DefaultEndpointsProtocol=https;AccountName=stfidev20;AccountKey=roEOP1LaD3cZVgvt6+BYMIPBSuJ+yOlYoF4lLnzzndpqMHyh/9Bg0P9Gc7PQkfjfNn06ksl6/gtIoOfssYrpzQ==;EndpointSuffix=core.windows.net", "User")

echo 'setting CAIG_AZURE_STORAGE_CONTAINER'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_CONTAINER", "tenant1-dev20", "User")

echo 'setting CAIG_AZURE_STORAGE_FOLDER_PREFIX'
[Environment]::SetEnvironmentVariable("CAIG_AZURE_STORAGE_FOLDER_PREFIX", "system/contract-intelligence", "User")
```

Then run:
```powershell
.\set-caig-env-vars.ps1
```

**Option B: .env File (Development)**

Add to `web_app/.env`:

```bash
CAIG_AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=stfidev20;AccountKey=roEOP1LaD3cZVgvt6+BYMIPBSuJ+yOlYoF4lLnzzndpqMHyh/9Bg0P9Gc7PQkfjfNn06ksl6/gtIoOfssYrpzQ==;EndpointSuffix=core.windows.net"
CAIG_AZURE_STORAGE_CONTAINER="tenant1-dev20"
CAIG_AZURE_STORAGE_FOLDER_PREFIX="system/contract-intelligence"
CAIG_BLOB_SAS_EXPIRY_HOURS=1
```

### Step 1.3: Verify Configuration

```bash
cd web_app
python test_blob_storage.py
```

Expected output:
```
============================================================
Azure Blob Storage Configuration Test
============================================================
✅ Service initialized successfully
✅ Found X PDF files in blob storage
✅ Generated SAS URL successfully
✅ All tests passed!
```

---

## Phase 2: Backend Integration (45 minutes)

### Step 2.1: Update web_app.py - Add Imports

Add to the imports section at the top of `web_app/web_app.py`:

```python
from src.services.blob_storage_service import BlobStorageService
```

### Step 2.2: Update web_app.py - Add Global Variable

Add after other service variables (around line 50):

```python
# Blob Storage Service for contract PDFs
blob_storage_service: Optional[BlobStorageService] = None
```

### Step 2.3: Update web_app.py - Initialize in Lifespan

Add to the `lifespan()` function after other service initializations:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing initializations ...

    # Initialize Blob Storage Service
    global blob_storage_service
    try:
        config = ConfigService()
        conn_str = config.azure_storage_connection_string()

        if conn_str:
            blob_storage_service = BlobStorageService(
                connection_string=conn_str,
                container_name=config.azure_storage_container(),
                folder_prefix=config.azure_storage_folder_prefix()
            )
            logging.info("✅ BlobStorageService initialized successfully")
        else:
            logging.warning("⚠️ Blob storage connection string not configured - PDF access will not be available")
    except Exception as e:
        logging.error(f"❌ Failed to initialize BlobStorageService: {e}")
        blob_storage_service = None

    yield
    # Cleanup
```

### Step 2.4: Add API Endpoint

Add this endpoint after `/api/contracts/{contract_id}/clauses` (around line 2200):

```python
@app.get("/api/contracts/{contract_id}/pdf-url")
async def get_contract_pdf_url(contract_id: str):
    """
    Generate a time-limited SAS URL for downloading a contract PDF.
    """
    if not blob_storage_service:
        return JSONResponse(
            status_code=503,
            content={"error": "PDF access not configured"}
        )

    try:
        # Set the container
        cosmos_nosql_service.set_container(
            ConfigService.graph_source_db(),
            ConfigService.graph_source_container()
        )

        # Query for contract
        query = "SELECT c.id, c.filename, c.pdf_filename FROM c WHERE c.id = @contract_id AND c.doctype = 'contract_parent'"
        parameters = [{"name": "@contract_id", "value": contract_id}]
        results = list(cosmos_nosql_service.query_items(query, parameters))

        if not results:
            return JSONResponse(
                status_code=404,
                content={"error": "Contract not found"}
            )

        contract = results[0]
        pdf_filename = contract.get('pdf_filename') or contract.get('filename')

        if not pdf_filename:
            return JSONResponse(
                status_code=404,
                content={"error": "PDF filename not found"}
            )

        # Ensure .pdf extension
        if not pdf_filename.lower().endswith('.pdf'):
            pdf_filename = f"{pdf_filename}.pdf"

        # Check existence
        if not blob_storage_service.file_exists(pdf_filename):
            return JSONResponse(
                status_code=404,
                content={"error": "PDF file not found in storage"}
            )

        # Generate SAS URL
        config = ConfigService()
        expiry_hours = config.blob_sas_expiry_hours()
        sas_url = blob_storage_service.generate_sas_url(pdf_filename, expiry_hours)

        return {
            "contract_id": contract_id,
            "pdf_url": sas_url,
            "expires_in_hours": expiry_hours,
            "pdf_filename": pdf_filename
        }

    except Exception as e:
        logging.error(f"Error generating PDF URL: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
```

### Step 2.5: Test Backend

```bash
# Start the web app
cd web_app
python web_app.py
```

Test the endpoint:
```bash
# In another terminal
curl "http://localhost:8000/api/contracts/contract_123/pdf-url"
```

---

## Phase 3: Frontend Integration (30 minutes)

### Step 3.1: Update contract.service.ts

Add to `query-builder/src/app/contract-workbench/services/contract.service.ts`:

```typescript
getContractPdfUrl(contractId: string): Observable<{
  contract_id: string;
  pdf_url: string;
  expires_in_hours: number;
  pdf_filename: string;
}> {
  return this.http.get<any>(`${this.apiUrl}/contracts/${contractId}/pdf-url`);
}

openContractPdf(contractId: string): void {
  this.getContractPdfUrl(contractId).subscribe({
    next: (response) => {
      window.open(response.pdf_url, '_blank');
    },
    error: (error) => {
      console.error('Error opening PDF:', error);
      alert(`PDF Error: ${error.error?.message || 'Failed to open PDF'}`);
    }
  });
}
```

### Step 3.2: Update contract-workbench.ts

Add method to component:

```typescript
viewContractPdf(contractId: string): void {
  this.contractService.openContractPdf(contractId);
}
```

### Step 3.3: Update contract-workbench.html

Add button to contract details or list:

```html
<button
  class="btn btn-primary btn-sm"
  (click)="viewContractPdf(contract.id)"
  title="Open PDF in new tab">
  📄 View PDF
</button>
```

### Step 3.4: Test Frontend

```bash
# Build and serve Angular app
cd query-builder
npm run start
```

Visit `https://localhost:4200` and test "View PDF" button.

---

## Phase 4: Data Migration (1-2 hours)

### Step 4.1: Verify PDFs Exist Locally

```bash
ls web_app/static/contracts/pdfs/*.pdf | wc -l
```

### Step 4.2: Run Migration in Dry-Run Mode

```bash
cd web_app
python migrate_pdfs_to_blob.py --dry-run
```

This shows what would be uploaded without actually uploading.

### Step 4.3: Run Actual Migration

```bash
python migrate_pdfs_to_blob.py
```

Monitor output:
```
[1/15] Processing: CONTRACT_NAME.pdf
  Size: 847.61 KB
✅ UPLOADED: CONTRACT_NAME.pdf
✓ VERIFIED: CONTRACT_NAME.pdf

...

Migration Complete
Total files: 15
Successful: 15
Failed: 0
Success rate: 100.0%
```

### Step 4.4: Verify Migration

```bash
python migrate_pdfs_to_blob.py --verify
```

Or manually check in Azure Portal:
1. Go to Storage Account `stfidev20`
2. Navigate to container `tenant1-dev20`
3. Open folder `system/contract-intelligence/`
4. Verify all PDFs are present

---

## Phase 5: Update Contract Metadata (Optional)

If your contract documents in CosmosDB don't have `pdf_filename` field, you need to add it:

```python
# Script to update contracts with pdf_filename
import os
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService

config = ConfigService()
cosmos = CosmosNoSQLService(
    uri=config.cosmosdb_nosql_uri(),
    key=config.cosmosdb_nosql_key()
)

cosmos.set_container(config.graph_source_db(), config.graph_source_container())

# Query all contracts
query = "SELECT * FROM c WHERE c.doctype = 'contract_parent'"
contracts = list(cosmos.query_items(query, []))

for contract in contracts:
    # If pdf_filename not set, derive from filename
    if 'pdf_filename' not in contract and 'filename' in contract:
        pdf_filename = contract['filename']
        if not pdf_filename.endswith('.pdf'):
            pdf_filename += '.pdf'

        contract['pdf_filename'] = pdf_filename
        cosmos.upsert_item(contract)
        print(f"Updated {contract['id']} with pdf_filename: {pdf_filename}")
```

---

## Phase 6: Testing & Validation (30 minutes)

### Test Checklist

#### Backend Tests
- [ ] `/api/contracts/{id}/pdf-url` returns SAS URL
- [ ] SAS URL is valid and opens PDF
- [ ] Invalid contract ID returns 404
- [ ] Missing PDF returns 404
- [ ] Service unavailable returns 503

#### Frontend Tests
- [ ] "View PDF" button opens new tab with PDF
- [ ] PDF displays correctly in browser
- [ ] Error messages display for failures
- [ ] Works across different browsers
- [ ] Popup blocker doesn't interfere

#### Migration Tests
- [ ] All local PDFs uploaded to blob storage
- [ ] File sizes match between local and blob
- [ ] No upload failures or errors
- [ ] Verification confirms all files present

#### End-to-End Tests
1. Select a contract in the UI
2. Click "View PDF"
3. PDF opens in new tab within 2 seconds
4. PDF content displays correctly
5. Can download PDF from browser
6. Repeat with 3+ different contracts

---

## Phase 7: Cleanup (Optional - After 2 Week Validation)

Once you've validated that blob storage is working correctly:

### Step 7.1: Backup Local PDFs

```bash
# Create backup before deletion
cd web_app/static/contracts
tar -czf pdfs_backup_$(date +%Y%m%d).tar.gz pdfs/
```

### Step 7.2: Remove Static Files Mount

In `web_app/web_app.py`, comment out or remove:

```python
# app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Step 7.3: Delete Local PDFs

```bash
# After confirming backup and blob storage work
rm -rf web_app/static/contracts/pdfs/
```

---

## Troubleshooting

### Issue: "Connection string not found"
**Solution:** Run `set-caig-env-vars.ps1` or restart terminal after setting environment variables.

### Issue: "Container not found"
**Solution:** Verify container name is `tenant1-dev20` (case-sensitive).

### Issue: "Blob not found"
**Solution:** Check files are in `system/contract-intelligence/` folder path.

### Issue: "SAS URL returns 403 Forbidden"
**Solution:**
- Verify account key is correct
- Check SAS token hasn't expired
- Ensure blob path matches exactly (case-sensitive)

### Issue: "PDF doesn't open"
**Solution:**
- Check browser popup blocker settings
- Try right-click → "Open in new tab"
- Check browser console for errors

### Issue: "Migration script fails"
**Solution:**
- Verify connection string is correct
- Check network connectivity to Azure
- Run with `--dry-run` first to diagnose
- Check `pdf_migration.log` for details

---

## Rollback Plan

If you need to rollback to local file serving:

1. **Keep local PDFs** - Don't delete until fully validated
2. **Re-enable StaticFiles** in web_app.py
3. **Update Angular** to use `/static/contracts/pdfs/` URLs
4. **Restart services**

---

## Performance Benchmarks

Expected performance metrics:

| Operation | Target | Acceptable |
|-----------|--------|------------|
| SAS URL Generation | <100ms | <500ms |
| PDF Load Time | <2s | <5s |
| Migration (15 PDFs) | <5 min | <10 min |
| Blob List Operation | <1s | <3s |

---

## Support and Next Steps

### Documentation References
- [Azure Blob Storage Setup](./AZURE_BLOB_STORAGE_SETUP.md)
- [Angular Updates](../query-builder/ANGULAR_BLOB_STORAGE_UPDATES.md)
- [API Endpoint Code](./CONTRACT_PDF_API_ENDPOINT.py)

### Future Enhancements
1. Add PDF thumbnail generation
2. Implement PDF annotation/commenting
3. Add version control for PDF updates
4. Enable PDF full-text search
5. Add PDF comparison/diff functionality

### Questions or Issues?
- Check logs: `web_app/pdf_migration.log`
- Review Azure Portal blob container
- Test with `test_blob_storage.py`
- Verify environment variables are set

---

## Success Criteria

✅ All PDFs accessible via Azure Blob Storage
✅ Frontend "View PDF" functionality working
✅ No local file dependencies
✅ SAS URLs generating correctly
✅ Migration completed without errors
✅ End-to-end testing passed
✅ Performance within acceptable limits

**Congratulations! Your PDF storage is now cloud-based and scalable!** 🎉
