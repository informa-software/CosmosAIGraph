import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ComplianceService } from '../../compliance/services/compliance.service';
import { ContractEvaluationResults } from '../../compliance/models/compliance.models';
import { ContractService } from '../../contract-workbench/services/contract.service';
import { ContractUploadService, UploadJobStatus } from '../../contract-workbench/services/contract-upload.service';
import { ToastService } from '../../shared/services/toast.service';
import { JobNotificationService } from '../../shared/services/job-notification.service';
import { JobsUpdateEvent, JobType } from '../../shared/models/job.models';

interface Contract {
  id: string;
  filename: string;
  contractor_party: string;
  contracting_party: string;
  governing_law_state: string;
  contract_type: string;
  effective_date: string;
  expiration_date: string;
  contract_value: string;
}

interface ContractFilters {
  contractor_party: string[];
  contracting_party: string[];
  governing_law_state: string[];
  contract_type: string[];
  dateFrom: string;
  dateTo: string;
}

@Component({
  selector: 'app-contracts-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './contracts-list.component.html',
  styleUrls: ['./contracts-list.component.scss']
})
export class ContractsListComponent implements OnInit {
  contracts: Contract[] = [];
  filteredContracts: Contract[] = [];

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalContracts = 0;
  totalPages = 0;

  // Sorting
  sortColumn: string = 'filename';
  sortDirection: 'asc' | 'desc' = 'asc';

  // Filters
  filters: ContractFilters = {
    contractor_party: [],
    contracting_party: [],
    governing_law_state: [],
    contract_type: [],
    dateFrom: '',
    dateTo: ''
  };

  // Filter options (will be populated from API)
  contractorParties: string[] = [];
  contractingParties: string[] = [];
  governingLawStates: string[] = [];
  contractTypes: string[] = [];

  loading = false;
  error: string | null = null;

  // Dropdown state
  openDropdown: string | null = null;

  // Contract Details Dialog
  showDetailsDialog = false;
  selectedContract: Contract | null = null;
  contractPdfUrl: SafeResourceUrl | null = null;
  complianceResults: ContractEvaluationResults | null = null;
  loadingCompliance = false;

  // Upload state
  showUploadModal = false;
  selectedFile: File | null = null;
  isDraggingFile = false;

  // Track notified jobs to prevent duplicate notifications
  private notifiedJobIds = new Set<string>();

  constructor(
    private complianceService: ComplianceService,
    private sanitizer: DomSanitizer,
    private contractService: ContractService,
    private uploadService: ContractUploadService,
    private toastService: ToastService,
    private jobNotificationService: JobNotificationService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    this.loadContracts();
    this.loadFilterOptions();
    this.subscribeToJobNotifications();

    // Check if we need to open a specific contract details from query params
    this.route.queryParams.subscribe(params => {
      const contractId = params['contractId'];
      if (contractId) {
        // Find and open the contract details
        // Need to wait for contracts to load first
        this.openContractById(contractId);
      }
    });
  }

  /**
   * Subscribe to job notifications for upload completion
   */
  subscribeToJobNotifications(): void {
    this.jobNotificationService.subscribeToUserJobs('system').subscribe({
      next: (event: JobsUpdateEvent) => {
        // On first event, initialize the tracking set with all existing completed/failed jobs
        // This prevents showing toasts for old jobs when navigating to the page
        if (this.notifiedJobIds.size === 0) {
          event.jobs
            .filter(job => job.job_type === JobType.CONTRACT_UPLOAD &&
                          (job.status === 'completed' || job.status === 'failed'))
            .forEach(job => this.notifiedJobIds.add(job.job_id));
          return; // Don't show notifications on initial load
        }

        // Check for CONTRACT_UPLOAD jobs that just completed
        const newlyCompletedUploads = event.jobs.filter(
          job => job.job_type === JobType.CONTRACT_UPLOAD &&
                 job.status === 'completed' &&
                 !this.notifiedJobIds.has(job.job_id)
        );

        if (newlyCompletedUploads.length > 0) {
          // Mark as notified
          newlyCompletedUploads.forEach(job => this.notifiedJobIds.add(job.job_id));

          // Show success toast
          this.toastService.success(
            'Upload Complete',
            `Contract${newlyCompletedUploads.length > 1 ? 's' : ''} uploaded successfully`
          );

          // Refresh contract list to show new contracts
          this.loadContracts();
        }

        // Check for failed uploads
        const newlyFailedUploads = event.jobs.filter(
          job => job.job_type === JobType.CONTRACT_UPLOAD &&
                 job.status === 'failed' &&
                 !this.notifiedJobIds.has(job.job_id)
        );

        if (newlyFailedUploads.length > 0) {
          // Mark as notified
          newlyFailedUploads.forEach(job => this.notifiedJobIds.add(job.job_id));

          this.toastService.error(
            'Upload Failed',
            newlyFailedUploads[0].error_message || 'Contract upload failed'
          );
        }
      },
      error: (error) => {
        console.error('Job notification error:', error);
      }
    });
  }

  async loadContracts() {
    this.loading = true;
    this.error = null;

    try {
      // Build request body with filter parameters (bypasses LLM)
      const requestBody: any = {
        query: this.buildQuery(),  // Still send query for logging/display
        limit: this.pageSize,
        strategy_override: 'db',
        offset: (this.currentPage - 1) * this.pageSize
      };

      // Add filter parameters - when present, these trigger programmatic mode
      if (this.filters.contractor_party.length > 0) {
        requestBody.contractor_party = this.filters.contractor_party;
      }
      if (this.filters.contracting_party.length > 0) {
        requestBody.contracting_party = this.filters.contracting_party;
      }
      if (this.filters.governing_law_state.length > 0) {
        requestBody.governing_law_state = this.filters.governing_law_state;
      }
      if (this.filters.contract_type.length > 0) {
        requestBody.contract_type = this.filters.contract_type;
      }

      const response = await fetch(`https://localhost:8000/query_contracts_direct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error('Failed to load contracts');
      }

      const data = await response.json();
      this.contracts = data.documents || [];
      this.filteredContracts = [...this.contracts];
      this.totalContracts = data.document_count || 0;
      this.totalPages = Math.ceil(this.totalContracts / this.pageSize);

      this.applySort();
    } catch (err: any) {
      this.error = err.message || 'Failed to load contracts';
      console.error('Error loading contracts:', err);
    } finally {
      this.loading = false;
    }
  }

  buildQuery(): string {
    const conditions: string[] = [];

    if (this.filters.contractor_party.length > 0) {
      const values = this.filters.contractor_party.map(v => `'${v}'`).join(', ');
      conditions.push(`contractor_party in (${values})`);
    }
    if (this.filters.contracting_party.length > 0) {
      const values = this.filters.contracting_party.map(v => `'${v}'`).join(', ');
      conditions.push(`contracting_party in (${values})`);
    }
    if (this.filters.governing_law_state.length > 0) {
      const values = this.filters.governing_law_state.map(v => `'${v}'`).join(', ');
      conditions.push(`governing_law_state in (${values})`);
    }
    if (this.filters.contract_type.length > 0) {
      const values = this.filters.contract_type.map(v => `'${v}'`).join(', ');
      conditions.push(`contract_type in (${values})`);
    }

    if (conditions.length > 0) {
      return `Show all contracts where ${conditions.join(' and ')}`;
    }

    return 'Show all contracts';
  }

  async loadFilterOptions() {
    // Load unique values for filter dropdowns
    // This would ideally come from entity collections
    try {
      const response = await fetch(`https://localhost:8000/query_contracts_direct`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'Show all contracts',
          limit: 1000,
          strategy_override: 'db'
        })
      });

      if (response.ok) {
        const data = await response.json();
        const contracts = data.documents || [];

        // Extract unique values
        this.contractorParties = ([...new Set(contracts.map((c: Contract) => c.contractor_party).filter((v: string | undefined): v is string => Boolean(v)))] as string[]).sort();
        this.contractingParties = ([...new Set(contracts.map((c: Contract) => c.contracting_party).filter((v: string | undefined): v is string => Boolean(v)))] as string[]).sort();
        this.governingLawStates = ([...new Set(contracts.map((c: Contract) => c.governing_law_state).filter((v: string | undefined): v is string => Boolean(v)))] as string[]).sort();
        this.contractTypes = ([...new Set(contracts.map((c: Contract) => c.contract_type).filter((v: string | undefined): v is string => Boolean(v)))] as string[]).sort();
      }
    } catch (err) {
      console.error('Failed to load filter options:', err);
    }
  }

  onFilterChange() {
    this.currentPage = 1;
    this.loadContracts();
  }

  clearFilters() {
    this.filters = {
      contractor_party: [],
      contracting_party: [],
      governing_law_state: [],
      contract_type: [],
      dateFrom: '',
      dateTo: ''
    };
    this.onFilterChange();
  }

  sort(column: string) {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.applySort();
  }

  applySort() {
    this.filteredContracts.sort((a, b) => {
      const aVal = (a as any)[this.sortColumn] || '';
      const bVal = (b as any)[this.sortColumn] || '';

      if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadContracts();
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadContracts();
    }
  }

  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadContracts();
    }
  }

  get pageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(this.totalPages, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  }

  /**
   * Open contract details dialog
   */
  openContractDetails(contract: Contract) {
    this.selectedContract = contract;

    // Get secure PDF URL from blob storage via API
    this.contractService.getContractPdfUrl(contract.id).subscribe({
      next: (response) => {
        this.contractPdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(response.pdf_url);
      },
      error: (error) => {
        console.error('Error loading PDF URL:', error);
        this.contractPdfUrl = null;
        // Note: Dialog will still open but without PDF preview
      }
    });

    this.showDetailsDialog = true;

    // Load compliance results for this contract
    this.loadComplianceResults(contract.id);
  }

  /**
   * Close contract details dialog
   */
  closeDetailsDialog() {
    this.showDetailsDialog = false;
    this.selectedContract = null;
    this.contractPdfUrl = null;
    this.complianceResults = null;
  }

  /**
   * Load compliance results for the selected contract
   */
  loadComplianceResults(contractId: string) {
    this.loadingCompliance = true;
    this.complianceService.getContractResults(contractId).subscribe({
      next: (results) => {
        this.complianceResults = results;
        this.loadingCompliance = false;
      },
      error: (error) => {
        console.error('Error loading compliance results:', error);
        this.loadingCompliance = false;
        // Set empty results on error
        this.complianceResults = {
          contract_id: contractId,
          results: [],
          summary: { total: 0, pass: 0, fail: 0, partial: 0, not_applicable: 0 }
        };
      }
    });
  }

  // Dropdown toggle methods
  toggleDropdown(dropdownName: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    this.openDropdown = this.openDropdown === dropdownName ? null : dropdownName;
  }

  isDropdownOpen(dropdownName: string): boolean {
    return this.openDropdown === dropdownName;
  }

  closeAllDropdowns() {
    this.openDropdown = null;
  }

  // Multi-select filter helpers
  toggleContractorParty(party: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    if (party === 'Any') {
      this.filters.contractor_party = [];
    } else {
      const index = this.filters.contractor_party.indexOf(party);
      if (index > -1) {
        this.filters.contractor_party.splice(index, 1);
      } else {
        this.filters.contractor_party.push(party);
      }
    }
    this.onFilterChange();
  }

  isContractorPartySelected(party: string): boolean {
    return this.filters.contractor_party.includes(party);
  }

  toggleContractingParty(party: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    if (party === 'Any') {
      this.filters.contracting_party = [];
    } else {
      const index = this.filters.contracting_party.indexOf(party);
      if (index > -1) {
        this.filters.contracting_party.splice(index, 1);
      } else {
        this.filters.contracting_party.push(party);
      }
    }
    this.onFilterChange();
  }

  isContractingPartySelected(party: string): boolean {
    return this.filters.contracting_party.includes(party);
  }

  toggleGoverningLawState(state: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    if (state === 'Any') {
      this.filters.governing_law_state = [];
    } else {
      const index = this.filters.governing_law_state.indexOf(state);
      if (index > -1) {
        this.filters.governing_law_state.splice(index, 1);
      } else {
        this.filters.governing_law_state.push(state);
      }
    }
    this.onFilterChange();
  }

  isGoverningLawStateSelected(state: string): boolean {
    return this.filters.governing_law_state.includes(state);
  }

  toggleContractType(type: string, event?: Event) {
    if (event) {
      event.stopPropagation();
    }
    if (type === 'Any') {
      this.filters.contract_type = [];
    } else {
      const index = this.filters.contract_type.indexOf(type);
      if (index > -1) {
        this.filters.contract_type.splice(index, 1);
      } else {
        this.filters.contract_type.push(type);
      }
    }
    this.onFilterChange();
  }

  isContractTypeSelected(type: string): boolean {
    return this.filters.contract_type.includes(type);
  }

  /**
   * Format date for display
   * Treats dates as absolute dates (not UTC) to avoid timezone conversion
   */
  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';

    // Parse as absolute date without timezone conversion
    // Expected format: YYYY-MM-DD or ISO string
    const parts = dateString.split('T')[0].split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1; // JS months are 0-indexed
      const day = parseInt(parts[2], 10);

      const date = new Date(year, month, day);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    }

    return dateString;
  }

  // ============================================================================
  // CONTRACT UPLOAD METHODS
  // ============================================================================

  openUploadModal(): void {
    this.showUploadModal = true;
    this.selectedFile = null;
  }

  closeUploadModal(): void {
    this.showUploadModal = false;
    this.selectedFile = null;
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingFile = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFileSelection(files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingFile = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingFile = false;
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileSelection(input.files[0]);
    }
  }

  handleFileSelection(file: File): void {
    const validationError = this.uploadService.validateFile(file);
    if (validationError) {
      this.toastService.error('Invalid File', validationError);
      return;
    }

    // Server handles duplicate checking and automatic renaming
    this.selectedFile = file;
  }

  uploadFile(): void {
    if (!this.selectedFile) {
      return;
    }

    // Save filename before upload to use in toast
    const uploadingFilename = this.selectedFile.name;

    this.uploadService.uploadContract(this.selectedFile).subscribe({
      next: (response) => {
        // Close modal immediately
        this.closeUploadModal();

        // Show info toast that upload is processing
        // Use the actual filename from response (which may have versioning like _1, _2, etc.)
        const actualFilename = response.filename || uploadingFilename;
        this.toastService.info(
          'Upload Started',
          `Contract "${actualFilename}" is being processed. Check the Jobs page for progress.`
        );

        // Reset state
        this.selectedFile = null;
      },
      error: (error) => {
        this.toastService.error('Upload Failed', error.message || 'Failed to upload contract');
      }
    });
  }

  formatFileSize(bytes: number): string {
    return this.uploadService.formatFileSize(bytes);
  }

  /**
   * Open contract details by ID (used when navigating from Jobs page)
   */
  openContractById(contractId: string): void {
    // Try to find contract in already loaded contracts
    const contract = this.filteredContracts.find(c => c.id === contractId);

    if (contract) {
      // Contract is already loaded, open it
      this.openContractDetails(contract);
    } else {
      // Contract not in current page, fetch it from API
      this.contractService.getContractById(contractId).subscribe({
        next: (fetchedContract) => {
          // Transform to local Contract interface (camelCase to snake_case)
          const localContract: Contract = {
            id: fetchedContract.id,
            filename: fetchedContract.title || '',  // Use title as filename
            contractor_party: fetchedContract.contractorParty || '',
            contracting_party: fetchedContract.contractingParty || '',
            governing_law_state: fetchedContract.governing_law_state || '',
            contract_type: fetchedContract.contract_type || '',
            effective_date: fetchedContract.effective_date || '',
            expiration_date: fetchedContract.expiration_date || '',
            contract_value: fetchedContract.contract_value || ''
          };
          this.openContractDetails(localContract);
        },
        error: (error) => {
          console.error('Error loading contract:', error);
          this.toastService.error('Contract Not Found', `Could not load contract with ID: ${contractId}`);
        }
      });
    }
  }
}
