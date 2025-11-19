# Contract Upload - Quick Reference

## Overview

Add contract upload functionality with Azure Content Understanding integration.

## Key Features

✅ **Upload Methods**: Button click + Drag-and-drop
✅ **File Validation**: PDF only, 2MB max
✅ **Duplicate Detection**: Warn and auto-rename (file_1.pdf, file_2.pdf)
✅ **Progress Tracking**: Real-time status updates
✅ **Background Processing**: Async jobs with JobService
✅ **Toast Notifications**: Success/failure alerts
✅ **Auto-refresh**: Contracts list updates automatically

---

## Architecture

```
User uploads PDF
    ↓
Frontend validation (PDF, 2MB)
    ↓
Check for duplicates
    ↓
Upload to Azure Blob Storage
    ↓
Create background job
    ↓
Azure Content Understanding (extract contract data)
    ↓
Process through main_contracts pipeline
    ↓
Load into CosmosDB (parent + clauses + chunks)
    ↓
Toast notification + refresh list
```

---

## Files to Create/Modify

### Backend (7 files)

1. **.env** - Add Azure CU config
2. **config_service.py** - Add config methods
3. **content_understanding_service.py** - NEW service
4. **job_models.py** - Add CONTRACT_UPLOAD type
5. **blob_storage_service.py** - Add duplicate check
6. **web_app.py** - Add upload endpoints
7. **background_worker.py** - Add job processor

### Frontend (5 files)

1. **contract-upload.service.ts** - NEW service
2. **contract-upload-modal.component.ts** - NEW modal
3. **contract-upload-modal.component.html** - NEW template
4. **contract-upload-modal.component.scss** - NEW styles
5. **contracts-list.component.ts** - Add upload button

---

## Key Configuration

```bash
# .env
CAIG_CONTENT_UNDERSTANDING_ENDPOINT="https://aif-inf-sl-dev-westus-001.services.ai.azure.com/"
CAIG_CONTENT_UNDERSTANDING_KEY="9ckDJiwB6762WEVxviqBjnJQ7Am7C2psv5KozggJQyLF28mv1Pq1JQQJ99BGAC4f1cMXJ3w3AAAAACOGT9GT"
CAIG_CONTENT_UNDERSTANDING_ANALYZER_ID="contract_extraction"
CAIG_CONTENT_UNDERSTANDING_API_VERSION="2025-05-01-preview"
CAIG_CONTRACT_UPLOAD_MAX_SIZE_MB="2"
CAIG_CONTRACT_UPLOAD_DEFAULT_USER="system_admin"
```

---

## API Endpoints

### POST /api/contracts/check-duplicate
Check if filename exists
```json
Request: { "filename": "contract.pdf" }
Response: {
  "exists": true,
  "filename": "contract.pdf",
  "suggested_filename": "contract_1.pdf"
}
```

### POST /api/contracts/upload
Upload contract file
```
multipart/form-data:
  - file: [PDF bytes]
  - uploaded_by: "user_id" (optional)

Response: {
  "success": true,
  "job_id": "job_1234567890_abc123",
  "filename": "contract.pdf",
  "message": "Contract uploaded successfully and queued for processing"
}
```

### GET /api/contracts/upload-job/{job_id}
Get upload job status
```json
Response: {
  "job_id": "job_1234567890_abc123",
  "status": "processing",
  "progress": {
    "current_step": "extracting",
    "percentage": 45.0,
    "message": "Extracting contract data..."
  }
}
```

---

## Progress Stages

1. **Uploading** (0-10%): File upload to blob storage
2. **Extracting** (10-50%): Azure Content Understanding extraction
3. **Processing** (50-90%): Generate embeddings, process clauses
4. **Loading** (90-95%): Save to CosmosDB
5. **Completed** (100%): Success!

---

## Error Handling

| Error | Handling |
|-------|----------|
| Non-PDF file | Reject on client, show error |
| File > 2MB | Reject on client, show error |
| Duplicate filename | Warn, allow proceed with suffix |
| Upload failure | Show error, allow retry |
| Azure CU failure | Mark as failed, store PDF anyway |
| Processing failure | Mark as failed, allow manual retry |

---

## Testing Checklist

- [ ] Upload valid PDF < 2MB → Success
- [ ] Upload PDF > 2MB → Error message
- [ ] Upload non-PDF → Error message
- [ ] Upload duplicate → Warning + auto-rename
- [ ] Drag and drop → Works
- [ ] File picker → Works
- [ ] Progress tracking → Updates correctly
- [ ] Toast notification → Shows on completion
- [ ] Contract appears in list → Refreshes automatically
- [ ] PDF viewable → Opens from blob storage
- [ ] Compliance evaluated → Rules run automatically
- [ ] Entities extracted → Contractor/contracting parties found

---

## Security Notes

⚠️ **Current Implementation**
- No user authentication (using default user)
- No virus scanning
- Basic file type validation only

✅ **Future Enhancements**
- Integrate Azure AD authentication
- Add virus scanning with Azure Defender
- Implement role-based access control
- Add audit logging

---

## Performance

- **Upload**: < 5 seconds for 2MB file
- **Azure CU**: 30-60 seconds for contract extraction
- **Processing**: 10-30 seconds for embeddings and CosmosDB
- **Total**: 60-120 seconds end-to-end

---

## Monitoring

Key metrics to track:
- Upload success rate
- Azure CU extraction accuracy
- Average processing time
- Error rates by stage
- User activity (uploads per day/user)

---

## Troubleshooting

### Upload fails immediately
- Check blob storage connection string
- Verify blob container exists
- Check file size and type

### Job stuck at "extracting"
- Check Azure Content Understanding key
- Verify analyzer ID is correct
- Check endpoint URL
- Review Azure CU quota/limits

### Job fails at "processing"
- Check CosmosDB connection
- Verify containers exist (contracts, contract_clauses, contract_chunks)
- Check AI service for embeddings
- Review logs for detailed error

### Contract not appearing in list
- Check job completed successfully
- Verify CosmosDB write succeeded
- Refresh contracts list manually
- Check container name matches config

---

## Next Steps

1. Review implementation plan
2. Add configuration to .env
3. Implement backend (Phase 1)
4. Test backend endpoints
5. Implement frontend (Phase 2)
6. End-to-end testing (Phase 3)
7. Deploy to production (Phase 4)

---

**Estimated Time**: 18-25 hours total

**Dependencies**:
- Azure Blob Storage (configured ✅)
- Azure Content Understanding (key provided ✅)
- CosmosDB (configured ✅)
- JobService (exists ✅)
- Background worker (exists ✅)

**Risk Level**: Low - leverages existing infrastructure

**Breaking Changes**: None - all new functionality
