import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import {
  Contract,
  ContractFilter,
  ContractQuery,
  EntityOption,
  ContractComparisonRequest,
  ContractComparisonResponse,
  ContractComparison,
  ClauseAnalysis,
  CLAUSE_KEYS,
  GOLD_STANDARD
} from './models/contract.models';
import { ContractService } from './services/contract.service';
import { ToastService } from '../shared/services/toast.service';
import { AnalysisResultsService } from '../shared/services/analysis-results.service';
import { UserPreferencesService } from '../shared/services/user-preferences.service';
import { JobService } from '../shared/services/job.service';
import { JobNotificationService } from '../shared/services/job-notification.service';
import { SaveComparisonRequest, SaveQueryRequest, ContractQueried } from '../shared/models/analysis-results.models';
import { BatchJob, JobStatus, JobType, JobUpdateEvent, JobsUpdateEvent } from '../shared/models/job.models';

@Component({
  selector: 'app-contract-workbench',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './contract-workbench.html',
  styleUrls: ['./contract-workbench.scss']
})
export class ContractWorkbenchComponent implements OnInit {
  // Constants
  readonly CLAUSE_KEYS = CLAUSE_KEYS;
  readonly GOLD_STANDARD = GOLD_STANDARD;
  readonly TOKEN_BUDGET = 50000;  // 50K tokens for testing/demo
  readonly RESERVED_TOKENS = 8000;  // Reserve for question, answer, and overhead

  // Mode state
  workbenchMode: 'comparison' | 'question' = 'comparison'; // Primary mode selector
  pageTitle: string = 'Contract Intelligence Workbench'; // Dynamic page title
  pageIcon: string = '📋'; // Dynamic page icon

  // State
  contracts: Contract[] = [];
  filteredContracts: Contract[] = [];
  allContracts: Contract[] = []; // All contracts for Standard Contract dropdown
  selectedContracts: string[] = [];
  standardContractId: string = '';
  standardContract: Contract | null = null;
  availableGoverningLaws: EntityOption[] = [];
  availableContractingParties: EntityOption[] = [];
  availableContractTypes: EntityOption[] = [];
  availableClausesFromStandard: string[] = []; // Clauses from the selected standard contract
  
  filters: ContractFilter = {
    mode: 'realtime',
    comparisonMode: 'clauses',
    type: 'Any',
    dateFrom: '',
    dateTo: '',
    clauses: [],
    risk: 50,
    governingLaws: [],
    contractingParties: []
  };

  searchText = '';
  question = '';
  answer = '';
  safeAnswer: SafeHtml | null = null;
  isLoadingAnswer = false;

  // Streaming state
  streamingAnswer: string = '';
  isStreaming: boolean = false;
  streamingElapsed: number = 0;

  // Token-based contract selection for questions
  selectedContractsForQuestion: string[] = [];
  questionContractsLoaded = false;

  // Modal search/filter
  modalSearchText: string = '';
  filteredContractsForModal: Contract[] = [];

  // Chat interface state
  chatHistory: { text: string; timestamp: Date; isProcessing?: boolean }[] = [];
  currentChatInput = '';

  // Comparison state
  comparisonResults: ContractComparisonResponse | null = null;
  isLoadingComparison = false;
  showComparisonModal = false;
  expandedClauses: { [key: string]: boolean } = {}; // Track which clauses are expanded
  showClauseTextModal = false;
  selectedClauseForReview: ClauseAnalysis | null = null;
  selectedContractIdForReview: string = '';

  // Model selection state
  selectedModel: string = 'primary';

  // Save & PDF state
  savedResultId: string | null = null;
  isSavingResult = false;
  isGeneratingPDF = false;
  showComparisonExportMenu = false;
  showQueryExportMenu = false;

  // UI state
  activeTab: 'answers' | 'contracts' | 'clauses' | 'comparison' = 'comparison';
  showContractSelectionModal = false;
  isLoadingContracts = false;
  showContractDetailsModal = false;
  showRawDiffModal = false;
  selectedContractForDetails: Contract | null = null;
  dateRangeError = '';

  // Job monitoring state
  showJobMonitor = false;
  activeJobs: BatchJob[] = [];
  activeJobCount = 0;
  currentJobId: string | null = null;  // Currently tracked job
  jobProgress: { [jobId: string]: number } = {};  // Progress by job ID

  // Computed properties
  get canSelectMoreContracts(): boolean {
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;
    return this.selectedContracts.length < maxContracts;
  }

  get pickedContracts(): Contract[] {
    return this.contracts.filter(c => this.selectedContracts.includes(c.id));
  }

  // Token management computed properties
  get availableTokenBudget(): number {
    return this.TOKEN_BUDGET - this.RESERVED_TOKENS;
  }

  get usedTokens(): number {
    return this.selectedContractsForQuestion.reduce((total, contractId) => {
      const contract = this.allContracts.find(c => c.id === contractId);
      return total + (contract?.text_tokens || 0);
    }, 0);
  }

  get remainingTokens(): number {
    return this.availableTokenBudget - this.usedTokens;
  }

  get tokenUsagePercentage(): number {
    return (this.usedTokens / this.availableTokenBudget) * 100;
  }

  get canSelectMoreForQuestion(): boolean {
    return this.usedTokens < this.availableTokenBudget;
  }

  get selectedContractsForQuestionDetails(): Contract[] {
    return this.allContracts.filter(c =>
      this.selectedContractsForQuestion.includes(c.id)
    );
  }

  get isTokenLimitExceeded(): boolean {
    return this.usedTokens > this.availableTokenBudget;
  }

  // Get filtered contracts excluding the standard contract for selection list
  getFilteredContractsForSelection(): Contract[] {
    return this.filteredContractsForModal;
  }

  // Update filtered contracts based on current filters
  updateFilteredContracts(): void {
    // Use allContracts for question mode, filteredContracts for comparison mode
    let contracts = this.workbenchMode === 'question' ? this.allContracts : this.filteredContracts;

    // Filter out the standard contract from the selection list in comparison mode
    if (this.standardContractId && this.workbenchMode === 'comparison') {
      contracts = contracts.filter(c => c.id !== this.standardContractId);
    }

    // Apply search filter
    if (this.modalSearchText.trim()) {
      const search = this.modalSearchText.toLowerCase();
      contracts = contracts.filter(c =>
        (c.title || '').toLowerCase().includes(search) ||
        (c.contract_type || '').toLowerCase().includes(search) ||
        (c.governing_law_state || '').toLowerCase().includes(search) ||
        (c.contractorParty || '').toLowerCase().includes(search)
      );
    }

    this.filteredContractsForModal = contracts;
  }

  get jurisdictionStats(): { [key: string]: number } {
    const stats: { [key: string]: number } = {};
    this.contracts.forEach(contract => {
      stats[contract.governing_law_state] = (stats[contract.governing_law_state] || 0) + 1;
    });
    return stats;
  }

  constructor(
    private contractService: ContractService,
    private toastService: ToastService,
    private router: Router,
    private sanitizer: DomSanitizer,
    private analysisResultsService: AnalysisResultsService,
    private userPreferencesService: UserPreferencesService,
    private jobService: JobService,
    private jobNotificationService: JobNotificationService
  ) {
    // Configure marked for markdown parsing
    marked.setOptions({
      breaks: true,
      gfm: true,
      async: false
    });
  }

  ngOnInit(): void {
    this.loadGoverningLaws();
    this.loadContractingParties();
    this.loadContractTypes();
    this.loadAllContracts(); // Load all contracts for Standard Contract dropdown
    // Don't load filtered contracts on init - wait for user to click Select Contracts

    // Set initial tab based on mode
    this.updateTabForMode();

    // Load user preferences for model selection
    this.loadUserPreferences();

    // Subscribe to job notifications for real-time updates
    this.subscribeToJobNotifications();
  }

  /**
   * Subscribe to real-time job notifications via SSE
   */
  subscribeToJobNotifications(): void {
    // Subscribe to ALL user jobs (no status filter) so completed jobs appear in sidebar
    // This allows users to click on completed jobs to view results
    this.jobNotificationService.subscribeToUserJobs('system');

    // Listen for job updates
    this.jobNotificationService.getUserJobsUpdates().subscribe({
      next: (event: JobsUpdateEvent) => {
        this.activeJobs = event.jobs.map(j => ({
          id: j.job_id,
          job_id: j.job_id,
          job_type: j.job_type,
          user_id: 'system',
          status: j.status,
          priority: 5,
          request: {},
          progress: {
            current_step: 'queued' as any,
            percentage: j.progress.percentage,
            message: j.progress.message
          },
          created_date: j.created_date,
          completed_date: j.completed_date,
          elapsed_time: j.elapsed_time,
          result_id: j.result_id,
          ttl: 604800
        }));

        // Badge shows only active (queued + processing) jobs
        this.activeJobCount = event.counts.queued + event.counts.processing;

        // Update progress tracking
        event.jobs.forEach(job => {
          this.jobProgress[job.job_id] = job.progress.percentage;
        });

        // Check for completed jobs and show notifications
        event.jobs.forEach(job => {
          if (job.status === JobStatus.COMPLETED && job.result_id) {
            this.showJobCompletedNotification(job.job_id, job.result_id, job.job_type);
          } else if (job.status === JobStatus.FAILED) {
            this.showJobFailedNotification(job.job_id);
          }
        });
      },
      error: (error) => {
        console.error('Error receiving job updates:', error);
      }
    });

    // Listen for job counts (for badge)
    this.jobNotificationService.getJobCounts().subscribe({
      next: (counts) => {
        // Badge shows only active jobs
        this.activeJobCount = counts.queued + counts.processing;
      }
    });
  }

  /**
   * Show notification when job is completed
   */
  showJobCompletedNotification(jobId: string, resultId: string, jobType: JobType): void {
    // Only show notification once per job
    if (this.currentJobId === jobId) {
      // Show toast with action button - user must click to navigate
      this.toastService.show({
        type: 'success',
        title: 'Analysis Complete!',
        message: 'Your batch job has finished.',
        duration: 10000,  // Longer duration for action toasts (10 seconds)
        action: {
          label: 'View Results',
          callback: () => this.viewJobResult(resultId, jobType)
        }
      });

      // Clear current job
      this.currentJobId = null;
    }
  }

  /**
   * Show notification when job fails
   */
  showJobFailedNotification(jobId: string): void {
    if (this.currentJobId === jobId) {
      this.toastService.error(
        'Job Failed',
        'Your batch job has failed. Click to retry.'
      );

      // Clear current job
      this.currentJobId = null;
    }
  }

  /**
   * View job result by result_id, routing to appropriate page based on job type
   */
  viewJobResult(resultId: string, jobType?: JobType): void {
    // Find the job to determine its type if not provided
    if (!jobType) {
      const job = this.activeJobs.find(j => j.result_id === resultId);
      jobType = job?.job_type;
    }

    // Navigate to the appropriate page based on job type
    if (jobType === JobType.CONTRACT_QUERY) {
      this.router.navigate(['/query-contracts'], { queryParams: { resultId: resultId } });
    } else if (jobType === JobType.CONTRACT_COMPARISON) {
      this.router.navigate(['/compare-contracts'], { queryParams: { resultId: resultId } });
    } else {
      // Default to comparison page if type is unknown
      console.warn('Unknown job type, defaulting to comparison page');
      this.router.navigate(['/compare-contracts'], { queryParams: { resultId: resultId } });
    }
  }

  /**
   * Load saved result by ID and display in the workbench
   */
  loadSavedResult(resultId: string): void {
    console.log('Loading saved result:', resultId);
    this.isLoadingComparison = true;
    this.showComparisonModal = true;

    this.analysisResultsService.getResult(resultId, 'system').subscribe({
      next: (result) => {
        console.log('Loaded result:', result);

        // Check if it's a comparison result
        if (result.result_type !== 'comparison') {
          this.toastService.error('Invalid Result Type', 'This result is not a contract comparison.');
          this.isLoadingComparison = false;
          this.showComparisonModal = false;
          return;
        }

        // Check if comparison data exists
        if (!result.comparison_data || !result.comparison_data.results) {
          this.toastService.error('Invalid Result Data', 'Comparison data is missing or corrupted.');
          this.isLoadingComparison = false;
          this.showComparisonModal = false;
          return;
        }

        // Extract comparison data
        const comparisonData = result.comparison_data;

        // Set the comparison results
        this.comparisonResults = comparisonData.results;

        // Set the standard contract ID
        this.standardContractId = comparisonData.standard_contract_id;

        // Set the selected contracts
        this.selectedContracts = [
          comparisonData.standard_contract_id,
          ...comparisonData.compare_contract_ids
        ];

        // Update filters to match the saved comparison
        this.filters.comparisonMode = comparisonData.comparison_mode;
        if (comparisonData.selected_clauses) {
          this.filters.clauses = comparisonData.selected_clauses;
        }

        // Load the standard contract details from already loaded contracts
        if (this.standardContractId) {
          this.standardContract = this.allContracts.find(
            c => c.id === this.standardContractId
          ) || null;

          if (!this.standardContract) {
            console.warn('Standard contract not found in loaded contracts:', this.standardContractId);
          }
        }

        // Switch to comparison tab and hide modal
        this.activeTab = 'comparison';
        this.isLoadingComparison = false;
        this.showComparisonModal = false;

        // Set saved result ID for PDF/export functionality
        this.savedResultId = resultId;

        this.toastService.success('Result Loaded', 'Saved comparison results have been loaded successfully.');
      },
      error: (error) => {
        console.error('Error loading saved result:', error);
        this.isLoadingComparison = false;
        this.showComparisonModal = false;
        this.toastService.error('Load Failed', 'Failed to load saved result. Please try again.');
      }
    });
  }

  /**
   * Load saved query result by ID and display in the workbench
   */
  loadSavedQueryResult(resultId: string): void {
    console.log('Loading saved query result:', resultId);
    this.isLoadingAnswer = true;

    this.analysisResultsService.getResult(resultId, 'system').subscribe({
      next: (result) => {
        console.log('Loaded query result:', result);

        // Check if it's a query result
        if (result.result_type !== 'query') {
          this.toastService.error('Invalid Result Type', 'This result is not a contract query.');
          this.isLoadingAnswer = false;
          return;
        }

        // Check if query data exists
        if (!result.query_data) {
          this.toastService.error('Invalid Result Data', 'Query data is missing or corrupted.');
          this.isLoadingAnswer = false;
          return;
        }

        // Extract query data
        const queryData = result.query_data;

        // Set the question and answer
        this.question = queryData.query_text;
        // The answer is in answer_summary field, not answer field
        this.answer = queryData.results?.answer_summary || queryData.results?.answer || '';
        this.safeAnswer = this.convertMarkdownToHtml(this.answer);

        // Set the selected contracts for the question
        if (queryData.contracts_queried && queryData.contracts_queried.length > 0) {
          this.selectedContractsForQuestion = queryData.contracts_queried.map(
            (c: ContractQueried) => c.contract_id
          );
        }

        // Switch to answers tab
        this.activeTab = 'answers';
        this.isLoadingAnswer = false;

        // Set saved result ID for PDF/export functionality
        this.savedResultId = resultId;

        this.toastService.success('Result Loaded', 'Saved query results have been loaded successfully.');
      },
      error: (error) => {
        console.error('Error loading saved query result:', error);
        this.isLoadingAnswer = false;
        this.toastService.error('Load Failed', 'Failed to load saved result. Please try again.');
      }
    });
  }

  /**
   * Toggle job monitor sidebar
   */
  toggleJobMonitor(): void {
    this.showJobMonitor = !this.showJobMonitor;
  }

  /**
   * Cancel a job
   */
  cancelJob(jobId: string): void {
    if (confirm('Are you sure you want to cancel this job?')) {
      this.jobService.cancelJob(jobId, 'system').subscribe({
        next: (response) => {
          this.toastService.success('Job Cancelled', response.message);

          // Immediately update local job status for instant UI feedback
          const job = this.activeJobs.find(j => j.job_id === jobId);
          if (job) {
            job.status = JobStatus.CANCELLED;
            job.completed_date = new Date().toISOString();

            // Update active job count (exclude cancelled jobs)
            this.activeJobCount = this.activeJobs.filter(
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

  /**
   * Retry a failed job
   */
  retryJob(jobId: string): void {
    this.jobService.retryJob(jobId, 'system').subscribe({
      next: (response) => {
        this.toastService.success('Job Retried', `New job created: ${response.new_job_id}`);
        this.currentJobId = response.new_job_id;
      },
      error: (error) => {
        console.error('Error retrying job:', error);
        this.toastService.error('Retry Failed', 'Failed to retry job.');
      }
    });
  }

  /**
   * Delete a finished job (completed/failed/cancelled)
   */
  deleteJob(jobId: string): void {
    if (confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
      this.jobService.deleteJob(jobId, 'system').subscribe({
        next: (response) => {
          this.toastService.success('Job Deleted', response.message);
          // Remove job from local list
          this.activeJobs = this.activeJobs.filter(job => job.job_id !== jobId);
        },
        error: (error) => {
          console.error('Error deleting job:', error);
          this.toastService.error('Delete Failed', 'Failed to delete job.');
        }
      });
    }
  }

  /**
   * Get job status helpers
   */
  getJobStatusClass(status: JobStatus): string {
    return this.jobService.getStatusColor(status);
  }

  getJobStatusBadgeClass(status: JobStatus): string {
    // Map status to CSS class names
    switch (status) {
      case JobStatus.QUEUED:
        return 'job-status-queued';
      case JobStatus.PROCESSING:
        return 'job-status-processing';
      case JobStatus.COMPLETED:
        return 'job-status-completed';
      case JobStatus.FAILED:
        return 'job-status-failed';
      case JobStatus.CANCELLED:
        return 'job-status-cancelled';
      default:
        return 'badge-secondary';
    }
  }

  getJobStatusIcon(status: JobStatus): string {
    return this.jobService.getStatusIcon(status);
  }

  getJobTypeName(job: BatchJob): string {
    return this.jobService.getJobTypeName(job.job_type);
  }

  getJobTypeIcon(jobType: JobType): string {
    switch (jobType) {
      case JobType.CONTRACT_COMPARISON:
        return '📊';
      case JobType.CONTRACT_QUERY:
        return '❓';
      default:
        return '⚙️';
    }
  }

  getJobTypeLabel(jobType: JobType): string {
    switch (jobType) {
      case JobType.CONTRACT_COMPARISON:
        return 'Contract Comparison';
      case JobType.CONTRACT_QUERY:
        return 'Contract Query';
      default:
        return 'Unknown Job';
    }
  }

  formatJobTimestamp(timestamp?: string): string {
    if (!timestamp) {
      return 'N/A';
    }
    try {
      const date = new Date(timestamp);
      // Format in browser's local timezone with custom options
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch (e) {
      return timestamp;
    }
  }

  formatElapsedTime(seconds?: number): string {
    if (!seconds || seconds < 0) {
      return 'N/A';
    }

    // Format elapsed time in human-readable format
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
    }
  }

  showJobError(job: BatchJob): void {
    const errorMessage = job.progress.error || 'Unknown error occurred';
    alert(`Job Error\n\nJob ID: ${job.job_id}\nStatus: ${job.status}\n\nError:\n${errorMessage}`);
  }

  canCancelJob(status: JobStatus): boolean {
    return this.jobService.canCancelJob(status);
  }

  canRetryJob(job: BatchJob): boolean {
    return this.jobService.canRetryJob(job.status);
  }

  canViewResults(job: BatchJob): boolean {
    return this.jobService.canViewResults(job);
  }

  loadUserPreferences(): void {
    this.userPreferencesService.preferences$.subscribe({
      next: (prefs) => {
        if (prefs && prefs.model_preference) {
          this.selectedModel = prefs.model_preference.default_model;
        }
      },
      error: (error) => {
        console.error('Error loading user preferences:', error);
        // Use default model selection
        this.selectedModel = 'primary';
      }
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const clickedInsideDropdown = target.closest('.export-dropdown');

    if (!clickedInsideDropdown) {
      this.showComparisonExportMenu = false;
      this.showQueryExportMenu = false;
    }
  }

  setWorkbenchMode(mode: 'comparison' | 'question'): void {
    this.workbenchMode = mode;
    this.updateTabForMode();
  }

  updateTabForMode(): void {
    if (this.workbenchMode === 'comparison') {
      // For comparison mode, show comparison results tab
      this.activeTab = 'comparison';
    } else {
      // For question mode, show answers tab
      this.activeTab = 'answers';
    }
  }

  loadGoverningLaws(): void {
    // Call API to get all governing laws
    this.contractService.getGoverningLaws().subscribe({
      next: (laws) => {
        if (laws && laws.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableGoverningLaws = laws.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded governing laws from API:', this.availableGoverningLaws);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Governing Laws Found',
            'The API returned no governing laws. Please check your data.'
          );
          this.availableGoverningLaws = [];
        }
      },
      error: (error) => {
        console.error('Error loading governing laws from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Governing Laws',
          'Unable to retrieve governing laws from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableGoverningLaws = [];
      }
    });
  }

  loadContractingParties(): void {
    // Call API to get all contracting parties
    this.contractService.getContractingParties().subscribe({
      next: (parties) => {
        if (parties && parties.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableContractingParties = parties.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded contracting parties from API:', this.availableContractingParties);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Contracting Parties Found',
            'The API returned no contracting parties. Please check your data.'
          );
          this.availableContractingParties = [];
        }
      },
      error: (error) => {
        console.error('Error loading contracting parties from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Contracting Parties',
          'Unable to retrieve contracting parties from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableContractingParties = [];
      }
    });
  }

  loadContractTypes(): void {
    // Call API to get all contract types
    this.contractService.getContractTypes().subscribe({
      next: (types) => {
        if (types && types.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableContractTypes = types.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded contract types from API:', this.availableContractTypes);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Contract Types Found',
            'The API returned no contract types. Please check your data.'
          );
          this.availableContractTypes = [];
        }
      },
      error: (error) => {
        console.error('Error loading contract types from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Contract Types',
          'Unable to retrieve contract types from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableContractTypes = [];
      }
    });
  }

  loadAllContracts(): void {
    // Load all contracts without any filters for the Standard Contract dropdown
    this.contractService.getContracts().subscribe({
      next: (contracts) => {
        this.allContracts = contracts;
        this.updateFilteredContracts(); // Update modal filtered list
        console.log('Loaded all contracts for Standard Contract dropdown:', contracts.length);
        console.log('Sample contract IDs:', contracts.slice(0, 3).map(c => ({ id: c.id, title: c.title })));
        console.log('Sample contract text_tokens:', contracts.slice(0, 3).map(c => ({ id: c.id, text_tokens: c.text_tokens })));
      },
      error: (error) => {
        console.error('Error loading all contracts:', error);
        // Silent failure - Standard Contract dropdown is optional
        this.allContracts = [];
        this.updateFilteredContracts(); // Clear modal filtered list
      }
    });
  }

  // Date validation is still needed for UI feedback
  validateDateRange(): void {
    if (this.filters.dateFrom && this.filters.dateTo) {
      const fromDate = new Date(this.filters.dateFrom);
      const toDate = new Date(this.filters.dateTo);
      
      if (fromDate > toDate) {
        this.dateRangeError = 'From date must be before or equal to To date';
      } else {
        this.dateRangeError = '';
      }
    } else {
      this.dateRangeError = '';
    }
    
    // Clear selected contracts when date range changes
    if (this.filters.dateFrom || this.filters.dateTo) {
      this.selectedContracts = [];
    }
  }

  onStandardContractChange(): void {
    if (this.standardContractId) {
      console.log('Standard contract ID from select:', this.standardContractId);
      console.log('All contracts:', this.allContracts.map(c => ({ id: c.id, title: c.title })));
      
      // Look in allContracts instead of contracts (which might be filtered)
      this.standardContract = this.allContracts.find(c => c.id === this.standardContractId) || null;
      console.log('Standard contract selected:', this.standardContract);
      
      // Extract available clauses from the standard contract
      if (this.standardContract && this.standardContract.clauses) {
        this.availableClausesFromStandard = Object.keys(this.standardContract.clauses);
        console.log('Available clauses from standard contract:', this.availableClausesFromStandard);
        
        // Default to selecting all clauses
        this.filters.clauses = [...this.availableClausesFromStandard];
      } else {
        this.availableClausesFromStandard = [];
        this.filters.clauses = [];
      }
      
      // Remove standard contract from selected contracts if it was selected
      const index = this.selectedContracts.indexOf(this.standardContractId);
      if (index > -1) {
        this.selectedContracts.splice(index, 1);
      }
    } else {
      this.standardContract = null;
      this.availableClausesFromStandard = [];
      this.filters.clauses = [];
    }
  }

  onModeChange(mode: 'realtime' | 'batch'): void {
    this.filters.mode = mode;

    // Enforce limits for contracts only
    if (mode === 'realtime') {
      if (this.selectedContracts.length > 3) {
        this.selectedContracts = this.selectedContracts.slice(0, 3);
      }
    }
  }

  toggleContractSelection(contractId: string): void {
    const index = this.selectedContracts.indexOf(contractId);
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;

    if (index === -1) {
      if (this.selectedContracts.length < maxContracts) {
        this.selectedContracts.push(contractId);
      }
    } else {
      this.selectedContracts.splice(index, 1);
    }
  }

  isContractSelected(contractId: string): boolean {
    return this.selectedContracts.includes(contractId);
  }

  selectAllContracts(): void {
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;
    
    this.filteredContracts.forEach(contract => {
      if (!this.selectedContracts.includes(contract.id) && this.selectedContracts.length < maxContracts) {
        this.selectedContracts.push(contract.id);
      }
    });
  }

  deselectAllContracts(): void {
    const filteredIds = this.filteredContracts.map(c => c.id);
    this.selectedContracts = this.selectedContracts.filter(id => !filteredIds.includes(id));
  }

  toggleClause(clause: string): void {
    const index = this.filters.clauses.indexOf(clause);

    if (index === -1) {
      this.filters.clauses.push(clause);
    } else {
      this.filters.clauses.splice(index, 1);
    }
  }

  isClauseSelected(clause: string): boolean {
    return this.filters.clauses.includes(clause);
  }

  // Handler for contract type changes
  onContractTypeChange(): void {
    // Clear selected contracts when contract type changes
    this.selectedContracts = [];
  }

  // Handler for comparison mode changes
  onComparisonModeChange(mode: 'clauses' | 'full'): void {
    this.filters.comparisonMode = mode;
  }


  // Convert markdown string to SafeHtml for rendering
  private convertMarkdownToHtml(markdown: string): SafeHtml {
    try {
      let cleanedMarkdown = markdown.trim();

      // Check if content is JSON (for backward compatibility with old batch job results)
      if (cleanedMarkdown.startsWith('{') || cleanedMarkdown.startsWith('[')) {
        try {
          const jsonData = JSON.parse(cleanedMarkdown);
          // Convert JSON to readable markdown format
          cleanedMarkdown = this.convertJsonToMarkdown(jsonData);
        } catch (e) {
          // Not valid JSON, treat as markdown
          console.log('Content looks like JSON but failed to parse, treating as markdown');
        }
      }

      // Strip code fence markers if present (LLM sometimes wraps markdown in ```markdown ... ```)
      // Remove opening code fence
      if (cleanedMarkdown.startsWith('```markdown') || cleanedMarkdown.startsWith('```md')) {
        cleanedMarkdown = cleanedMarkdown.replace(/^```(markdown|md)\n?/, '');
      } else if (cleanedMarkdown.startsWith('```')) {
        cleanedMarkdown = cleanedMarkdown.replace(/^```\n?/, '');
      }

      // Remove closing code fence
      if (cleanedMarkdown.endsWith('```')) {
        cleanedMarkdown = cleanedMarkdown.replace(/\n?```$/, '');
      }

      const html = marked(cleanedMarkdown, { async: false }) as string;
      return this.sanitizer.bypassSecurityTrustHtml(html);
    } catch (error) {
      console.error('Error converting markdown:', error);
      return this.sanitizer.bypassSecurityTrustHtml(markdown);
    }
  }

  // Convert JSON structure to readable markdown (for legacy batch job results)
  private convertJsonToMarkdown(json: any): string {
    let markdown = '';

    if (json.analysis) {
      markdown += '# Contract Analysis\n\n';

      // Process each contract in the analysis
      Object.keys(json.analysis).forEach(contractKey => {
        const contract = json.analysis[contractKey];
        markdown += `## ${contractKey.replace(/_/g, ' ').toUpperCase()}\n\n`;

        if (contract.type) {
          markdown += `**Type:** ${contract.type}\n\n`;
        }
        if (contract.contract_sum) {
          markdown += `**Contract Sum:** ${contract.contract_sum}\n\n`;
        }
        if (contract.scope) {
          markdown += `**Scope:** ${contract.scope}\n\n`;
        }
        if (contract.financial_risk_summary) {
          markdown += `### Financial Risk Summary\n${contract.financial_risk_summary}\n\n`;
        }
        if (contract.risk_factors && Array.isArray(contract.risk_factors)) {
          markdown += `### Risk Factors\n`;
          contract.risk_factors.forEach((risk: string) => {
            markdown += `- ${risk}\n`;
          });
          markdown += '\n';
        }
      });
    }

    if (json.conclusion) {
      markdown += '# Conclusion\n\n';
      if (json.conclusion.most_financial_risk) {
        markdown += `**Contract with Most Financial Risk:** ${json.conclusion.most_financial_risk}\n\n`;
      }
      if (json.conclusion.justification) {
        markdown += `**Justification:** ${json.conclusion.justification}\n\n`;
      }
    }

    return markdown || '```json\n' + JSON.stringify(json, null, 2) + '\n```';
  }

  getAnswer(): void {
    // Check if batch mode is selected
    if (this.filters.mode === 'batch') {
      this.submitQueryBatchJob();
    } else {
      // Use streaming for real-time mode
      this.getAnswerStreaming();
    }
  }

  submitQueryBatchJob(): void {
    if (!this.question || this.question.trim() === '') {
      this.toastService.warning('Question Required', 'Please enter a question before submitting.');
      return;
    }

    // Use selectedContractsForQuestion in question mode, selectedContracts in comparison mode
    const contractIds = this.workbenchMode === 'question'
      ? this.selectedContractsForQuestion
      : this.selectedContracts;

    if (contractIds.length === 0) {
      this.toastService.warning('Contracts Required', 'Please select at least one contract for context.');
      return;
    }

    // Create batch job request
    const jobRequest = {
      request: {
        question: this.question,
        contract_ids: contractIds,
        modelSelection: this.selectedModel,
        userEmail: this.userPreferencesService.getCurrentUserEmail()
      },
      priority: 5
    };

    console.log('Submitting query batch job:', jobRequest);

    this.jobService.submitQueryJob(jobRequest, 'system').subscribe({
      next: (response) => {
        this.toastService.info(
          'Batch Processing Started',
          `Query job submitted successfully. You will be notified when complete. Job ID: ${response.job_id}`
        );
        this.currentJobId = response.job_id;

        // Clear the question input and loading states
        this.question = '';
        this.currentChatInput = '';
        this.isStreaming = false;
        this.isLoadingAnswer = false;

        // Update chat history to remove processing state
        if (this.chatHistory.length > 0) {
          const lastMessage = this.chatHistory[this.chatHistory.length - 1];
          if (lastMessage.isProcessing) {
            lastMessage.isProcessing = false;
          }
        }
      },
      error: (error) => {
        console.error('Error submitting query job:', error);
        this.toastService.error('Submission Failed', 'Failed to submit query job. Please try again.');

        // Clear loading states on error
        this.isStreaming = false;
        this.isLoadingAnswer = false;

        // Update chat history to remove processing state
        if (this.chatHistory.length > 0) {
          const lastMessage = this.chatHistory[this.chatHistory.length - 1];
          if (lastMessage.isProcessing) {
            lastMessage.isProcessing = false;
          }
        }
      }
    });
  }

  getAnswerStreaming(): void {
    this.isStreaming = true;
    this.streamingAnswer = '';
    this.answer = '';
    this.safeAnswer = null;
    this.streamingElapsed = 0;

    const contractIds = this.selectedContracts;

    this.contractService.queryContractsStreaming(this.question, contractIds).subscribe({
      next: (event) => {
        if (event.type === 'metadata') {
          console.log('Stream metadata:', event.data);
        } else if (event.type === 'content') {
          // Append new content as it arrives
          this.streamingAnswer += event.data.content;
          // Convert to HTML for display
          this.safeAnswer = this.convertMarkdownToHtml(this.streamingAnswer);
        } else if (event.type === 'complete') {
          console.log('Stream complete:', event.data);
          this.isStreaming = false;
          this.answer = this.streamingAnswer;
          this.streamingElapsed = event.data.elapsed || 0;
          this.activeTab = 'answers';

          // Update chat history to remove processing state
          if (this.chatHistory.length > 0) {
            this.chatHistory[this.chatHistory.length - 1].isProcessing = false;
          }
        } else if (event.type === 'error') {
          console.error('Stream error:', event.data);
          this.isStreaming = false;
          this.answer = `Error: ${event.data.error}`;
          this.safeAnswer = this.convertMarkdownToHtml(this.answer);

          // Update chat history to remove processing state
          if (this.chatHistory.length > 0) {
            this.chatHistory[this.chatHistory.length - 1].isProcessing = false;
          }
        }
      },
      error: (error) => {
        console.error('Error getting answer:', error);
        this.isStreaming = false;
        this.answer = 'Error processing query. Please try again.';
        this.safeAnswer = this.convertMarkdownToHtml('Error processing query. Please try again.');

        // Update chat history to remove processing state
        if (this.chatHistory.length > 0) {
          this.chatHistory[this.chatHistory.length - 1].isProcessing = false;
        }
      }
    });
  }

  sendChatMessage(): void {
    if (!this.currentChatInput.trim()) {
      return;
    }

    // Validate that contracts are selected
    if (this.selectedContractsForQuestion.length === 0) {
      this.toastService.warning(
        'No Contracts Selected',
        'Please select at least one contract for context before asking a question.'
      );
      return;
    }

    // Check if token limit is exceeded - automatically switch to batch mode
    if (this.isTokenLimitExceeded) {
      // Automatically switch to batch mode if not already in batch mode
      if (this.filters.mode !== 'batch') {
        this.filters.mode = 'batch';
        this.toastService.info(
          'Switched to Batch Mode',
          `Token limit exceeded (${this.formatTokens(this.usedTokens)} / ${this.formatTokens(this.availableTokenBudget)}). Automatically switched to batch processing.`
        );
      }
    }

    // Add question to chat history with processing state
    this.chatHistory.push({
      text: this.currentChatInput,
      timestamp: new Date(),
      isProcessing: true
    });

    // Set the question for the query
    this.question = this.currentChatInput;

    // Clear input
    this.currentChatInput = '';

    // Use selected contracts for the query
    this.selectedContracts = this.selectedContractsForQuestion;

    // Send the query
    this.getAnswer();
  }

  clearChatHistory(): void {
    this.chatHistory = [];
    this.currentChatInput = '';
    this.question = '';
    this.answer = '';
    this.safeAnswer = null;
  }

  onChatKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendChatMessage();
    }
  }

  askExampleQuestion(question: string): void {
    this.currentChatInput = question;
    this.sendChatMessage();
  }

  compareSelected(): void {
    // Open the contract selection modal and load filtered contracts
    this.modalSearchText = ''; // Clear search on open
    this.showContractSelectionModal = true;
    this.loadFilteredContracts();
    this.updateFilteredContracts(); // Initialize filtered list
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
  }
  
  closeContractSelectionModal(): void {
    this.showContractSelectionModal = false;
    // Re-enable body scroll
    document.body.style.overflow = '';
  }

  loadFilteredContracts(): void {
    this.isLoadingContracts = true;
    
    // Build filter parameters for API call
    // Only pass non-"Any" values and non-empty arrays
    // Use the stored normalized values (which are now in filters)
    const contractType = this.filters.type !== 'Any' ? this.filters.type : undefined;
    const governingLaws = this.filters.governingLaws && this.filters.governingLaws.length > 0 
      ? this.filters.governingLaws : undefined;
    const contractingParties = this.filters.contractingParties && this.filters.contractingParties.length > 0
      ? this.filters.contractingParties : undefined;
    const dateFrom = this.filters.dateFrom || undefined;
    const dateTo = this.filters.dateTo || undefined;

    // Call the service with arrays for multi-select fields
    this.contractService.getContracts(
      contractType,
      undefined, // contractor_party - not in our filters yet
      contractingParties, // Pass full array - service will convert to comma-separated
      governingLaws,      // Pass full array - service will convert to comma-separated
      dateFrom,
      dateTo
    ).subscribe({
      next: (contracts) => {
        this.contracts = contracts;
        this.filteredContracts = contracts; // All returned contracts are already filtered
        this.isLoadingContracts = false;
        this.updateFilteredContracts(); // Update modal filtered list
        console.log('Loaded filtered contracts:', contracts.length);
      },
      error: (error) => {
        console.error('Error loading contracts:', error);
        this.toastService.error('Failed to Load Contracts', 'Unable to retrieve contracts from the server.');
        this.contracts = [];
        this.filteredContracts = [];
        this.isLoadingContracts = false;
        this.updateFilteredContracts(); // Clear modal filtered list
      }
    });
  }

  copyResults(): void {
    const results = {
      query: this.question,
      filters: this.filters,
      selectedContracts: this.pickedContracts,
      timestamp: new Date().toISOString()
    };

    navigator.clipboard.writeText(JSON.stringify(results, null, 2))
      .then(() => {
        alert('Results copied to clipboard!');
      })
      .catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy results to clipboard');
      });
  }

  showContractDetails(contract: Contract): void {
    this.selectedContractForDetails = contract;
    this.showContractDetailsModal = true;
  }

  showRawDiff(): void {
    if (this.pickedContracts.length >= 2) {
      this.showRawDiffModal = true;
    }
  }

  highlightText(text: string): string {
    if (!this.searchText || !text) return text;
    const regex = new RegExp(`(${this.searchText})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  normalizeText(text: string): string {
    return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  isDifferentFromGoldStandard(provision: string, value: string): boolean {
    // First check if we have a standard contract selected
    if (this.standardContract && this.standardContract.clauses[provision]) {
      const standardValue = this.standardContract.clauses[provision];
      return this.normalizeText(value) !== this.normalizeText(standardValue);
    }
    
    // Fall back to predefined gold standard
    const goldStandard = this.GOLD_STANDARD[provision];
    if (!goldStandard) return false;
    return this.normalizeText(value) !== this.normalizeText(goldStandard);
  }

  hasGoldStandard(provision: string): boolean {
    // Check if standard contract has this provision
    if (this.standardContract && this.standardContract.clauses[provision]) {
      return true;
    }
    
    // Fall back to predefined gold standard
    return !!this.GOLD_STANDARD[provision];
  }

  getStandardValue(provision: string): string {
    // Return the standard value for comparison
    if (this.standardContract && this.standardContract.clauses[provision]) {
      return this.standardContract.clauses[provision];
    }
    return this.GOLD_STANDARD[provision] || '';
  }

  diffStrings(a: string, b: string): string[] {
    const aWords = a.split(/\s+/);
    const bWords = new Set(b.split(/\s+/));
    
    return aWords.map(word => {
      if (bWords.has(word)) {
        return word;
      } else {
        return `<span class="diff-highlight">${word}</span>`;
      }
    });
  }

  getClauseIcon(clauseName: string): string {
    const icons: { [key: string]: string } = {
      'Indemnity': '🛡️',
      'Payment Terms': '💰',
      'Governing Law': '⚖️',
      'Insurance': '☂️',
      'Limitation of Liability': '⚠️'
    };
    return icons[clauseName] || '📄';
  }

  runSavedQuery(queryName: string): void {
    let queryText = '';
    if (queryName === 'non-delaware') {
      queryText = 'Which contracts are governed by states other than Delaware?';
    } else if (queryName === 'indemnity-by-type') {
      queryText = 'Show indemnity clause variations grouped by contract type';
    }
    
    if (queryText) {
      // Add to chat history
      this.chatHistory.push({
        text: queryText,
        timestamp: new Date(),
        isProcessing: true
      });
      
      this.question = queryText;
      this.getAnswer();
    }
  }

  toggleGoverningLaw(law: string): void {
    if (law === 'Any') {
      // Clear all selections
      this.filters.governingLaws = [];
    } else {
      if (!this.filters.governingLaws) {
        this.filters.governingLaws = [];
      }
      
      const index = this.filters.governingLaws.indexOf(law);
      if (index === -1) {
        this.filters.governingLaws.push(law);
      } else {
        this.filters.governingLaws.splice(index, 1);
      }
    }
    
    // Clear selected contracts when filter changes
    this.selectedContracts = [];
  }

  isGoverningLawSelected(law: string): boolean {
    return this.filters.governingLaws ? this.filters.governingLaws.includes(law) : false;
  }

  toggleContractingParty(party: string): void {
    if (party === 'Any') {
      // Clear all selections
      this.filters.contractingParties = [];
    } else {
      if (!this.filters.contractingParties) {
        this.filters.contractingParties = [];
      }
      
      const index = this.filters.contractingParties.indexOf(party);
      if (index === -1) {
        this.filters.contractingParties.push(party);
      } else {
        this.filters.contractingParties.splice(index, 1);
      }
    }
    
    // Clear selected contracts when filter changes
    this.selectedContracts = [];
  }

  isContractingPartySelected(party: string): boolean {
    return this.filters.contractingParties ? this.filters.contractingParties.includes(party) : false;
  }
  
  getContractingPartyDisplayName(normalizedName: string): string {
    const party = this.availableContractingParties.find(p => p.normalizedName === normalizedName);
    return party ? party.displayName : normalizedName;
  }
  
  getGoverningLawDisplayName(normalizedName: string): string {
    const law = this.availableGoverningLaws.find(l => l.normalizedName === normalizedName);
    return law ? law.displayName : normalizedName;
  }
  
  // Helper methods for Clauses dropdown
  areAllClausesSelected(): boolean {
    return this.availableClausesFromStandard.length > 0 && 
           this.filters.clauses.length === this.availableClausesFromStandard.length;
  }
  
  toggleAllClauses(): void {
    if (this.areAllClausesSelected()) {
      // Deselect all
      this.filters.clauses = [];
    } else {
      // Select all
      this.filters.clauses = [...this.availableClausesFromStandard];
    }
  }
  
  getClausesButtonText(): string {
    if (this.filters.clauses.length === 0) {
      return 'Select clauses to compare';
    } else if (this.areAllClausesSelected()) {
      return 'All clauses selected';
    } else {
      return `${this.filters.clauses.length} of ${this.availableClausesFromStandard.length} clauses selected`;
    }
  }

  // Comparison methods
  runComparison(): void {
    // Validate that we have required data
    if (!this.standardContractId) {
      this.toastService.warning('No Standard Contract', 'Please select a standard contract for comparison.');
      return;
    }

    if (this.selectedContracts.length === 0) {
      this.toastService.warning('No Contracts Selected', 'Please select contracts to compare against the standard.');
      return;
    }

    console.log('Running comparison with standardContractId:', this.standardContractId);
    console.log('Selected contracts:', this.selectedContracts);

    // Ensure the standard contract ID has the correct format
    // The backend expects IDs with "contract_" prefix
    let normalizedStandardId = this.standardContractId;
    if (!normalizedStandardId.startsWith('contract_')) {
      console.warn(`Standard contract ID missing prefix: ${normalizedStandardId}, adding "contract_" prefix`);
      normalizedStandardId = `contract_${normalizedStandardId}`;
    }

    // Filter out the standard contract from the comparison list
    const compareContractIds = this.selectedContracts.filter(id => 
      id !== this.standardContractId && id !== normalizedStandardId
    );
    
    if (compareContractIds.length === 0) {
      this.toastService.warning('Insufficient Contracts', 'Please select contracts other than the standard contract to compare.');
      return;
    }

    // Ensure all comparison contract IDs have the correct format
    const normalizedCompareIds = compareContractIds.map(id => {
      if (!id.startsWith('contract_')) {
        console.warn(`Compare contract ID missing prefix: ${id}, adding "contract_" prefix`);
        return `contract_${id}`;
      }
      return id;
    });

    // Determine selected clauses
    const selectedClauses = this.filters.comparisonMode === 'full' 
      ? 'all' 
      : (this.areAllClausesSelected() ? 'all' : this.filters.clauses);

    // Create the comparison request
    const request: ContractComparisonRequest = {
      standardContractId: normalizedStandardId,
      compareContractIds: normalizedCompareIds,
      comparisonMode: this.filters.comparisonMode || 'clauses',  // Default to 'clauses' if undefined
      selectedClauses: selectedClauses as string[] | 'all',  // Type assertion since we know it's valid
      modelSelection: this.selectedModel,  // Add model selection
      userEmail: this.userPreferencesService.getCurrentUserEmail(),  // Add user email
      forceBatch: this.filters.mode === 'batch'  // Force batch mode if user selected batch
    };

    console.log('Comparison request:', request);

    // Start the comparison
    this.isLoadingComparison = true;
    this.showComparisonModal = true;
    
    this.contractService.compareContracts(request).subscribe({
      next: (response) => {
        this.isLoadingComparison = false;

        // Check if response is batch mode
        if (response.batch_mode && response.job_id) {
          // BATCH MODE: Job submitted, show notification and track progress
          this.currentJobId = response.job_id;
          this.showComparisonModal = false;  // Close modal, will track via job monitor

          this.toastService.info(
            'Batch Processing Started',
            `Comparison job submitted successfully. You will be notified when complete. Job ID: ${response.job_id}`
          );

          // Job will be tracked automatically via SSE subscription in ngOnInit
          // No need to subscribe here as we're already listening to user jobs stream

        } else {
          // REAL-TIME MODE: Show results immediately
          this.comparisonResults = response;

          if (response.success && response.results) {
            this.activeTab = 'comparison';
            this.toastService.success('Comparison Complete', 'Contract comparison has been completed successfully.');
          } else {
            this.toastService.error('Comparison Failed', response.error || 'An error occurred during comparison.');
          }
        }
      },
      error: (error) => {
        console.error('Error comparing contracts:', error);
        this.isLoadingComparison = false;
        this.showComparisonModal = false;
        this.toastService.error('Comparison Error', 'Failed to complete contract comparison. Please try again.');
      }
    });
  }

  generateComparison(): void {
    // This is triggered by the "Generate" button in the sidebar
    if (this.filters.mode === 'realtime') {
      // For real-time mode, run the comparison immediately
      this.runComparison();
    } else {
      // For batch mode, show a confirmation dialog first
      if (confirm('This will start a batch comparison process. You will be notified when complete. Continue?')) {
        this.runComparison();
      }
    }
  }

  getRiskBadgeClass(riskLevel: string): string {
    switch (riskLevel) {
      case 'high': return 'badge-danger';
      case 'medium': return 'badge-warning';
      case 'low': return 'badge-success';
      default: return 'badge-secondary';
    }
  }

  getSimilarityBadgeClass(score: number): string {
    if (score >= 90) return 'badge-success';
    if (score >= 70) return 'badge-info';
    if (score >= 50) return 'badge-warning';
    return 'badge-danger';
  }

  getContractTitle(contractId: string): string {
    const contract = this.allContracts.find(c => c.id === contractId);
    return contract ? contract.title : contractId;
  }

  exportComparisonResults(): void {
    if (!this.comparisonResults) return;

    const exportData = {
      timestamp: new Date().toISOString(),
      standardContract: this.standardContractId,
      comparedContracts: this.comparisonResults.compareContractIds,
      mode: this.comparisonResults.comparisonMode,
      results: this.comparisonResults.results
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `contract-comparison-${new Date().getTime()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  }

  // Sort clause analyses by similarity score (ascending - least similar first)
  getSortedClauseAnalyses(analyses: ClauseAnalysis[]): ClauseAnalysis[] {
    if (!analyses) return [];
    return [...analyses].sort((a, b) => a.similarity_score - b.similarity_score);
  }

  // Toggle clause expansion
  toggleClauseExpansion(contractId: string, clauseType: string): void {
    const key = `${contractId}_${clauseType}`;
    this.expandedClauses[key] = !this.expandedClauses[key];
  }

  // Check if clause is expanded
  isClauseExpanded(contractId: string, clauseType: string): boolean {
    const key = `${contractId}_${clauseType}`;
    return this.expandedClauses[key] || false;
  }

  // Get a unique key for the clause
  getClauseKey(contractId: string, clauseType: string): string {
    return `${contractId}_${clauseType}`;
  }

  // Show clause text comparison modal
  showClauseText(clauseAnalysis: ClauseAnalysis, contractId: string): void {
    this.selectedClauseForReview = clauseAnalysis;
    this.selectedContractIdForReview = contractId;
    this.showClauseTextModal = true;
  }

  // Close clause text modal
  closeClauseTextModal(): void {
    this.showClauseTextModal = false;
    this.selectedClauseForReview = null;
    this.selectedContractIdForReview = '';
  }

  /**
   * Token management methods for question mode
   */
  toggleContractForQuestion(contractId: string): void {
    const contract = this.allContracts.find(c => c.id === contractId);
    if (!contract) return;

    const index = this.selectedContractsForQuestion.indexOf(contractId);
    const tokens = contract.text_tokens || 0;

    if (index === -1) {
      // Adding contract - allow selection and show warning if exceeding budget
      this.selectedContractsForQuestion = [...this.selectedContractsForQuestion, contractId];

      // Show warning if this selection exceeds the token budget
      if (this.usedTokens > this.availableTokenBudget) {
        this.toastService.warning(
          'Token Budget Exceeded',
          `Your query will be processed in the background and you will be notified when complete. ` +
          `Token usage: ${this.formatTokens(this.usedTokens)} / ${this.formatTokens(this.availableTokenBudget)}`
        );
      }
    } else {
      // Removing contract - use immutable operation
      this.selectedContractsForQuestion = this.selectedContractsForQuestion.filter(id => id !== contractId);
    }
  }

  isContractSelectedForQuestion(contractId: string): boolean {
    return this.selectedContractsForQuestion.includes(contractId);
  }

  clearQuestionContracts(): void {
    this.selectedContractsForQuestion = []; // Already immutable assignment
  }

  formatTokens(tokens: number): string {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  }

  openQuestionContractSelector(): void {
    this.modalSearchText = ''; // Clear search on open
    this.showContractSelectionModal = true;
    if (!this.questionContractsLoaded) {
      this.loadAllContracts();
      this.questionContractsLoaded = true;
    }
    this.updateFilteredContracts(); // Initialize filtered list
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
  }

  clearModalSearch(): void {
    this.modalSearchText = '';
    this.updateFilteredContracts();
  }

  getTokenBadgeClass(): string {
    const percentage = this.tokenUsagePercentage;
    if (percentage >= 90) return 'badge-danger';
    if (percentage >= 75) return 'badge-warning';
    if (percentage >= 50) return 'badge-info';
    return 'badge-success';
  }

  getContractTokenBadgeClass(tokens: number): string {
    // Classify contract size by tokens
    if (tokens > 30000) return 'token-badge-xlarge';
    if (tokens > 20000) return 'token-badge-large';
    if (tokens > 10000) return 'token-badge-medium';
    return 'token-badge-small';
  }

  /**
   * Navigate to compliance evaluation page for the given contract
   */
  evaluateContract(contractId: string): void {
    // Find the contract to get its title/name for display
    const contract = this.allContracts.find(c => c.id === contractId);
    const contractName = contract ? contract.title : contractId;

    this.router.navigate(['/compliance/evaluate'], {
      queryParams: {
        contract_id: contractId,
        contract_name: contractName
      }
    });
  }

  // =========================================================================
  // Save & PDF Generation Methods (Phase 4)
  // =========================================================================

  /**
   * Save comparison results and generate PDF
   */
  saveAndGenerateComparisonPDF(): void {
    if (!this.comparisonResults) {
      this.toastService.error('No Results', 'No comparison results to save.');
      return;
    }

    this.isSavingResult = true;

    // Build the save request
    const request: SaveComparisonRequest = {
      user_id: 'system', // TODO: Replace with actual user from auth
      standard_contract_id: this.standardContractId,
      compare_contract_ids: this.comparisonResults.compareContractIds || [],
      comparison_mode: this.comparisonResults.comparisonMode as 'full' | 'clauses',
      selected_clauses: this.filters.clauses.length > 0 ? this.filters.clauses : undefined,
      results: this.comparisonResults,
      metadata: {
        title: `Comparison: ${this.getContractTitle(this.standardContractId)} vs ${(this.comparisonResults.compareContractIds || []).length} contract(s)`,
        description: `${this.comparisonResults.comparisonMode} comparison`
      }
    };

    // Save the results
    this.analysisResultsService.saveComparisonResult(request).subscribe({
      next: (response) => {
        this.savedResultId = response.result_id;
        this.isSavingResult = false;
        this.toastService.success('Saved', 'Comparison results saved successfully.');

        // Automatically generate PDF
        this.generatePDFFromSavedResult();
      },
      error: (error) => {
        console.error('Error saving comparison:', error);
        this.isSavingResult = false;
        this.toastService.error('Save Failed', error.message || 'Failed to save comparison results.');
      }
    });
  }

  /**
   * Save query results and generate PDF
   */
  saveAndGenerateQueryPDF(): void {
    if (!this.answer || this.selectedContractsForQuestion.length === 0) {
      this.toastService.error('No Results', 'No query results to save.');
      return;
    }

    this.isSavingResult = true;

    // Build contracts queried list with filenames
    const contractsQueried: ContractQueried[] = this.selectedContractsForQuestion.map(contractId => {
      const contract = this.allContracts.find(c => c.id === contractId);
      return {
        contract_id: contractId,
        filename: `${contractId}.json`,
        contract_title: contract?.title || contractId
      };
    });

    // Build the save request
    const request: SaveQueryRequest = {
      user_id: 'system', // TODO: Replace with actual user from auth
      query_text: this.question,
      query_type: 'natural_language',
      contracts_queried: contractsQueried,
      results: {
        answer_summary: this.answer,
        ranked_contracts: [], // TODO: If you have ranking data, include it here
        execution_metadata: {
          contracts_analyzed: this.selectedContractsForQuestion.length,
          query_time_seconds: 0, // TODO: Track actual query time if available
          llm_model: 'gpt-4'
        }
      },
      metadata: {
        title: `Query: ${this.question.substring(0, 50)}${this.question.length > 50 ? '...' : ''}`,
        description: `Analyzed ${this.selectedContractsForQuestion.length} contracts`
      }
    };

    // Save the results
    this.analysisResultsService.saveQueryResult(request).subscribe({
      next: (response) => {
        this.savedResultId = response.result_id;
        this.isSavingResult = false;
        this.toastService.success('Saved', 'Query results saved successfully.');

        // Automatically generate PDF
        this.generatePDFFromSavedResult();
      },
      error: (error) => {
        console.error('Error saving query:', error);
        this.isSavingResult = false;
        this.toastService.error('Save Failed', error.message || 'Failed to save query results.');
      }
    });
  }

  /**
   * Generate PDF from saved result
   */
  generatePDFFromSavedResult(): void {
    if (!this.savedResultId) {
      this.toastService.error('No Saved Result', 'Please save results first.');
      return;
    }

    this.isGeneratingPDF = true;
    const userId = 'system'; // TODO: Replace with actual user from auth

    this.analysisResultsService.generatePDF(this.savedResultId, userId).subscribe({
      next: (blob) => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `report_${this.savedResultId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        this.isGeneratingPDF = false;
        this.toastService.success('PDF Generated', 'Your PDF report has been downloaded.');
      },
      error: (error) => {
        console.error('Error generating PDF:', error);
        this.isGeneratingPDF = false;
        this.toastService.error('PDF Generation Failed', 'Failed to generate PDF. Please try again.');
      }
    });
  }

  /**
   * Email PDF (placeholder - Phase 3 deferred)
   */
  emailPDF(): void {
    this.toastService.info('Coming Soon', 'Email functionality will be available in a future release.');
  }

  /**
   * View contract PDF in new browser tab
   * 
   * @param contractId - ID of the contract to view
   */
  viewContractPdf(contractId: string): void {
    this.contractService.openContractPdf(contractId);
  }

  /**
   * Download contract PDF to local machine
   *
   * @param contractId - ID of the contract
   * @param contractTitle - Optional title for the file
   */
  downloadContractPdf(contractId: string, contractTitle?: string): void {
    this.contractService.downloadContractPdf(contractId, contractTitle);
  }

}