import { Component, OnInit, EventEmitter, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ComplianceService } from '../services/compliance.service';
import { ToastService } from '../../shared/services/toast.service';

/**
 * Contract metadata from Contracts collection
 */
export interface Contract {
  id: string;
  title: string;
  contractor_party?: string;
  contracting_party?: string;
  contract_type?: string;
  governing_law?: string;
  governing_law_state?: string;
  contract_value?: number;
  contract_date?: string;
  effective_date?: string;
}

/**
 * Contract reference with ID and title for user display
 */
export interface ContractReference {
  id: string;
  title: string;
}

@Component({
  selector: 'app-contract-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './contract-selector.component.html',
  styleUrls: ['./contract-selector.component.scss']
})
export class ContractSelectorComponent implements OnInit {
  @Input() multiSelect: boolean = false;
  @Input() selectedContractIds: string[] = [];
  @Output() contractsSelected = new EventEmitter<ContractReference[]>();

  contracts: Contract[] = [];
  filteredContracts: Contract[] = [];
  loading: boolean = false;

  // Dropdown filters
  contractingPartyFilter: string = '';
  contractorPartyFilter: string = '';
  contractTypeFilter: string = '';
  governingLawFilter: string = '';

  // Pagination
  pageSize: number = 20;
  currentPage: number = 1;
  totalPages: number = 1;

  // Unique filter values
  contractTypes: string[] = [];
  contractorParties: string[] = [];
  contractingParties: string[] = [];
  governingLaws: string[] = [];

  constructor(
    private complianceService: ComplianceService
  ) {}

  ngOnInit(): void {
    this.loadContracts();
  }

  /**
   * Load contracts from backend
   */
  loadContracts(): void {
    this.loading = true;
    this.complianceService.getContracts().subscribe({
      next: (response: any) => {
        console.log('Contracts API response:', response);

        // Handle different response formats
        if (Array.isArray(response)) {
          this.contracts = response;
        } else if (response && Array.isArray(response.contracts)) {
          this.contracts = response.contracts;
        } else if (response && Array.isArray(response.data)) {
          this.contracts = response.data;
        } else {
          console.error('Unexpected response format:', response);
          this.contracts = [];
        }

        console.log('Parsed contracts:', this.contracts);
        this.extractFilterValues();
        this.applyFilters();
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading contracts:', error);
        this.contracts = [];
        this.loading = false;
      }
    });
  }

  /**
   * Extract unique values for filter dropdowns
   */
  extractFilterValues(): void {
    this.contractTypes = [...new Set(this.contracts
      .map(c => c.contract_type)
      .filter(t => t) as string[])].sort();

    this.contractorParties = [...new Set(this.contracts
      .map(c => c.contractor_party)
      .filter(p => p) as string[])].sort();

    this.contractingParties = [...new Set(this.contracts
      .map(c => c.contracting_party)
      .filter(p => p) as string[])].sort();

    this.governingLaws = [...new Set(this.contracts
      .map(c => c.governing_law_state)
      .filter(l => l) as string[])].sort();
  }

  /**
   * Apply filters to contract list
   */
  applyFilters(): void {
    let filtered = [...this.contracts];

    // Contracting party filter
    if (this.contractingPartyFilter) {
      filtered = filtered.filter(c => c.contracting_party === this.contractingPartyFilter);
    }

    // Contractor party filter
    if (this.contractorPartyFilter) {
      filtered = filtered.filter(c => c.contractor_party === this.contractorPartyFilter);
    }

    // Contract type filter
    if (this.contractTypeFilter) {
      filtered = filtered.filter(c => c.contract_type === this.contractTypeFilter);
    }

    // Governing law filter
    if (this.governingLawFilter) {
      filtered = filtered.filter(c => c.governing_law_state === this.governingLawFilter);
    }

    this.filteredContracts = filtered;
    this.totalPages = Math.ceil(filtered.length / this.pageSize);
    this.currentPage = 1;
  }

  /**
   * Get contracts for current page
   */
  getPagedContracts(): Contract[] {
    const start = (this.currentPage - 1) * this.pageSize;
    const end = start + this.pageSize;
    return this.filteredContracts.slice(start, end);
  }

  /**
   * Check if contract is selected
   */
  isContractSelected(contractId: string): boolean {
    return this.selectedContractIds.includes(contractId);
  }

  /**
   * Convert selected contract IDs to ContractReference objects
   */
  private getContractReferences(): ContractReference[] {
    return this.selectedContractIds
      .map(id => {
        const contract = this.contracts.find(c => c.id === id);
        return contract ? { id: contract.id, title: contract.title } : null;
      })
      .filter((ref): ref is ContractReference => ref !== null);
  }

  /**
   * Toggle contract selection
   */
  toggleContract(contractId: string): void {
    if (this.multiSelect) {
      const index = this.selectedContractIds.indexOf(contractId);
      if (index > -1) {
        this.selectedContractIds.splice(index, 1);
      } else {
        this.selectedContractIds.push(contractId);
      }
    } else {
      // Single select - replace selection
      this.selectedContractIds = [contractId];
    }

    this.contractsSelected.emit(this.getContractReferences());
  }

  /**
   * Select all filtered contracts (multi-select only)
   */
  selectAll(): void {
    if (!this.multiSelect) return;

    this.selectedContractIds = [...new Set([
      ...this.selectedContractIds,
      ...this.filteredContracts.map(c => c.id)
    ])];

    this.contractsSelected.emit(this.getContractReferences());
  }

  /**
   * Clear all selections
   */
  clearSelection(): void {
    this.selectedContractIds = [];
    this.contractsSelected.emit([]);
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.contractingPartyFilter = '';
    this.contractorPartyFilter = '';
    this.contractTypeFilter = '';
    this.governingLawFilter = '';
    this.applyFilters();
  }

  /**
   * Navigate to page
   */
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  /**
   * Format contract value for display
   */
  formatValue(value: number | undefined): string {
    if (!value) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string | undefined): string {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  /**
   * Get page numbers for pagination
   */
  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    const halfVisible = Math.floor(maxVisible / 2);

    let startPage = Math.max(1, this.currentPage - halfVisible);
    let endPage = Math.min(this.totalPages, startPage + maxVisible - 1);

    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    return pages;
  }
}
