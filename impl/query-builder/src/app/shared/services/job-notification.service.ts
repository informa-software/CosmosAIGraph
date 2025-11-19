/**
 * Job Notification Service
 *
 * Service for receiving real-time job updates via Server-Sent Events (SSE).
 * Manages EventSource connections and emits job updates to subscribers.
 */

import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import {
  JobUpdateEvent,
  JobsUpdateEvent,
  HeartbeatEvent,
  ErrorEvent,
  JobCounts
} from '../models/job.models';

@Injectable({
  providedIn: 'root'
})
export class JobNotificationService implements OnDestroy {
  private readonly baseUrl = 'https://localhost:8000/api/jobs';

  // Single job stream
  private jobEventSource: EventSource | null = null;
  private jobUpdateSubject = new Subject<JobUpdateEvent>();
  private jobErrorSubject = new Subject<ErrorEvent>();

  // User jobs stream
  private userJobsEventSource: EventSource | null = null;
  private jobsUpdateSubject = new Subject<JobsUpdateEvent>();
  private jobsErrorSubject = new Subject<ErrorEvent>();

  // Job counts for badge
  private jobCountsSubject = new BehaviorSubject<JobCounts>({
    queued: 0,
    processing: 0,
    completed: 0,
    failed: 0,
    cancelled: 0
  });

  // Connection status
  private connectionStatusSubject = new BehaviorSubject<{
    singleJob: boolean;
    userJobs: boolean;
  }>({
    singleJob: false,
    userJobs: false
  });

  constructor() {}

  // ============================================================================
  // Single Job Progress Stream
  // ============================================================================

  /**
   * Subscribe to progress updates for a specific job
   */
  subscribeToJob(jobId: string, userId: string = 'system'): Observable<JobUpdateEvent> {
    this.disconnectJobStream();

    const url = `${this.baseUrl}/${jobId}/stream?user_id=${userId}`;
    this.jobEventSource = new EventSource(url);

    this.jobEventSource.addEventListener('job_update', (event: MessageEvent) => {
      try {
        const data: JobUpdateEvent = JSON.parse(event.data);
        this.jobUpdateSubject.next(data);
      } catch (error) {
        console.error('Error parsing job_update event:', error);
      }
    });

    this.jobEventSource.addEventListener('heartbeat', (event: MessageEvent) => {
      // Heartbeat received - connection is alive
      console.debug('Job stream heartbeat received');
    });

    this.jobEventSource.addEventListener('error', (event: MessageEvent) => {
      try {
        if (event.data) {
          const data: ErrorEvent = JSON.parse(event.data);
          this.jobErrorSubject.next(data);
        }
      } catch (error) {
        console.error('Error parsing error event:', error);
      }

      // Connection error - will auto-retry
      this.disconnectJobStream();
    });

    this.jobEventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      this.disconnectJobStream();
    };

    this.updateConnectionStatus('singleJob', true);

    return this.jobUpdateSubject.asObservable();
  }

  /**
   * Disconnect from single job stream
   */
  disconnectJobStream(): void {
    if (this.jobEventSource) {
      this.jobEventSource.close();
      this.jobEventSource = null;
      this.updateConnectionStatus('singleJob', false);
    }
  }

  /**
   * Get job update observable
   */
  getJobUpdates(): Observable<JobUpdateEvent> {
    return this.jobUpdateSubject.asObservable();
  }

  /**
   * Get job error observable
   */
  getJobErrors(): Observable<ErrorEvent> {
    return this.jobErrorSubject.asObservable();
  }

  // ============================================================================
  // User Jobs Stream
  // ============================================================================

  /**
   * Subscribe to updates for all user jobs
   */
  subscribeToUserJobs(
    userId: string = 'system',
    statusFilter?: string
  ): Observable<JobsUpdateEvent> {
    this.disconnectUserJobsStream();

    let url = `${this.baseUrl}/user/${userId}/stream`;
    if (statusFilter) {
      url += `?status=${statusFilter}`;
    }

    this.userJobsEventSource = new EventSource(url);

    this.userJobsEventSource.addEventListener('jobs_update', (event: MessageEvent) => {
      try {
        const data: JobsUpdateEvent = JSON.parse(event.data);
        this.jobsUpdateSubject.next(data);

        // Update job counts for badge
        if (data.counts) {
          this.jobCountsSubject.next(data.counts);
        }
      } catch (error) {
        console.error('Error parsing jobs_update event:', error);
      }
    });

    this.userJobsEventSource.addEventListener('heartbeat', (event: MessageEvent) => {
      console.debug('User jobs stream heartbeat received');
    });

    this.userJobsEventSource.addEventListener('error', (event: MessageEvent) => {
      try {
        if (event.data) {
          const data: ErrorEvent = JSON.parse(event.data);
          this.jobsErrorSubject.next(data);
        }
      } catch (error) {
        console.error('Error parsing error event:', error);
      }

      this.disconnectUserJobsStream();
    });

    this.userJobsEventSource.onerror = (error) => {
      console.error('EventSource error:', error);
      this.disconnectUserJobsStream();
    };

    this.updateConnectionStatus('userJobs', true);

    return this.jobsUpdateSubject.asObservable();
  }

  /**
   * Disconnect from user jobs stream
   */
  disconnectUserJobsStream(): void {
    if (this.userJobsEventSource) {
      this.userJobsEventSource.close();
      this.userJobsEventSource = null;
      this.updateConnectionStatus('userJobs', false);
    }
  }

  /**
   * Get user jobs update observable
   */
  getUserJobsUpdates(): Observable<JobsUpdateEvent> {
    return this.jobsUpdateSubject.asObservable();
  }

  /**
   * Get user jobs error observable
   */
  getUserJobsErrors(): Observable<ErrorEvent> {
    return this.jobsErrorSubject.asObservable();
  }

  // ============================================================================
  // Job Counts (for badge)
  // ============================================================================

  /**
   * Get job counts observable
   */
  getJobCounts(): Observable<JobCounts> {
    return this.jobCountsSubject.asObservable();
  }

  /**
   * Get current active jobs count (queued + processing)
   */
  getActiveJobsCount(): number {
    const counts = this.jobCountsSubject.value;
    return counts.queued + counts.processing;
  }

  // ============================================================================
  // Connection Status
  // ============================================================================

  /**
   * Get connection status observable
   */
  getConnectionStatus(): Observable<{ singleJob: boolean; userJobs: boolean }> {
    return this.connectionStatusSubject.asObservable();
  }

  /**
   * Check if connected to any stream
   */
  isConnected(): boolean {
    const status = this.connectionStatusSubject.value;
    return status.singleJob || status.userJobs;
  }

  private updateConnectionStatus(
    stream: 'singleJob' | 'userJobs',
    connected: boolean
  ): void {
    const current = this.connectionStatusSubject.value;
    this.connectionStatusSubject.next({
      ...current,
      [stream]: connected
    });
  }

  // ============================================================================
  // Cleanup
  // ============================================================================

  /**
   * Disconnect all streams
   */
  disconnectAll(): void {
    this.disconnectJobStream();
    this.disconnectUserJobsStream();
  }

  ngOnDestroy(): void {
    this.disconnectAll();
  }
}
