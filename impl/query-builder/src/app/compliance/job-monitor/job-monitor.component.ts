import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ComplianceService } from '../services/compliance.service';
import { ToastService } from '../../shared/services/toast.service';
import { EvaluationJob } from '../models/compliance.models';

@Component({
  selector: 'app-job-monitor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './job-monitor.component.html',
  styleUrls: ['./job-monitor.component.scss']
})
export class JobMonitorComponent implements OnInit, OnDestroy {
  jobs: EvaluationJob[] = [];
  selectedJob: EvaluationJob | null = null;
  loading: boolean = false;
  autoRefresh: boolean = true;

  // Filters
  statusFilter: string = '';
  jobTypeFilter: string = '';

  // Polling
  private pollingSubscription: Subscription | null = null;
  pollingInterval: number = 3000; // 3 seconds

  constructor(
    private complianceService: ComplianceService,
    private toastService: ToastService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    // Check if a specific job ID was provided in route params
    this.route.params.subscribe(params => {
      if (params['id']) {
        this.loadJobDetails(params['id']);
      } else {
        this.loadJobs();
      }
    });

    // Start auto-refresh if enabled
    if (this.autoRefresh) {
      this.startPolling();
    }
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  /**
   * Load all jobs with filters
   */
  loadJobs(): void {
    this.loading = true;
    this.complianceService.getJobs(
      this.statusFilter || undefined,
      this.jobTypeFilter || undefined,
      100
    ).subscribe({
      next: (jobs: EvaluationJob[]) => {
        // Ensure jobs is always an array
        this.jobs = Array.isArray(jobs) ? jobs : [];

        // If we have a selected job, update it
        if (this.selectedJob && Array.isArray(this.jobs)) {
          const updatedJob = this.jobs.find(j => j.id === this.selectedJob!.id);
          if (updatedJob) {
            this.selectedJob = updatedJob;
          }
        }

        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading jobs:', error);
        this.toastService.error('Failed to load jobs');
        this.jobs = [];
        this.loading = false;
      }
    });
  }

  /**
   * Load specific job details
   */
  loadJobDetails(jobId: string): void {
    this.loading = true;
    this.complianceService.getJob(jobId).subscribe({
      next: (job: EvaluationJob | null) => {
        if (job) {
          this.selectedJob = job;
          this.loadJobs(); // Also load the jobs list
        } else {
          this.toastService.error('Job not found');
          this.router.navigate(['/compliance/jobs']);
        }
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading job:', error);
        this.toastService.error('Failed to load job details');
        this.loading = false;
      }
    });
  }

  /**
   * Start polling for job updates
   */
  startPolling(): void {
    this.stopPolling(); // Clear any existing subscription

    this.pollingSubscription = interval(this.pollingInterval)
      .pipe(
        switchMap(() => this.complianceService.getJobs(
          this.statusFilter || undefined,
          this.jobTypeFilter || undefined,
          100
        ))
      )
      .subscribe({
        next: (jobs: EvaluationJob[]) => {
          this.jobs = jobs;

          // Update selected job if it exists
          if (this.selectedJob) {
            const updatedJob = jobs.find(j => j.id === this.selectedJob!.id);
            if (updatedJob) {
              this.selectedJob = updatedJob;
            }
          }
        },
        error: (error: any) => {
          console.error('Polling error:', error);
        }
      });
  }

  /**
   * Stop polling
   */
  stopPolling(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
      this.pollingSubscription = null;
    }
  }

  /**
   * Toggle auto-refresh
   */
  toggleAutoRefresh(): void {
    this.autoRefresh = !this.autoRefresh;

    if (this.autoRefresh) {
      this.startPolling();
    } else {
      this.stopPolling();
    }
  }

  /**
   * Select a job to view details
   */
  selectJob(job: EvaluationJob): void {
    this.selectedJob = job;
    this.router.navigate(['/compliance/jobs', job.id]);
  }

  /**
   * Deselect job
   */
  deselectJob(): void {
    this.selectedJob = null;
    this.router.navigate(['/compliance/jobs']);
  }

  /**
   * Cancel a running job
   */
  cancelJob(job: EvaluationJob): void {
    if (!confirm(`Are you sure you want to cancel job "${job.id}"?`)) {
      return;
    }

    this.complianceService.cancelJob(job.id).subscribe({
      next: () => {
        this.toastService.success('Job cancelled successfully');
        this.loadJobs();
      },
      error: (error: any) => {
        console.error('Error cancelling job:', error);
        this.toastService.error('Failed to cancel job', error.message);
      }
    });
  }

  /**
   * Apply filters
   */
  onFilterChange(): void {
    this.loadJobs();
  }

  /**
   * Refresh jobs manually
   */
  refresh(): void {
    this.loadJobs();
  }

  /**
   * Navigate to view results
   */
  viewResults(job: EvaluationJob): void {
    // Navigate based on job type
    if (job.job_type === 'evaluate_contract' && job.contract_id) {
      this.router.navigate(['/compliance/results/contract', job.contract_id]);
    } else if (job.job_type === 'evaluate_rule' && job.rule_ids.length > 0) {
      this.router.navigate(['/compliance/results/rule', job.rule_ids[0]]);
    } else {
      this.toastService.info('Results viewing not available for this job type');
    }
  }

  /**
   * Navigate to dashboard
   */
  viewDashboard(): void {
    this.router.navigate(['/compliance/dashboard']);
  }

  /**
   * Navigate to evaluation trigger
   */
  newEvaluation(): void {
    this.router.navigate(['/compliance/evaluate']);
  }

  /**
   * Get status color class
   */
  getStatusColor(status: string): string {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'danger';
      case 'in_progress':
        return 'info';
      case 'pending':
        return 'warning';
      case 'cancelled':
        return 'secondary';
      default:
        return 'secondary';
    }
  }

  /**
   * Get status icon
   */
  getStatusIcon(status: string): string {
    switch (status) {
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'in_progress':
        return '⏳';
      case 'pending':
        return '⏸️';
      case 'cancelled':
        return '🚫';
      default:
        return '❓';
    }
  }

  /**
   * Check if job can be cancelled
   */
  canCancelJob(job: EvaluationJob): boolean {
    return job.status === 'pending' || job.status === 'in_progress';
  }

  /**
   * Check if job is complete
   */
  isJobComplete(job: EvaluationJob): boolean {
    return job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled';
  }

  /**
   * Format date for display in browser's local timezone
   */
  formatDate(dateString: string | null): string {
    if (!dateString) return 'N/A';

    try {
      // Normalize the timestamp to ensure it's treated as UTC
      let utcTimestamp = dateString.trim();

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
        console.error('Invalid timestamp:', dateString);
        return 'Invalid date';
      }

      // Format in browser's local timezone with explicit timezone display
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true,
        timeZoneName: 'short'
      });
    } catch (error) {
      console.error('Error formatting timestamp:', dateString, error);
      return 'Invalid date';
    }
  }

  /**
   * Calculate elapsed time
   */
  getElapsedTime(job: EvaluationJob): string {
    const start = new Date(job.started_date).getTime();
    const end = job.completed_date ? new Date(job.completed_date).getTime() : Date.now();
    const elapsed = Math.floor((end - start) / 1000); // seconds

    if (elapsed < 60) return `${elapsed}s`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`;
  }

  /**
   * Get running jobs count
   */
  getRunningJobsCount(): number {
    if (!Array.isArray(this.jobs)) return 0;
    return this.jobs.filter(j => j.status === 'in_progress' || j.status === 'pending').length;
  }

  /**
   * Get completed jobs count
   */
  getCompletedJobsCount(): number {
    if (!Array.isArray(this.jobs)) return 0;
    return this.jobs.filter(j => j.status === 'completed').length;
  }

  /**
   * Get failed jobs count
   */
  getFailedJobsCount(): number {
    if (!Array.isArray(this.jobs)) return 0;
    return this.jobs.filter(j => j.status === 'failed').length;
  }

  /**
   * Helper to expose Array.isArray to template
   */
  Array = Array;
}
