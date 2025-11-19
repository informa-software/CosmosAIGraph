# Contract Upload Implementation Plan

## Overview

Add contract upload capability to the Contract Workbench, allowing users to upload PDF contracts that will be:
1. Uploaded to Azure Blob Storage
2. Processed through Azure Content Understanding (contract extraction analyzer)
3. Loaded into CosmosDB with full entity extraction and vector embeddings
4. Available immediately in the contracts list

## Requirements Summary

- **UI**: Upload button + drag-and-drop modal + file picker
- **Processing**: Asynchronous with job tracking
- **File Validation**: PDF only, max 2MB
- **Duplicate Handling**: Warn user, allow proceed with numbered suffix (file_1.pdf, file_2.pdf)
- **Filename Strategy**: Use original filename (with suffix if duplicate)
- **Error Handling**: Store PDF, mark status, allow retry
- **Progress Tracking**: Real-time progress display
- **User Tracking**: Track uploader (default user: "system_admin" until auth implemented)
- **Azure CU Config**: analyzer_id="contract_extraction", endpoint: https://aif-inf-sl-dev-westus-001.services.ai.azure.com/
- **Post-Upload**: Show in list, toast notification, no redirect

---

## Architecture Overview

### Processing Flow

```
1. User uploads PDF → Frontend validation (size, type)
2. Frontend → Backend: POST /api/contracts/upload
3. Backend: Check for duplicates in blob storage
4. If duplicate: Return warning, allow user to confirm
5. Backend: Upload to blob storage
6. Backend: Create upload job in job_queue
7. Background worker: Process job
   a. Call Azure Content Understanding API
   b. Poll for results
   c. Process JSON result through main_contracts.process_contract()
   d. Update job status
8. Frontend: Poll job status, show progress
9. Frontend: Display toast notification on completion
10. Frontend: Refresh contracts list
```

---

## Phase 1: Backend Infrastructure

### 1.1 Environment Configuration

**File**: `web_app/.env`

Add Azure Content Understanding configuration:

```bash
# Azure Content Understanding Configuration
CAIG_CONTENT_UNDERSTANDING_ENDPOINT="https://aif-inf-sl-dev-westus-001.services.ai.azure.com/"
CAIG_CONTENT_UNDERSTANDING_KEY="9ckDJiwB6762WEVxviqBjnJQ7Am7C2psv5KozggJQyLF28mv1Pq1JQQJ99BGAC4f1cMXJ3w3AAAAACOGT9GT"
CAIG_CONTENT_UNDERSTANDING_ANALYZER_ID="contract_extraction"
CAIG_CONTENT_UNDERSTANDING_API_VERSION="2025-05-01-preview"

# Upload Configuration
CAIG_CONTRACT_UPLOAD_MAX_SIZE_MB="2"
CAIG_CONTRACT_UPLOAD_DEFAULT_USER="system_admin"
```

### 1.2 Config Service Updates

**File**: `web_app/src/services/config_service.py`

Add configuration methods:

```python
@classmethod
def content_understanding_endpoint(cls) -> str:
    """Azure Content Understanding endpoint URL"""
    return cls.envvar("CAIG_CONTENT_UNDERSTANDING_ENDPOINT", "https://aif-inf-sl-dev-westus-001.services.ai.azure.com/")

@classmethod
def content_understanding_key(cls) -> str:
    """Azure Content Understanding subscription key"""
    return cls.envvar("CAIG_CONTENT_UNDERSTANDING_KEY", None)

@classmethod
def content_understanding_analyzer_id(cls) -> str:
    """Azure Content Understanding analyzer ID for contracts"""
    return cls.envvar("CAIG_CONTENT_UNDERSTANDING_ANALYZER_ID", "contract_extraction")

@classmethod
def content_understanding_api_version(cls) -> str:
    """Azure Content Understanding API version"""
    return cls.envvar("CAIG_CONTENT_UNDERSTANDING_API_VERSION", "2025-05-01-preview")

@classmethod
def contract_upload_max_size_mb(cls) -> int:
    """Maximum contract upload size in MB"""
    return cls.int_envvar("CAIG_CONTRACT_UPLOAD_MAX_SIZE_MB", 2)

@classmethod
def contract_upload_default_user(cls) -> str:
    """Default user for contract uploads"""
    return cls.envvar("CAIG_CONTRACT_UPLOAD_DEFAULT_USER", "system_admin")
```

### 1.3 Content Understanding Service (NEW)

**File**: `web_app/src/services/content_understanding_service.py`

Create service based on Azure sample code:

```python
"""
Azure Content Understanding Service

Handles contract extraction using Azure Content Understanding API.
Based on Azure sample code for contract_extraction analyzer.
"""

import logging
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


class ContentUnderstandingService:
    """Service for Azure Content Understanding API interactions"""

    def __init__(self, endpoint: str, api_version: str, subscription_key: str, analyzer_id: str):
        """
        Initialize Content Understanding Service

        Args:
            endpoint: Azure CU endpoint URL
            api_version: API version to use
            subscription_key: Subscription key for authentication
            analyzer_id: Analyzer ID (e.g., "contract_extraction")
        """
        if not subscription_key:
            raise ValueError("Subscription key must be provided")
        if not endpoint:
            raise ValueError("Endpoint must be provided")
        if not api_version:
            raise ValueError("API version must be provided")
        if not analyzer_id:
            raise ValueError("Analyzer ID must be provided")

        self.endpoint = endpoint.rstrip("/")
        self.api_version = api_version
        self.analyzer_id = analyzer_id
        self.headers = {
            "Ocp-Apim-Subscription-Key": subscription_key,
            "x-ms-useragent": "contract-intelligence-workbench"
        }

        logger.info(f"ContentUnderstandingService initialized with analyzer: {analyzer_id}")

    def analyze_document_from_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze a contract document from bytes

        Args:
            file_bytes: PDF file content as bytes
            filename: Original filename (for logging)

        Returns:
            Analysis result as JSON dict

        Raises:
            requests.HTTPError: If API request fails
            TimeoutError: If polling times out
            RuntimeError: If analysis fails
        """
        logger.info(f"Starting contract analysis for: {filename}")

        # Start analysis
        response = self._begin_analyze(file_bytes)

        # Poll for results
        result = self._poll_result(response, timeout_seconds=300, polling_interval_seconds=2)

        logger.info(f"Contract analysis completed successfully for: {filename}")
        return result

    def _begin_analyze(self, file_bytes: bytes) -> requests.Response:
        """
        Begin analysis of file bytes

        Args:
            file_bytes: PDF file content

        Returns:
            Response object with operation-location header
        """
        url = f"{self.endpoint}/contentunderstanding/analyzers/{self.analyzer_id}:analyze"
        params = {
            "api-version": self.api_version,
            "stringEncoding": "utf16"
        }
        headers = {
            **self.headers,
            "Content-Type": "application/octet-stream"
        }

        response = requests.post(url, params=params, headers=headers, data=file_bytes)
        response.raise_for_status()

        logger.info(f"Analysis started successfully")
        return response

    def _poll_result(
        self,
        response: requests.Response,
        timeout_seconds: int = 300,
        polling_interval_seconds: int = 2
    ) -> Dict[str, Any]:
        """
        Poll for analysis results until complete or timeout

        Args:
            response: Initial response with operation-location
            timeout_seconds: Maximum wait time (default: 300s = 5 min)
            polling_interval_seconds: Time between polls (default: 2s)

        Returns:
            Analysis result JSON

        Raises:
            ValueError: If operation-location not found
            TimeoutError: If operation times out
            RuntimeError: If operation fails
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers")

        start_time = time.time()
        poll_count = 0

        while True:
            elapsed_time = time.time() - start_time
            poll_count += 1

            if elapsed_time > timeout_seconds:
                raise TimeoutError(f"Analysis timed out after {timeout_seconds} seconds")

            # Poll for status
            poll_response = requests.get(operation_location, headers=self.headers)
            poll_response.raise_for_status()
            result = poll_response.json()

            status = result.get("status", "").lower()

            if status == "succeeded":
                logger.info(f"Analysis completed after {elapsed_time:.2f} seconds ({poll_count} polls)")
                return result
            elif status == "failed":
                error_msg = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"Analysis failed: {error_msg}")
                raise RuntimeError(f"Analysis failed: {error_msg}")
            else:
                # Still running
                if poll_count % 10 == 0:  # Log every 10 polls
                    logger.info(f"Analysis in progress... ({elapsed_time:.0f}s elapsed)")
                time.sleep(polling_interval_seconds)
```

### 1.4 Job Models Extension

**File**: `web_app/src/models/job_models.py`

Add new job type (verify if this exists, update if needed):

```python
class JobType(str, Enum):
    """Type of batch processing job"""
    COMPARISON = "comparison"
    QUERY = "query"
    CONTRACT_UPLOAD = "contract_upload"  # NEW

class ProcessingStep(str, Enum):
    """Current processing step for job"""
    QUEUED = "queued"
    UPLOADING = "uploading"                    # NEW
    EXTRACTING = "extracting"                   # NEW
    PROCESSING = "processing"                   # NEW
    LOADING = "loading"                         # NEW
    COMPLETED = "completed"
    FAILED = "failed"

# Add new request model
class ContractUploadJobRequest(BaseModel):
    """Request model for contract upload job"""
    filename: str
    original_filename: str
    blob_url: str
    uploaded_by: str
    file_size_bytes: int
```

### 1.5 Blob Storage Service Updates

**File**: `web_app/src/services/blob_storage_service.py`

Add duplicate check and upload methods:

```python
def check_duplicate(self, filename: str) -> bool:
    """
    Check if a file with the same name already exists

    Args:
        filename: Name of file to check

    Returns:
        True if file exists, False otherwise
    """
    return self.file_exists(filename)

def get_unique_filename(self, original_filename: str) -> str:
    """
    Generate a unique filename by adding numbered suffix if needed

    Args:
        original_filename: Original filename (e.g., "contract.pdf")

    Returns:
        Unique filename (e.g., "contract_1.pdf" if duplicate)
    """
    if not self.check_duplicate(original_filename):
        return original_filename

    # Split filename and extension
    name_parts = original_filename.rsplit('.', 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
    else:
        base_name = original_filename
        extension = ""

    # Try numbered suffixes
    counter = 1
    while counter < 1000:  # Safety limit
        new_filename = f"{base_name}_{counter}.{extension}" if extension else f"{base_name}_{counter}"
        if not self.check_duplicate(new_filename):
            return new_filename
        counter += 1

    # Fallback: use timestamp
    import time
    timestamp = int(time.time())
    return f"{base_name}_{timestamp}.{extension}" if extension else f"{base_name}_{timestamp}"

def upload_from_bytes(self, file_bytes: bytes, filename: str, overwrite: bool = False) -> str:
    """
    Upload file from bytes to blob storage

    Args:
        file_bytes: File content as bytes
        filename: Destination filename
        overwrite: Whether to overwrite if exists

    Returns:
        Blob URL (without SAS token)
    """
    blob_path = self._get_blob_path(filename)
    blob_client = self.container_client.get_blob_client(blob_path)

    # Upload the file
    blob_client.upload_blob(file_bytes, overwrite=overwrite)

    logger.info(f"Uploaded file to blob storage: {blob_path}")
    return blob_client.url
```

### 1.6 Upload API Endpoint

**File**: `web_app/web_app.py`

Add upload endpoint:

```python
from fastapi import UploadFile, File, Form, HTTPException
from src.services.content_understanding_service import ContentUnderstandingService
from src.models.job_models import JobType, ContractUploadJobRequest

# Global variable (add with other globals)
content_understanding_service: Optional[ContentUnderstandingService] = None

# Initialize in lifespan (add with other initializations)
async def initialize_content_understanding_service():
    global content_understanding_service
    try:
        endpoint = ConfigService.content_understanding_endpoint()
        key = ConfigService.content_understanding_key()
        analyzer_id = ConfigService.content_understanding_analyzer_id()
        api_version = ConfigService.content_understanding_api_version()

        if endpoint and key and analyzer_id:
            content_understanding_service = ContentUnderstandingService(
                endpoint=endpoint,
                api_version=api_version,
                subscription_key=key,
                analyzer_id=analyzer_id
            )
            logging.info("ContentUnderstandingService initialized successfully")
        else:
            logging.warning("Content Understanding not configured - upload feature disabled")
    except Exception as e:
        logging.error(f"Failed to initialize ContentUnderstandingService: {e}")
        content_understanding_service = None

# API Endpoints

@app.post("/api/contracts/check-duplicate")
async def check_duplicate_contract(filename: str = Form(...)):
    """Check if a contract filename already exists in blob storage"""
    if not blob_storage_service:
        raise HTTPException(status_code=503, detail="Blob storage not configured")

    exists = blob_storage_service.check_duplicate(filename)

    return {
        "exists": exists,
        "filename": filename,
        "suggested_filename": blob_storage_service.get_unique_filename(filename) if exists else filename
    }

@app.post("/api/contracts/upload")
async def upload_contract(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default=None)
):
    """
    Upload a contract PDF file

    Flow:
    1. Validate file (PDF, size)
    2. Check for duplicates
    3. Upload to blob storage
    4. Create processing job
    5. Return job ID for tracking
    """
    if not blob_storage_service:
        raise HTTPException(status_code=503, detail="Blob storage not configured")
    if not content_understanding_service:
        raise HTTPException(status_code=503, detail="Content Understanding not configured")
    if not job_svc:
        raise HTTPException(status_code=503, detail="Job service not configured")

    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file bytes
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        # Validate file size
        max_size_mb = ConfigService.contract_upload_max_size_mb()
        if file_size_mb > max_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum ({max_size_mb}MB)"
            )

        # Use default user if not provided
        uploader = uploaded_by or ConfigService.contract_upload_default_user()

        # Upload to blob storage
        blob_url = blob_storage_service.upload_from_bytes(
            file_bytes=file_bytes,
            filename=file.filename,
            overwrite=False
        )

        # Create upload job
        job_request = ContractUploadJobRequest(
            filename=file.filename,
            original_filename=file.filename,
            blob_url=blob_url,
            uploaded_by=uploader,
            file_size_bytes=len(file_bytes)
        )

        job_id = await job_svc.create_job(
            user_id=uploader,
            job_type=JobType.CONTRACT_UPLOAD,
            request=job_request.model_dump(),
            priority=7  # Higher priority for user-initiated uploads
        )

        logging.info(f"Contract upload job created: {job_id} for file: {file.filename}")

        return {
            "success": True,
            "job_id": job_id,
            "filename": file.filename,
            "message": "Contract uploaded successfully and queued for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uploading contract: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contracts/upload-job/{job_id}")
async def get_upload_job_status(job_id: str, user_id: str = None):
    """Get status of contract upload job"""
    if not job_svc:
        raise HTTPException(status_code=503, detail="Job service not configured")

    try:
        # Use default user if not provided
        user = user_id or ConfigService.contract_upload_default_user()

        job = await job_svc.get_job(job_id, user)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.model_dump(mode='json')

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 1.7 Background Worker for Upload Jobs

**File**: `web_app/src/services/background_worker.py`

Add contract upload job processor (update existing worker or create new method):

```python
async def process_contract_upload_job(job_id: str, job_data: Dict[str, Any]):
    """
    Process a contract upload job

    Steps:
    1. Download PDF from blob storage
    2. Call Azure Content Understanding
    3. Process result through main_contracts.process_contract()
    4. Update job status
    """
    from src.services.content_understanding_service import ContentUnderstandingService
    from src.services.blob_storage_service import BlobStorageService
    from main_contracts import process_contract

    try:
        # Update job to extracting
        await job_svc.update_job_progress(
            job_id=job_id,
            step=ProcessingStep.EXTRACTING,
            percentage=10.0,
            message="Extracting contract data with Azure Content Understanding..."
        )

        # Get file from blob storage
        request = job_data.get("request", {})
        filename = request.get("filename")

        # Download file bytes
        file_bytes = blob_storage_service.download_file_bytes(filename)

        # Call Azure Content Understanding
        cu_result = content_understanding_service.analyze_document_from_bytes(
            file_bytes=file_bytes,
            filename=filename
        )

        # Update progress
        await job_svc.update_job_progress(
            job_id=job_id,
            step=ProcessingStep.PROCESSING,
            percentage=50.0,
            message="Processing contract data and generating embeddings..."
        )

        # Prepare contract data for processing (match format from files)
        contract_data = {
            "imageQuestDocumentId": job_id,  # Use job ID as unique identifier
            "filename": filename,
            "status": "processed",
            "result": cu_result.get("result", {}),
            "uploaded_by": request.get("uploaded_by"),
            "upload_date": datetime.utcnow().isoformat()
        }

        # Process through existing pipeline
        await process_contract(
            nosql_svc=nosql_svc,
            ai_svc=ai_svc,
            contract_data=contract_data,
            cname=ConfigService.graph_source_container(),
            load_counter=Counter(),  # Create temporary counter
            compliance_svc=compliance_svc,
            compliance_enabled=True
        )

        # Update to completed
        await job_svc.update_job_progress(
            job_id=job_id,
            step=ProcessingStep.COMPLETED,
            percentage=100.0,
            message="Contract processed successfully"
        )

        await job_svc.complete_job(
            job_id=job_id,
            result={
                "contract_id": f"contract_{job_id}",
                "filename": filename,
                "status": "success"
            }
        )

    except Exception as e:
        logging.error(f"Error processing upload job {job_id}: {e}")

        await job_svc.update_job_progress(
            job_id=job_id,
            step=ProcessingStep.FAILED,
            percentage=0.0,
            message=f"Processing failed: {str(e)}"
        )

        await job_svc.fail_job(
            job_id=job_id,
            error_message=str(e)
        )
```

---

## Phase 2: Frontend Implementation

### 2.1 Upload Service

**File**: `query-builder/src/app/shared/services/contract-upload.service.ts` (NEW)

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, interval, switchMap, takeWhile, map } from 'rxjs';

export interface UploadProgress {
  percentage: number;
  step: string;
  message: string;
}

export interface UploadResult {
  success: boolean;
  job_id: string;
  filename: string;
  message: string;
}

export interface DuplicateCheckResult {
  exists: boolean;
  filename: string;
  suggested_filename: string;
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress: {
    current_step: string;
    percentage: number;
    message: string;
  };
  result?: any;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ContractUploadService {
  private apiUrl = 'https://localhost:8000/api';

  constructor(private http: HttpClient) {}

  checkDuplicate(filename: string): Observable<DuplicateCheckResult> {
    const formData = new FormData();
    formData.append('filename', filename);

    return this.http.post<DuplicateCheckResult>(
      `${this.apiUrl}/contracts/check-duplicate`,
      formData
    );
  }

  uploadContract(file: File, uploadedBy?: string): Observable<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    if (uploadedBy) {
      formData.append('uploaded_by', uploadedBy);
    }

    return this.http.post<UploadResult>(
      `${this.apiUrl}/contracts/upload`,
      formData
    );
  }

  getJobStatus(jobId: string, userId?: string): Observable<JobStatus> {
    const params = userId ? { user_id: userId } : {};

    return this.http.get<JobStatus>(
      `${this.apiUrl}/contracts/upload-job/${jobId}`,
      { params }
    );
  }

  pollJobStatus(jobId: string, userId?: string): Observable<JobStatus> {
    return interval(2000).pipe(  // Poll every 2 seconds
      switchMap(() => this.getJobStatus(jobId, userId)),
      takeWhile(status =>
        status.status === 'queued' ||
        status.status === 'processing' ||
        status.status === 'running',
        true  // Include the final status
      )
    );
  }
}
```

### 2.2 Upload Modal Component

**File**: `query-builder/src/app/contracts/contract-upload-modal/contract-upload-modal.component.ts` (NEW)

```typescript
import { Component, EventEmitter, Output, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ContractUploadService, UploadProgress, JobStatus } from '../../shared/services/contract-upload.service';

@Component({
  selector: 'app-contract-upload-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './contract-upload-modal.component.html',
  styleUrls: ['./contract-upload-modal.component.scss']
})
export class ContractUploadModalComponent {
  @Output() uploadComplete = new EventEmitter<string>();  // Emits contract ID
  @Output() close = new EventEmitter<void>();
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  // State
  showModal = false;
  isDragging = false;
  selectedFile: File | null = null;

  // Upload progress
  isUploading = false;
  uploadProgress: UploadProgress = {
    percentage: 0,
    step: '',
    message: ''
  };

  // Duplicate handling
  showDuplicateWarning = false;
  suggestedFilename = '';

  // Job tracking
  currentJobId: string | null = null;

  // Error handling
  error: string | null = null;

  // Validation
  readonly MAX_FILE_SIZE_MB = 2;
  readonly ALLOWED_TYPES = ['application/pdf'];

  constructor(private uploadService: ContractUploadService) {}

  open() {
    this.showModal = true;
    this.reset();
  }

  closeModal() {
    if (!this.isUploading) {
      this.showModal = false;
      this.close.emit();
    }
  }

  reset() {
    this.selectedFile = null;
    this.isUploading = false;
    this.uploadProgress = { percentage: 0, step: '', message: '' };
    this.showDuplicateWarning = false;
    this.suggestedFilename = '';
    this.error = null;
    this.currentJobId = null;
    this.isDragging = false;
  }

  // Drag and drop handlers
  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFileSelection(files[0]);
    }
  }

  // File picker
  onFilePickerClick() {
    this.fileInput.nativeElement.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileSelection(input.files[0]);
    }
  }

  handleFileSelection(file: File) {
    this.error = null;

    // Validate file type
    if (!this.ALLOWED_TYPES.includes(file.type)) {
      this.error = 'Only PDF files are allowed';
      return;
    }

    // Validate file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > this.MAX_FILE_SIZE_MB) {
      this.error = `File size (${fileSizeMB.toFixed(2)}MB) exceeds maximum (${this.MAX_FILE_SIZE_MB}MB)`;
      return;
    }

    this.selectedFile = file;

    // Check for duplicates
    this.checkDuplicate(file.name);
  }

  checkDuplicate(filename: string) {
    this.uploadService.checkDuplicate(filename).subscribe({
      next: (result) => {
        if (result.exists) {
          this.showDuplicateWarning = true;
          this.suggestedFilename = result.suggested_filename;
        }
      },
      error: (error) => {
        console.error('Error checking duplicate:', error);
        // Continue anyway - duplicate check is not critical
      }
    });
  }

  proceedWithUpload() {
    this.showDuplicateWarning = false;
    this.startUpload();
  }

  cancelDuplicate() {
    this.reset();
  }

  startUpload() {
    if (!this.selectedFile) return;

    this.isUploading = true;
    this.error = null;
    this.uploadProgress = {
      percentage: 5,
      step: 'uploading',
      message: 'Uploading file to server...'
    };

    this.uploadService.uploadContract(this.selectedFile).subscribe({
      next: (result) => {
        if (result.success) {
          this.currentJobId = result.job_id;
          this.trackJobProgress(result.job_id);
        } else {
          this.error = result.message || 'Upload failed';
          this.isUploading = false;
        }
      },
      error: (error) => {
        console.error('Upload error:', error);
        this.error = error.error?.detail || 'Failed to upload contract';
        this.isUploading = false;
      }
    });
  }

  trackJobProgress(jobId: string) {
    this.uploadService.pollJobStatus(jobId).subscribe({
      next: (status: JobStatus) => {
        this.uploadProgress = {
          percentage: status.progress.percentage,
          step: status.progress.current_step,
          message: status.progress.message
        };

        if (status.status === 'completed') {
          this.handleUploadSuccess(status);
        } else if (status.status === 'failed') {
          this.handleUploadError(status.error || 'Processing failed');
        }
      },
      error: (error) => {
        console.error('Job tracking error:', error);
        this.error = 'Failed to track upload progress';
        this.isUploading = false;
      }
    });
  }

  handleUploadSuccess(status: JobStatus) {
    this.isUploading = false;

    // Emit contract ID to parent
    const contractId = status.result?.contract_id;
    if (contractId) {
      this.uploadComplete.emit(contractId);
    }

    // Close modal after brief delay
    setTimeout(() => {
      this.closeModal();
    }, 1500);
  }

  handleUploadError(errorMessage: string) {
    this.error = errorMessage;
    this.isUploading = false;
  }

  getProgressBarClass(): string {
    if (this.uploadProgress.percentage === 100) {
      return 'progress-success';
    } else if (this.error) {
      return 'progress-error';
    }
    return 'progress-active';
  }
}
```

### 2.3 Upload Modal Template

**File**: `query-builder/src/app/contracts/contract-upload-modal/contract-upload-modal.component.html` (NEW)

```html
<!-- Modal Overlay -->
<div class="modal-overlay" *ngIf="showModal" (click)="closeModal()">
  <div class="modal-content" (click)="$event.stopPropagation()">

    <!-- Header -->
    <div class="modal-header">
      <h2>Upload Contract</h2>
      <button class="close-btn" (click)="closeModal()" [disabled]="isUploading">×</button>
    </div>

    <!-- Body -->
    <div class="modal-body">

      <!-- File Selection (shown when not uploading) -->
      <div *ngIf="!isUploading && !selectedFile" class="upload-area">

        <!-- Drag & Drop Zone -->
        <div
          class="drop-zone"
          [class.dragging]="isDragging"
          (dragover)="onDragOver($event)"
          (dragleave)="onDragLeave($event)"
          (drop)="onDrop($event)"
          (click)="onFilePickerClick()">

          <div class="drop-zone-content">
            <svg class="upload-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>

            <p class="drop-text">
              <strong>Drag and drop</strong> your PDF here<br>
              or <span class="link-text">click to browse</span>
            </p>

            <p class="drop-hint">
              PDF files only • Max {{ MAX_FILE_SIZE_MB }}MB
            </p>
          </div>
        </div>

        <!-- Hidden file input -->
        <input
          #fileInput
          type="file"
          accept=".pdf,application/pdf"
          (change)="onFileSelected($event)"
          style="display: none">
      </div>

      <!-- File Selected (shown when file selected but not uploading) -->
      <div *ngIf="!isUploading && selectedFile && !showDuplicateWarning" class="file-selected">
        <div class="file-info">
          <svg class="file-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke-width="2"/>
            <polyline points="14 2 14 8 20 8" stroke-width="2"/>
          </svg>

          <div class="file-details">
            <p class="file-name">{{ selectedFile.name }}</p>
            <p class="file-size">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</p>
          </div>
        </div>

        <div class="file-actions">
          <button class="btn btn-secondary" (click)="reset()">Cancel</button>
          <button class="btn btn-primary" (click)="startUpload()">Upload</button>
        </div>
      </div>

      <!-- Duplicate Warning -->
      <div *ngIf="showDuplicateWarning" class="duplicate-warning">
        <div class="warning-icon">⚠️</div>
        <h3>Duplicate File Detected</h3>
        <p>A file named <strong>{{ selectedFile?.name }}</strong> already exists.</p>
        <p>If you proceed, it will be saved as: <strong>{{ suggestedFilename }}</strong></p>

        <div class="warning-actions">
          <button class="btn btn-secondary" (click)="cancelDuplicate()">Cancel</button>
          <button class="btn btn-warning" (click)="proceedWithUpload()">Proceed Anyway</button>
        </div>
      </div>

      <!-- Upload Progress -->
      <div *ngIf="isUploading" class="upload-progress">
        <div class="progress-info">
          <h3>{{ uploadProgress.message }}</h3>
          <p class="progress-step">{{ uploadProgress.step }}</p>
        </div>

        <div class="progress-bar-container">
          <div
            class="progress-bar"
            [class]="getProgressBarClass()"
            [style.width.%]="uploadProgress.percentage">
          </div>
        </div>

        <p class="progress-percentage">{{ uploadProgress.percentage.toFixed(0) }}%</p>

        <div class="progress-stages">
          <div class="stage" [class.active]="uploadProgress.step === 'uploading'" [class.completed]="uploadProgress.percentage > 10">
            <div class="stage-icon">📤</div>
            <div class="stage-label">Uploading</div>
          </div>
          <div class="stage" [class.active]="uploadProgress.step === 'extracting'" [class.completed]="uploadProgress.percentage > 50">
            <div class="stage-icon">🔍</div>
            <div class="stage-label">Extracting</div>
          </div>
          <div class="stage" [class.active]="uploadProgress.step === 'processing'" [class.completed]="uploadProgress.percentage > 70">
            <div class="stage-icon">⚙️</div>
            <div class="stage-label">Processing</div>
          </div>
          <div class="stage" [class.active]="uploadProgress.step === 'completed'" [class.completed]="uploadProgress.percentage === 100">
            <div class="stage-icon">✅</div>
            <div class="stage-label">Complete</div>
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div *ngIf="error" class="error-message">
        <svg class="error-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10" stroke-width="2"/>
          <line x1="12" y1="8" x2="12" y2="12" stroke-width="2" stroke-linecap="round"/>
          <line x1="12" y1="16" x2="12.01" y2="16" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p>{{ error }}</p>
      </div>

    </div>
  </div>
</div>
```

### 2.4 Upload Modal Styles

**File**: `query-builder/src/app/contracts/contract-upload-modal/contract-upload-modal.component.scss` (NEW)

(Styles for modal, drag-drop zone, progress indicators - full CSS provided in separate file)

### 2.5 Update Contracts List Component

**File**: `query-builder/src/app/contracts/contracts-list/contracts-list.component.ts`

Add upload button and modal integration:

```typescript
import { ContractUploadModalComponent } from '../contract-upload-modal/contract-upload-modal.component';

@Component({
  // ... existing config
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    ContractUploadModalComponent  // Add this
  ],
})
export class ContractsListComponent implements OnInit {
  @ViewChild(ContractUploadModalComponent) uploadModal!: ContractUploadModalComponent;

  // ... existing properties

  openUploadModal() {
    this.uploadModal.open();
  }

  onUploadComplete(contractId: string) {
    // Show toast notification
    this.showToast(`Contract uploaded successfully!`, 'success');

    // Refresh contracts list
    this.loadContracts();
  }

  showToast(message: string, type: 'success' | 'error' | 'info') {
    // Simple toast implementation (can use a library like ngx-toastr)
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 100);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        document.body.removeChild(toast);
      }, 300);
    }, 3000);
  }
}
```

### 2.6 Update Contracts List Template

**File**: `query-builder/src/app/contracts/contracts-list/contracts-list.component.html`

Add upload button in toolbar:

```html
<!-- Add near the top, after filters -->
<div class="toolbar">
  <button class="btn btn-primary upload-btn" (click)="openUploadModal()">
    📤 Upload Contract
  </button>

  <!-- ... existing filter controls -->
</div>

<!-- Add modal at bottom -->
<app-contract-upload-modal
  (uploadComplete)="onUploadComplete($event)"
  (close)="uploadModal.closeModal()">
</app-contract-upload-modal>
```

---

## Phase 3: Testing & Validation

### Test Cases

1. **File Validation**
   - Upload non-PDF file → Should reject
   - Upload file > 2MB → Should reject
   - Upload valid PDF < 2MB → Should accept

2. **Duplicate Detection**
   - Upload file with existing name → Should warn
   - Proceed with duplicate → Should save as filename_1.pdf
   - Upload again → Should save as filename_2.pdf

3. **Upload Progress**
   - Track progress through all stages
   - Verify percentage updates
   - Confirm completion notification

4. **Error Handling**
   - Network failure during upload
   - Azure CU API failure
   - Processing failure
   - Verify error messages displayed

5. **Integration**
   - Uploaded contract appears in list
   - PDF viewable from blob storage
   - Compliance rules evaluated
   - Entities extracted correctly

---

## Phase 4: Deployment Checklist

- [ ] Add environment variables to production .env
- [ ] Verify Azure Content Understanding endpoint and key
- [ ] Test blob storage upload permissions
- [ ] Verify CosmosDB containers exist
- [ ] Test background worker is running
- [ ] Configure monitoring/alerts for upload failures
- [ ] Test end-to-end upload flow
- [ ] Verify duplicate detection works
- [ ] Test progress tracking
- [ ] Verify toast notifications display

---

## Dependencies

### Backend
- `requests` (already installed)
- No new Python packages required

### Frontend
- No new npm packages required
- Uses existing Angular features

---

## Security Considerations

1. **File Upload Security**
   - Validate file type on both client and server
   - Scan for malicious content (future enhancement)
   - Limit file size to prevent DoS

2. **Authentication**
   - Currently using default user
   - TODO: Integrate with proper auth system

3. **Authorization**
   - Currently no restrictions
   - TODO: Add role-based access control

4. **Blob Storage**
   - Files uploaded with private access
   - SAS URLs generated on-demand with expiry

---

## Future Enhancements

1. **Batch Upload**: Upload multiple contracts at once
2. **Virus Scanning**: Integrate with Azure Defender
3. **OCR Support**: Handle scanned PDFs
4. **Version Control**: Track contract revisions
5. **User Authentication**: Integrate with Azure AD
6. **Notifications**: Email/SMS when processing complete
7. **Retry Logic**: Automatic retry on transient failures
8. **Analytics**: Track upload metrics and success rates

---

## Estimated Timeline

- Phase 1 (Backend): 6-8 hours
- Phase 2 (Frontend): 6-8 hours
- Phase 3 (Testing): 4-6 hours
- Phase 4 (Deployment): 2-3 hours

**Total**: 18-25 hours

---

## Questions Before Implementation

1. Should we implement all phases at once or incrementally?
2. Do you want to review the backend implementation before starting frontend?
3. Should we add any additional validation or security measures?
4. Do you want to implement email notifications for upload completion?

---

**Status**: Implementation plan complete, ready for approval and execution.
