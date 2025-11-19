import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { catchError, map, switchMap, takeWhile, tap } from 'rxjs/operators';

/**
 * Response from duplicate check endpoint
 */
export interface DuplicateCheckResponse {
  exists: boolean;
  filename: string;
  suggested_filename: string;
}

/**
 * Response from upload endpoint
 */
export interface UploadResponse {
  success: boolean;
  job_id: string;
  filename: string;
  message: string;
}

/**
 * Job status response
 */
export interface UploadJobStatus {
  id: string;
  job_id: string;
  job_type: string;
  user_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  priority: number;
  request: {
    filename: string;
    original_filename: string;
    blob_url: string;
    uploaded_by: string;
    file_size_bytes: number;
  };
  progress: {
    current_step: string;
    current_item: number;
    total_items: number;
    percentage: number;
    message: string;
    estimated_time_remaining?: number;
  };
  result_id?: string;
  error_message?: string;
  error_details?: any;
  created_date: string;
  started_date?: string;
  completed_date?: string;
  elapsed_time?: number;
  ttl: number;
}

/**
 * Progress update event
 */
export interface UploadProgress {
  percentage: number;
  stage: 'uploading' | 'processing' | 'completed' | 'error';
  message: string;
  jobId?: string;
}

@Injectable({
  providedIn: 'root'
})
export class ContractUploadService {
  private apiUrl = 'https://localhost:8000/api'; // Backend API URL

  constructor(private http: HttpClient) {}

  /**
   * Check if a filename already exists in blob storage
   */
  checkDuplicate(filename: string): Observable<DuplicateCheckResponse> {
    const formData = new FormData();
    formData.append('filename', filename);

    return this.http.post<DuplicateCheckResponse>(
      `${this.apiUrl}/contracts/check-duplicate`,
      formData
    ).pipe(
      catchError(error => {
        console.error('Duplicate check failed:', error);
        return throwError(() => new Error('Failed to check for duplicate filename'));
      })
    );
  }

  /**
   * Upload a contract PDF file
   *
   * @param file The PDF file to upload
   * @param uploadedBy Username of person uploading (optional)
   * @returns Observable with upload response including job_id
   */
  uploadContract(file: File, uploadedBy?: string): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    if (uploadedBy) {
      formData.append('uploaded_by', uploadedBy);
    }

    return this.http.post<UploadResponse>(
      `${this.apiUrl}/contracts/upload`,
      formData
    ).pipe(
      catchError(error => {
        console.error('Upload failed:', error);
        let errorMessage = 'Failed to upload contract';

        if (error.error?.detail) {
          errorMessage = error.error.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }

        return throwError(() => new Error(errorMessage));
      })
    );
  }

  /**
   * Get the status of an upload job
   *
   * @param jobId The job ID to check
   * @param userId User ID (optional)
   * @returns Observable with job status
   */
  getJobStatus(jobId: string, userId?: string): Observable<UploadJobStatus> {
    let url = `${this.apiUrl}/contracts/upload-job/${jobId}`;
    if (userId) {
      url += `?user_id=${userId}`;
    }

    return this.http.get<UploadJobStatus>(url).pipe(
      catchError(error => {
        console.error('Failed to get job status:', error);
        return throwError(() => new Error('Failed to retrieve job status'));
      })
    );
  }

  /**
   * Poll job status until completion or error
   *
   * @param jobId The job ID to poll
   * @param userId User ID (optional)
   * @param pollingInterval Milliseconds between polls (default: 2000)
   * @param maxAttempts Maximum number of polling attempts (default: 150, i.e., 5 minutes)
   * @returns Observable that emits job status updates and completes when job finishes
   */
  pollJobStatus(
    jobId: string,
    userId?: string,
    pollingInterval: number = 2000,
    maxAttempts: number = 150
  ): Observable<UploadJobStatus> {
    let attemptCount = 0;

    return timer(0, pollingInterval).pipe(
      // Stop polling after max attempts
      takeWhile(() => attemptCount < maxAttempts),
      // Fetch job status
      switchMap(() => {
        attemptCount++;
        return this.getJobStatus(jobId, userId);
      }),
      // Stop polling when job is complete, failed, or cancelled
      takeWhile(status => {
        return status.status !== 'completed' &&
               status.status !== 'failed' &&
               status.status !== 'cancelled';
      }, true), // true = include the final emission
      // Error handling
      catchError(error => {
        console.error('Job polling failed:', error);
        return throwError(() => error);
      })
    );
  }

  /**
   * Validate file before upload
   *
   * @param file File to validate
   * @param maxSizeMB Maximum file size in MB (default: 2)
   * @returns Error message if invalid, null if valid
   */
  validateFile(file: File, maxSizeMB: number = 2): string | null {
    // Check file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return 'Only PDF files are allowed';
    }

    // Check file size
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return `File size (${sizeMB}MB) exceeds maximum (${maxSizeMB}MB)`;
    }

    return null;
  }

  /**
   * Format file size for display
   *
   * @param bytes File size in bytes
   * @returns Formatted string (e.g., "1.5 MB")
   */
  formatFileSize(bytes: number): string {
    if (bytes < 1024) {
      return bytes + ' B';
    } else if (bytes < 1024 * 1024) {
      return (bytes / 1024).toFixed(1) + ' KB';
    } else {
      return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }
  }

  /**
   * Get user-friendly status message
   *
   * @param status Job status object
   * @returns Display-friendly status message
   */
  getStatusMessage(status: UploadJobStatus): string {
    if (status.status === 'completed') {
      return 'Upload completed successfully';
    } else if (status.status === 'failed') {
      return status.error_message || 'Upload failed';
    } else if (status.status === 'cancelled') {
      return 'Upload cancelled';
    } else if (status.progress) {
      return status.progress.message;
    } else {
      return 'Processing...';
    }
  }

  /**
   * Get progress percentage from job status
   *
   * @param status Job status object
   * @returns Progress percentage (0-100)
   */
  getProgressPercentage(status: UploadJobStatus): number {
    if (status.status === 'completed') {
      return 100;
    } else if (status.progress) {
      return status.progress.percentage;
    }
    return 0;
  }
}
