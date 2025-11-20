import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { JobService } from '../shared/services/job.service';
import { JobNotificationService } from '../shared/services/job-notification.service';
import { ToastService } from '../shared/services/toast.service';
import { BatchJob, JobStatus, JobType, JobsUpdateEvent } from '../shared/models/job.models';
import { ContractService } from '../contract-workbench/services/contract.service';
import { Contract } from '../contract-workbench/models/contract.models';

@Component({
  selector: 'app-jobs-page',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="jobs-page">
      <div class="jobs-header">
        <h1>⚙️ Background Jobs</h1>
        <div class="jobs-stats">
          <span class="stat">Total: {{ jobs.length }}</span>
          <span class="stat">Active: {{ activeJobCount }}</span>
        </div>
      </div>

      <div class="jobs-content">
        <!-- Empty State -->
        <div *ngIf="jobs.length === 0" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>No jobs found</p>
          <small>Batch jobs will appear here when you submit comparison or query operations</small>
        </div>

        <!-- Job List -->
        <div *ngIf="jobs.length > 0" class="job-list">
          <div *ngFor="let job of jobs" class="job-card">
            <!-- Job Header (clickable for completed jobs) -->
            <div class="job-card-header"
                 [class.clickable]="job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled'"
                 (click)="(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && toggleJobExpansion(job.job_id)">
              <div class="job-info">
                <span class="job-type-icon">{{ getJobTypeIcon(job.job_type) }}</span>
                <div class="job-details">
                  <h3>{{ getJobTypeName(job) }}</h3>
                  <small>Job ID: {{ job.job_id }}</small>
                </div>
              </div>
              <div class="job-header-actions">
                <span class="badge" [ngClass]="getJobStatusBadgeClass(job.status)">{{ job.status }}</span>
                <!-- Expansion indicator for completed jobs -->
                <span *ngIf="job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled'"
                      class="expansion-indicator">
                  {{ isJobExpanded(job.job_id) ? '▼' : '▶' }}
                </span>
                <button
                  *ngIf="job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled'"
                  (click)="deleteJob(job.job_id); $event.stopPropagation()"
                  class="btn-delete-job"
                  title="Delete this job">🗑️</button>
              </div>
            </div>

            <!-- Progress Bar (for queued/processing jobs) -->
            <div *ngIf="job.status === 'queued' || job.status === 'processing'" class="progress-section">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  [style.width.%]="job.progress.percentage"
                  [class.processing]="job.status === 'processing'">
                </div>
              </div>
              <div class="progress-text">
                <span>{{ job.progress.message }}</span>
                <span>{{ job.progress.percentage }}%</span>
              </div>
            </div>

            <!-- Job Details - 2 Column Layout (only show for expanded completed jobs or active jobs) -->
            <div *ngIf="shouldShowFullDetails(job)" class="job-details-grid">
              <!-- Left Column: Job-Specific Details -->
              <div class="job-details-left">
                <!-- Contract Upload Details -->
                <div *ngIf="job.job_type === JobType.CONTRACT_UPLOAD">
                  <div class="detail-section">
                    <div class="detail-label">Filename:</div>
                    <div class="detail-value">{{ job.request?.['filename'] }}</div>
                  </div>
                  <div class="detail-section" *ngIf="job.request?.['file_size_bytes']">
                    <div class="detail-label">File Size:</div>
                    <div class="detail-value">{{ formatFileSize(job.request['file_size_bytes']) }}</div>
                  </div>
                  <div class="detail-section" *ngIf="job.request?.['uploaded_by']">
                    <div class="detail-label">Uploaded By:</div>
                    <div class="detail-value">{{ job.request['uploaded_by'] }}</div>
                  </div>
                </div>

                <!-- Contract Query Details -->
                <div *ngIf="job.job_type === JobType.CONTRACT_QUERY">
                  <div class="detail-section">
                    <div class="detail-label">Question:</div>
                    <div class="detail-value">{{ getQueryQuestion(job) }}</div>
                  </div>
                  <div class="detail-section">
                    <div class="detail-label">Contracts:</div>
                    <div class="detail-value">
                      <div *ngFor="let contract of getQueryContracts(job)" class="contract-item">
                        • {{ contract }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Contract Comparison Details -->
                <div *ngIf="job.job_type === JobType.CONTRACT_COMPARISON">
                  <div class="detail-section">
                    <div class="detail-label">Comparison Mode:</div>
                    <div class="detail-value">{{ getComparisonMode(job) }}</div>
                  </div>
                  <div class="detail-section" *ngIf="getComparisonContracts(job) as contracts">
                    <div class="detail-label">Standard Contract:</div>
                    <div class="detail-value">{{ contracts.standard }}</div>
                  </div>
                  <div class="detail-section" *ngIf="getComparisonContracts(job) as contracts">
                    <div class="detail-label">Comparing Against:</div>
                    <div class="detail-value">
                      <div *ngFor="let contract of contracts.comparing" class="contract-item">
                        • {{ contract }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Right Column: Timestamps & Duration -->
              <div class="job-details-right">
                <div class="metadata-row">
                  <span class="label">Created:</span>
                  <span class="value">{{ formatJobTimestamp(job.created_date) }}</span>
                </div>
                <div *ngIf="job.completed_date" class="metadata-row">
                  <span class="label">Finished:</span>
                  <span class="value">{{ formatJobTimestamp(job.completed_date) }}</span>
                </div>
                <div *ngIf="job.completed_date" class="metadata-row">
                  <span class="label">Duration:</span>
                  <span class="value">{{ formatElapsedTime(job) }}</span>
                </div>
              </div>
            </div>

            <!-- Action Buttons (only show for expanded completed jobs or active jobs) -->
            <div *ngIf="shouldShowFullDetails(job)" class="job-actions">
              <button
                *ngIf="canCancelJob(job.status)"
                (click)="cancelJob(job.job_id)"
                class="btn btn-sm btn-warning">
                ⏸️ Cancel
              </button>
              <button
                *ngIf="job.status === 'failed'"
                (click)="retryJob(job.job_id)"
                class="btn btn-sm btn-primary">
                🔄 Retry
              </button>
              <button
                *ngIf="job.status === 'completed' && job.result_id"
                (click)="viewJobResult(job.result_id, job.job_type)"
                class="btn btn-sm btn-success">
                👁️ View
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .jobs-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }

    .jobs-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid #e0e0e0;
    }

    .jobs-header h1 {
      margin: 0;
      font-size: 2rem;
      color: #333;
    }

    .jobs-stats {
      display: flex;
      gap: 1.5rem;
    }

    .stat {
      font-size: 0.9rem;
      color: #666;
      font-weight: 500;
    }

    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: #999;
    }

    .empty-icon {
      font-size: 4rem;
      margin-bottom: 1rem;
    }

    .job-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .job-card {
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1.5rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .job-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      transition: background-color 0.2s;
    }

    .job-card-header.clickable {
      cursor: pointer;
      border-radius: 4px;
      padding: 0.5rem;
      margin: -0.5rem;
      margin-bottom: 0.5rem;
    }

    .job-card-header.clickable:hover {
      background-color: #f5f5f5;
    }

    .job-info {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .job-type-icon {
      font-size: 2rem;
    }

    .job-details h3 {
      margin: 0 0 0.25rem 0;
      font-size: 1.1rem;
      color: #333;
    }

    .job-details small {
      color: #666;
      font-size: 0.85rem;
    }

    .job-header-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .expansion-indicator {
      font-size: 0.9rem;
      color: #666;
      margin-left: 0.5rem;
      user-select: none;
    }

    .badge {
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 500;
    }

    .job-status-queued { background: #e3f2fd; color: #1976d2; }
    .job-status-processing { background: #fff3e0; color: #f57c00; }
    .job-status-completed { background: #e8f5e9; color: #388e3c; }
    .job-status-failed { background: #ffebee; color: #d32f2f; }
    .job-status-cancelled { background: #f5f5f5; color: #757575; }

    .btn-delete-job {
      background: transparent;
      border: none;
      color: #dc3545;
      font-size: 1.1rem;
      cursor: pointer;
      opacity: 0.7;
      transition: all 0.2s;
    }

    .btn-delete-job:hover {
      opacity: 1;
      transform: scale(1.2);
    }

    .progress-section {
      margin-bottom: 1rem;
    }

    .progress-bar {
      width: 100%;
      height: 8px;
      background: #f0f0f0;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }

    .progress-fill {
      height: 100%;
      background: #4caf50;
      transition: width 0.3s ease;
    }

    .progress-fill.processing {
      background: linear-gradient(90deg, #4caf50, #8bc34a, #4caf50);
      background-size: 200% 100%;
      animation: progressShine 2s linear infinite;
    }

    @keyframes progressShine {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .progress-text {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      color: #666;
    }

    .job-details-grid {
      display: grid;
      grid-template-columns: 1fr 350px;
      gap: 2rem;
      margin-bottom: 1rem;
      padding-top: 1rem;
      border-top: 1px solid #f0f0f0;
    }

    .job-details-left {
      min-width: 0;
    }

    .job-details-right {
      border-left: 1px solid #f0f0f0;
      padding-left: 1.5rem;
    }

    .detail-section {
      margin-bottom: 1rem;
    }

    .detail-section:last-child {
      margin-bottom: 0;
    }

    .detail-label {
      font-weight: 600;
      color: #444;
      margin-bottom: 0.5rem;
      font-size: 0.9rem;
    }

    .detail-value {
      color: #555;
      font-size: 0.9rem;
      line-height: 1.5;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }

    .contract-item {
      padding: 0.25rem 0;
      color: #555;
    }

    .metadata-row {
      display: flex;
      justify-content: space-between;
      padding: 0.4rem 0;
      font-size: 0.9rem;
    }

    .metadata-row .label {
      color: #666;
      font-weight: 500;
      margin-right: 1rem;
    }

    .metadata-row .value {
      color: #333;
      text-align: right;
    }

    .job-actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 0.2s;
    }

    .btn-sm {
      padding: 0.4rem 0.8rem;
      font-size: 0.85rem;
    }

    .btn-primary {
      background: #2196f3;
      color: white;
    }

    .btn-primary:hover {
      background: #1976d2;
    }

    .btn-success {
      background: #4caf50;
      color: white;
    }

    .btn-success:hover {
      background: #388e3c;
    }

    .btn-warning {
      background: #ff9800;
      color: white;
    }

    .btn-warning:hover {
      background: #f57c00;
    }

    .btn-danger {
      background: #f44336;
      color: white;
    }

    .btn-danger:hover {
      background: #d32f2f;
    }
  `]
})
export class JobsPageComponent implements OnInit, OnDestroy {
  jobs: BatchJob[] = [];
  activeJobCount = 0;
  contracts: Contract[] = [];
  contractsMap: Map<string, Contract> = new Map();
  expandedJobs: Set<string> = new Set();  // Track which jobs are expanded

  // Expose enums to template
  JobType = JobType;
  JobStatus = JobStatus;

  constructor(
    private jobService: JobService,
    private jobNotificationService: JobNotificationService,
    private toastService: ToastService,
    private router: Router,
    private contractService: ContractService
  ) {}

  ngOnInit(): void {
    // Load contracts for reference
    this.contractService.getContracts().subscribe({
      next: (contracts) => {
        this.contracts = contracts;
        this.contractsMap = new Map(contracts.map(c => [c.id, c]));
      },
      error: (error) => {
        console.error('Error loading contracts:', error);
      }
    });

    // Load initial jobs
    this.loadJobs();

    // Subscribe to job notifications for real-time updates
    this.jobNotificationService.subscribeToUserJobs('system');

    this.jobNotificationService.getUserJobsUpdates().subscribe({
      next: (event: JobsUpdateEvent) => {
        console.log('Received job updates:', event);
        this.activeJobCount = event.counts.queued + event.counts.processing;

        // Refresh jobs list to get latest data
        this.loadJobs();
      },
      error: (error) => {
        console.error('Error receiving job updates:', error);
      }
    });
  }

  loadJobs(): void {
    this.jobService.getUserJobs('system').subscribe({
      next: (response) => {
        console.log('Loaded jobs:', response);
        this.jobs = response.jobs;

        // Sort by created date (newest first)
        this.jobs.sort((a, b) =>
          new Date(b.created_date).getTime() - new Date(a.created_date).getTime()
        );

        // Update active job count
        this.activeJobCount = this.jobs.filter(
          j => j.status === JobStatus.QUEUED || j.status === JobStatus.PROCESSING
        ).length;
      },
      error: (error) => {
        console.error('Error loading jobs:', error);
      }
    });
  }

  ngOnDestroy(): void {
    this.jobNotificationService.disconnectUserJobsStream();
  }

  viewJobResult(resultId: string, jobType?: JobType): void {
    if (jobType === JobType.CONTRACT_QUERY) {
      this.router.navigate(['/query-contracts'], { queryParams: { resultId: resultId } });
    } else if (jobType === JobType.CONTRACT_COMPARISON) {
      this.router.navigate(['/compare-contracts'], { queryParams: { resultId: resultId } });
    } else if (jobType === JobType.CONTRACT_UPLOAD) {
      // Navigate to contracts page with contractId to open details dialog
      this.router.navigate(['/contracts'], { queryParams: { contractId: resultId } });
    } else {
      console.warn('Unknown job type, defaulting to comparison page');
      this.router.navigate(['/compare-contracts'], { queryParams: { resultId: resultId } });
    }
  }

  cancelJob(jobId: string): void {
    if (confirm('Are you sure you want to cancel this job?')) {
      this.jobService.cancelJob(jobId, 'system').subscribe({
        next: (response) => {
          this.toastService.success('Job Cancelled', response.message);

          const job = this.jobs.find(j => j.job_id === jobId);
          if (job) {
            job.status = JobStatus.CANCELLED;
            job.completed_date = new Date().toISOString();
            this.activeJobCount = this.jobs.filter(
              j => j.status === JobStatus.QUEUED || j.status === JobStatus.PROCESSING
            ).length;
          }
        },
        error: (error) => {
          console.error('Error cancelling job:', error);
          this.toastService.error('Cancel Failed', 'Failed to cancel job.');
        }
      });
    }
  }

  retryJob(jobId: string): void {
    this.jobService.retryJob(jobId, 'system').subscribe({
      next: (response) => {
        this.toastService.success('Job Retried', `New job created: ${response.new_job_id}`);
      },
      error: (error) => {
        console.error('Error retrying job:', error);
        this.toastService.error('Retry Failed', 'Failed to retry job.');
      }
    });
  }

  deleteJob(jobId: string): void {
    if (confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
      this.jobService.deleteJob(jobId, 'system').subscribe({
        next: (response) => {
          this.toastService.success('Job Deleted', response.message);
          this.jobs = this.jobs.filter(job => job.job_id !== jobId);
        },
        error: (error) => {
          console.error('Error deleting job:', error);
          this.toastService.error('Delete Failed', 'Failed to delete job.');
        }
      });
    }
  }

  canCancelJob(status: JobStatus): boolean {
    return [JobStatus.QUEUED, JobStatus.PROCESSING].includes(status);
  }

  getJobStatusBadgeClass(status: JobStatus): string {
    switch (status) {
      case JobStatus.QUEUED: return 'job-status-queued';
      case JobStatus.PROCESSING: return 'job-status-processing';
      case JobStatus.COMPLETED: return 'job-status-completed';
      case JobStatus.FAILED: return 'job-status-failed';
      case JobStatus.CANCELLED: return 'job-status-cancelled';
      default: return 'badge-secondary';
    }
  }

  getJobTypeIcon(jobType: JobType): string {
    switch (jobType) {
      case JobType.CONTRACT_COMPARISON: return '📊';
      case JobType.CONTRACT_QUERY: return '🔍';
      case JobType.CONTRACT_UPLOAD: return '⬆️';
      default: return '⚙️';
    }
  }

  getJobTypeName(job: BatchJob): string {
    // For query jobs, include first 40 chars of question
    if (job.job_type === JobType.CONTRACT_QUERY && job.request?.['question']) {
      const question = job.request['question'] as string;
      const preview = question.length > 40 ? question.substring(0, 40) + '...' : question;
      return `Contract Query: ${preview}`;
    }

    // For comparison jobs, include mode and contract count
    if (job.job_type === JobType.CONTRACT_COMPARISON) {
      const mode = this.getComparisonMode(job);
      const contracts = this.getComparisonContracts(job);
      if (mode && contracts) {
        const count = contracts.comparing.length;
        return `Contract Comparison: ${mode} (${count} contract${count !== 1 ? 's' : ''})`;
      }
    }

    // For upload jobs, show filename
    if (job.job_type === JobType.CONTRACT_UPLOAD && job.request?.['filename']) {
      const filename = job.request['filename'] as string;
      return `Contract Upload: ${filename}`;
    }

    return this.jobService.getJobTypeName(job.job_type);
  }

  getQueryQuestion(job: BatchJob): string | null {
    if (job.job_type === JobType.CONTRACT_QUERY && job.request?.['question']) {
      return job.request['question'] as string;
    }
    return null;
  }

  getQueryContracts(job: BatchJob): string[] {
    if (job.job_type === JobType.CONTRACT_QUERY && job.request?.['contract_ids']) {
      const contractIds = job.request['contract_ids'] as string[];
      return contractIds.map(id => {
        const contract = this.contractsMap.get(id);
        return contract?.title || id;
      });
    }
    return [];
  }

  getComparisonMode(job: BatchJob): string | null {
    if (job.job_type === JobType.CONTRACT_COMPARISON && job.request?.['comparisonMode']) {
      const mode = job.request['comparisonMode'] as string;
      return mode === 'full' ? 'Entire Contract' : 'Clauses';
    }
    return null;
  }

  getComparisonContracts(job: BatchJob): { standard: string; comparing: string[] } | null {
    if (job.job_type === JobType.CONTRACT_COMPARISON) {
      const standardId = job.request?.['standardContractId'] as string;
      const compareIds = job.request?.['compareContractIds'] as string[];

      if (!standardId || !compareIds) return null;

      const standardContract = this.contractsMap.get(standardId);
      const comparingContracts = compareIds.map(id => {
        const contract = this.contractsMap.get(id);
        return contract?.title || id;
      });

      return {
        standard: standardContract?.title || standardId,
        comparing: comparingContracts
      };
    }
    return null;
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  formatJobTimestamp(timestamp?: string): string {
    if (!timestamp) return 'N/A';

    try {
      // Normalize the timestamp to ensure it's treated as UTC
      let utcTimestamp = timestamp.trim();

      // Handle various timestamp formats
      if (!utcTimestamp.endsWith('Z') && !utcTimestamp.includes('+') && !utcTimestamp.includes('-', 10)) {
        // Format: "2025-01-15 10:30:00" or "2025-01-15T10:30:00" - add Z to indicate UTC
        if (!utcTimestamp.includes('T')) {
          utcTimestamp = utcTimestamp.replace(' ', 'T');
        }
        utcTimestamp += 'Z';
      }

      // Parse UTC timestamp - the Date constructor will convert to local time
      const date = new Date(utcTimestamp);

      // Check if date is valid
      if (isNaN(date.getTime())) {
        console.error('Invalid timestamp:', timestamp);
        return 'Invalid date';
      }

      // Format in browser's local timezone with explicit timezone display
      const formatted = date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
        timeZoneName: 'short'
      });

      return formatted;
    } catch (error) {
      console.error('Error formatting timestamp:', timestamp, error);
      return 'Invalid date';
    }
  }

  calculateDuration(job: BatchJob): number | null {
    if (!job.completed_date || !job.created_date) {
      return null;
    }

    // Parse timestamps as UTC
    let createdUtc = job.created_date;
    let completedUtc = job.completed_date;

    // Ensure UTC format
    if (!createdUtc.endsWith('Z') && !createdUtc.includes('+')) {
      createdUtc = createdUtc.includes('T') ? createdUtc + 'Z' : createdUtc.replace(' ', 'T') + 'Z';
    }
    if (!completedUtc.endsWith('Z') && !completedUtc.includes('+')) {
      completedUtc = completedUtc.includes('T') ? completedUtc + 'Z' : completedUtc.replace(' ', 'T') + 'Z';
    }

    const created = new Date(createdUtc);
    const completed = new Date(completedUtc);

    // Calculate difference in seconds
    const durationMs = completed.getTime() - created.getTime();
    return Math.round(durationMs / 1000);
  }

  formatElapsedTime(job: BatchJob): string {
    // Calculate duration from timestamps
    const seconds = this.calculateDuration(job);

    if (seconds === null) return 'N/A';

    // Always display in seconds
    return `${seconds}s`;
  }

  /**
   * Toggle job expansion state (for accordion behavior)
   */
  toggleJobExpansion(jobId: string): void {
    if (this.expandedJobs.has(jobId)) {
      this.expandedJobs.delete(jobId);
    } else {
      this.expandedJobs.add(jobId);
    }
  }

  /**
   * Check if a job is expanded
   */
  isJobExpanded(jobId: string): boolean {
    return this.expandedJobs.has(jobId);
  }

  /**
   * Check if a job should show full details
   * In-progress jobs always show full details
   * Completed jobs show full details only when expanded
   */
  shouldShowFullDetails(job: BatchJob): boolean {
    // Always show full details for active jobs
    if (job.status === JobStatus.QUEUED || job.status === JobStatus.PROCESSING) {
      return true;
    }
    // For completed/failed/cancelled jobs, show only when expanded
    return this.isJobExpanded(job.job_id);
  }
}
