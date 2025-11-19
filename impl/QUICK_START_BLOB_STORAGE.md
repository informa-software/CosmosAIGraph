# Quick Start: Azure Blob Storage Integration

**Your .env file has been configured!** ✅

This guide will get you up and running with Azure Blob Storage for contract PDFs in under 15 minutes.

---

## ✅ Step 1: Install Python Dependencies (2 minutes)

```bash
cd web_app

# Add Azure Storage SDK to requirements
echo "azure-storage-blob>=12.19.0" >> requirements.in

# Install dependencies
pip-compile requirements.in
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed azure-storage-blob-12.19.0 azure-core-1.30.0
```

---

## ✅ Step 2: Test Configuration (1 minute)

Your `.env` file now contains:
```bash
CAIG_AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=stfidev20;..."
CAIG_AZURE_STORAGE_CONTAINER="tenant1-dev20"
CAIG_AZURE_STORAGE_FOLDER_PREFIX="system/contract-intelligence"
CAIG_BLOB_SAS_EXPIRY_HOURS="1"
```

**Test the connection:**
```bash
cd web_app
python test_blob_storage.py
```

**Expected output:**
```
============================================================
Azure Blob Storage Configuration Test
============================================================

1. Configuration:
   Container: tenant1-dev20
   Folder Prefix: system/contract-intelligence
   SAS Expiry: 1 hours

2. Initializing Blob Storage Service...
   ✅ Service initialized successfully

3. Testing file listing...
   ✅ Found 15 PDF files in blob storage

4. Testing SAS URL generation...
   ✅ Generated SAS URL for: ALABAMA FIRE SPRINKLER CONTRACTORS LLC 30518.pdf

5. Testing file existence check...
   ✅ File existence check: ALABAMA FIRE SPRINKLER CONTRACTORS LLC 30518.pdf exists = True

============================================================
✅ All tests passed! Blob storage is configured correctly.
============================================================
```

If you see errors, check:
- Network connectivity to Azure
- Connection string is correct
- Container name is `tenant1-dev20`

---

## ✅ Step 3: Integrate Backend API (5 minutes)

### 3.1: Add Import to web_app.py

At the top of `web_app/web_app.py`, add to imports:

```python
from src.services.blob_storage_service import BlobStorageService
```

### 3.2: Add Global Variable

After other service variables (~line 50), add:

```python
# Blob Storage Service for contract PDFs
blob_storage_service: Optional[BlobStorageService] = None
```

### 3.3: Initialize in Lifespan Function

In the `lifespan()` function, after other service initializations, add:

```python
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
            logging.warning("⚠️ Blob storage not configured")
    except Exception as e:
        logging.error(f"❌ Failed to initialize BlobStorageService: {e}")
        blob_storage_service = None
```

### 3.4: Add API Endpoint

The complete endpoint code is in `CONTRACT_PDF_API_ENDPOINT.py`. Copy the endpoint function and add it after `/api/contracts/{contract_id}/clauses` (~line 2200 in web_app.py).

**Or use this simplified version:**

```python
@app.get("/api/contracts/{contract_id}/pdf-url")
async def get_contract_pdf_url(contract_id: str):
    """Generate time-limited SAS URL for contract PDF"""
    if not blob_storage_service:
        return JSONResponse(status_code=503, content={"error": "PDF access not configured"})

    try:
        # Query contract for PDF filename
        cosmos_nosql_service.set_container(
            ConfigService.graph_source_db(),
            ConfigService.graph_source_container()
        )

        query = "SELECT c.id, c.filename, c.pdf_filename FROM c WHERE c.id = @contract_id AND c.doctype = 'contract_parent'"
        parameters = [{"name": "@contract_id", "value": contract_id}]
        results = list(cosmos_nosql_service.query_items(query, parameters))

        if not results:
            return JSONResponse(status_code=404, content={"error": "Contract not found"})

        contract = results[0]
        pdf_filename = contract.get('pdf_filename') or contract.get('filename')

        if not pdf_filename:
            return JSONResponse(status_code=404, content={"error": "PDF filename not found"})

        if not pdf_filename.lower().endswith('.pdf'):
            pdf_filename = f"{pdf_filename}.pdf"

        if not blob_storage_service.file_exists(pdf_filename):
            return JSONResponse(status_code=404, content={"error": "PDF not found in storage"})

        # Generate SAS URL
        config = ConfigService()
        sas_url = blob_storage_service.generate_sas_url(
            pdf_filename,
            expiry_hours=config.blob_sas_expiry_hours()
        )

        return {
            "contract_id": contract_id,
            "pdf_url": sas_url,
            "expires_in_hours": config.blob_sas_expiry_hours(),
            "pdf_filename": pdf_filename
        }

    except Exception as e:
        logging.error(f"Error generating PDF URL: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
```

---

## ✅ Step 4: Test Backend (2 minutes)

### 4.1: Start the Web App

```bash
cd web_app
python web_app.py
```

Look for this in the logs:
```
✅ BlobStorageService initialized successfully
```

### 4.2: Test the Endpoint

In another terminal:
```bash
curl "http://localhost:8000/api/contracts/contract_123/pdf-url"
```

**Expected response:**
```json
{
  "contract_id": "contract_123",
  "pdf_url": "https://stfidev20.blob.core.windows.net/tenant1-dev20/system/contract-intelligence/CONTRACT_NAME.pdf?sv=...",
  "expires_in_hours": 1,
  "pdf_filename": "CONTRACT_NAME.pdf"
}
```

---

## ✅ Step 5: Integrate Frontend (5 minutes)

### 5.1: Update contract.service.ts

Add to `query-builder/src/app/contract-workbench/services/contract.service.ts`:

```typescript
/**
 * Get time-limited SAS URL for contract PDF
 */
getContractPdfUrl(contractId: string): Observable<{
  contract_id: string;
  pdf_url: string;
  expires_in_hours: number;
  pdf_filename: string;
}> {
  return this.http.get<any>(`${this.apiUrl}/contracts/${contractId}/pdf-url`);
}

/**
 * Open contract PDF in new browser tab
 */
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

### 5.2: Update Component

Add to `query-builder/src/app/contract-workbench/contract-workbench.ts`:

```typescript
/**
 * Open PDF viewer for contract
 */
viewContractPdf(contractId: string): void {
  this.contractService.openContractPdf(contractId);
}
```

### 5.3: Add Button to Template

Add to `contract-workbench.html` (e.g., in contract details modal):

```html
<button
  class="btn btn-primary btn-sm"
  (click)="viewContractPdf(contract.id)"
  title="Open PDF in new tab">
  📄 View PDF
</button>
```

---

## ✅ Step 6: Test End-to-End (2 minutes)

1. **Start Angular app:**
```bash
cd query-builder
npm run start
```

2. **Navigate to** `https://localhost:4200`

3. **Select a contract** and click "View PDF"

4. **PDF should open** in new tab within 2 seconds

---

## 🎉 Success!

You now have:
- ✅ Backend API serving PDFs from Azure Blob Storage
- ✅ Secure time-limited SAS URLs (1-hour expiry)
- ✅ Frontend "View PDF" functionality
- ✅ PDFs stored in `system/contract-intelligence/` folder

---

## 📋 Next Steps (Optional)

### Migrate Local PDFs to Blob Storage

If you need to upload PDFs from local disk:

```bash
cd web_app

# Dry run to preview
python migrate_pdfs_to_blob.py --dry-run

# Actual migration
python migrate_pdfs_to_blob.py

# Verify upload
python migrate_pdfs_to_blob.py --verify
```

See `BLOB_STORAGE_IMPLEMENTATION_GUIDE.md` for complete migration instructions.

---

## 🐛 Troubleshooting

### Test script fails
- Verify `.env` file contains all 4 blob storage variables
- Check network connectivity to Azure
- Verify connection string is correct

### API returns 503
- Check web app logs for initialization errors
- Verify BlobStorageService initialized successfully
- Restart web app after .env changes

### PDF doesn't open
- Check browser popup blocker
- Verify SAS URL in response is valid
- Check that PDF exists in blob storage folder

### Connection string error
- Ensure `.env` file is in `web_app/` directory
- No extra spaces in connection string
- Connection string is on single line

---

## 📚 Additional Resources

- Full implementation guide: `BLOB_STORAGE_IMPLEMENTATION_GUIDE.md`
- API endpoint code: `CONTRACT_PDF_API_ENDPOINT.py`
- Angular updates: `query-builder/ANGULAR_BLOB_STORAGE_UPDATES.md`
- Configuration details: `AZURE_BLOB_STORAGE_SETUP.md`

---

## 🆘 Need Help?

Check the logs:
- Web app: Console output when running `python web_app.py`
- Test script: `python test_blob_storage.py`
- Migration: `pdf_migration.log`

Common issues are documented in `BLOB_STORAGE_IMPLEMENTATION_GUIDE.md` troubleshooting section.
