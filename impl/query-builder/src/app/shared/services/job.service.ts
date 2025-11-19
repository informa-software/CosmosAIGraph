/**
 * Job Service
 *
 * Service for managing batch processing jobs.
 * Handles job submission, status checking, cancellation, and retry operations.
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BatchJob,
  JobStatus,
  JobType,
  SubmitJobRequest,
  SubmitJobResponse,
  JobStatusResponse,
  UserJobsResponse,
  CancelJobResponse,
  RetryJobResponse,
  DeleteJobResponse
} from '../models/job.models';

@Injectable({
  providedIn: 'root'
})
export class JobService {
  private readonly baseUrl = 'https://localhost:8000/api/jobs';

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Job Submission
  // ============================================================================

  /**
   * Submit a contract comparison batch job
   */
  submitComparisonJob(
    request: SubmitJobRequest,
    userId: string = 'system'
  ): Observable<SubmitJobResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.post<SubmitJobResponse>(
      `${this.baseUrl}/comparison`,
      request,
      { params }
    );
  }

  /**
   * Submit a contract query batch job
   */
  submitQueryJob(
    request: SubmitJobRequest,
    userId: string = 'system'
  ): Observable<SubmitJobResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.post<SubmitJobResponse>(
      `${this.baseUrl}/query`,
      request,
      { params }
    );
  }

  // ============================================================================
  // Job Status & Retrieval
  // ============================================================================

  /**
   * Get status and details of a specific job
   */
  getJobStatus(
    jobId: string,
    userId: string = 'system'
  ): Observable<JobStatusResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.get<JobStatusResponse>(
      `${this.baseUrl}/${jobId}`,
      { params }
    );
  }

  /**
   * Get all jobs for a user with optional filtering
   */
  getUserJobs(
    userId: string = 'system',
    statusFilter?: JobStatus[],
    jobTypeFilter?: JobType,
    limit: number = 50
  ): Observable<UserJobsResponse> {
    let params = new HttpParams();

    if (statusFilter && statusFilter.length > 0) {
      params = params.set('status', statusFilter.join(','));
    }

    if (jobTypeFilter) {
      params = params.set('job_type', jobTypeFilter);
    }

    params = params.set('limit', limit.toString());

    return this.http.get<UserJobsResponse>(
      `${this.baseUrl}/user/${userId}`,
      { params }
    );
  }

  // ============================================================================
  // Job Management
  // ============================================================================

  /**
   * Cancel a queued or processing job
   */
  cancelJob(
    jobId: string,
    userId: string = 'system'
  ): Observable<CancelJobResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.post<CancelJobResponse>(
      `${this.baseUrl}/${jobId}/cancel`,
      {},
      { params }
    );
  }

  /**
   * Retry a failed job by creating a new job with the same parameters
   */
  retryJob(
    jobId: string,
    userId: string = 'system'
  ): Observable<RetryJobResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.post<RetryJobResponse>(
      `${this.baseUrl}/${jobId}/retry`,
      {},
      { params }
    );
  }

  /**
   * Delete a job (only for completed/failed/cancelled jobs)
   */
  deleteJob(
    jobId: string,
    userId: string = 'system'
  ): Observable<DeleteJobResponse> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.delete<DeleteJobResponse>(
      `${this.baseUrl}/${jobId}`,
      { params }
    );
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  /**
   * Check if job service is healthy
   */
  healthCheck(): Observable<{ status: string; service: string; timestamp: string }> {
    return this.http.get<{ status: string; service: string; timestamp: string }>(
      `${this.baseUrl}/health`
    );
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  /**
   * Check if a job is in a final state (completed, failed, or cancelled)
   */
  isJobFinal(status: JobStatus): boolean {
    return [
      JobStatus.COMPLETED,
      JobStatus.FAILED,
      JobStatus.CANCELLED
    ].includes(status);
  }

  /**
   * Check if a job can be cancelled
   */
  canCancelJob(status: JobStatus): boolean {
    return [JobStatus.QUEUED, JobStatus.PROCESSING].includes(status);
  }

  /**
   * Check if a job can be retried
   */
  canRetryJob(status: JobStatus): boolean {
    return status === JobStatus.FAILED;
  }

  /**
   * Check if job results can be viewed
   */
  canViewResults(job: BatchJob): boolean {
    return job.status === JobStatus.COMPLETED && !!job.result_id;
  }

  /**
   * Get display-friendly job type name
   */
  getJobTypeName(jobType: JobType): string {
    switch (jobType) {
      case JobType.CONTRACT_COMPARISON:
        return 'Contract Comparison';
      case JobType.CONTRACT_QUERY:
        return 'Contract Query';
      case JobType.CONTRACT_UPLOAD:
        return 'Contract Upload';
      default:
        return 'Unknown Job';
    }
  }

  /**
   * Get display-friendly status name
   */
  getStatusName(status: JobStatus): string {
    switch (status) {
      case JobStatus.QUEUED:
        return 'Queued';
      case JobStatus.PROCESSING:
        return 'Processing';
      case JobStatus.COMPLETED:
        return 'Completed';
      case JobStatus.FAILED:
        return 'Failed';
      case JobStatus.CANCELLED:
        return 'Cancelled';
      default:
        return 'Unknown';
    }
  }

  /**
   * Get status color for UI
   */
  getStatusColor(status: JobStatus): 'primary' | 'accent' | 'warn' | 'success' | 'default' {
    switch (status) {
      case JobStatus.QUEUED:
        return 'default';
      case JobStatus.PROCESSING:
        return 'accent';
      case JobStatus.COMPLETED:
        return 'success';
      case JobStatus.FAILED:
        return 'warn';
      case JobStatus.CANCELLED:
        return 'default';
      default:
        return 'default';
    }
  }

  /**
   * Get status icon for UI
   */
  getStatusIcon(status: JobStatus): string {
    switch (status) {
      case JobStatus.QUEUED:
        return 'schedule';
      case JobStatus.PROCESSING:
        return 'sync';
      case JobStatus.COMPLETED:
        return 'check_circle';
      case JobStatus.FAILED:
        return 'error';
      case JobStatus.CANCELLED:
        return 'cancel';
      default:
        return 'help';
    }
  }
}
