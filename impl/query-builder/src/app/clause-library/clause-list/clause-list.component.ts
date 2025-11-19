import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ClauseLibraryService, Clause, Category } from '../../shared/services/clause-library.service';
import { ToastService } from '../../shared/services/toast.service';
import { CategoryTreeComponent } from '../category-tree/category-tree';

@Component({
  selector: 'app-clause-list',
  standalone: true,
  imports: [CommonModule, FormsModule, CategoryTreeComponent],
  templateUrl: './clause-list.component.html',
  styleUrls: ['./clause-list.component.scss']
})
export class ClauseListComponent implements OnInit {
  // Data
  clauses: Clause[] = [];
  categories: Category[] = [];
  filteredClauses: Clause[] = [];

  // Pagination
  currentPage = 1;
  pageSize = 20;
  totalClauses = 0;
  totalPages = 0;

  // Filters
  searchQuery = '';
  selectedCategory: string = '';
  selectedStatus: string = 'active';
  selectedRiskLevel: string = '';
  selectedComplexity: string = '';
  selectedContractType: string = '';

  // Sorting
  sortField: 'name' | 'created_date' | 'modified_date' | 'usage' = 'name';
  sortDirection: 'asc' | 'desc' = 'asc';

  // UI State
  isLoading = false;
  viewMode: 'grid' | 'list' = 'list';
  selectedClauses: Set<string> = new Set();
  showFilters = false;

  // Options
  statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'active', label: 'Active' },
    { value: 'draft', label: 'Draft' },
    { value: 'archived', label: 'Archived' }
  ];

  riskLevelOptions = [
    { value: '', label: 'All Risk Levels' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' }
  ];

  complexityOptions = [
    { value: '', label: 'All Complexities' },
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' }
  ];

  contractTypeOptions = [
    { value: '', label: 'All Contract Types' },
    { value: 'MSA', label: 'Master Service Agreement' },
    { value: 'SOW', label: 'Statement of Work' },
    { value: 'NDA', label: 'Non-Disclosure Agreement' },
    { value: 'SLA', label: 'Service Level Agreement' }
  ];

  constructor(
    private clauseLibraryService: ClauseLibraryService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadCategories();
    this.loadClauses();
  }

  /**
   * Load all categories for filter dropdown
   */
  loadCategories(): void {
    this.clauseLibraryService.getCategories().subscribe({
      next: (response) => {
        this.categories = response.categories;
      },
      error: (error) => {
        console.error('Error loading categories:', error);
        this.toastService.error('Load Failed', 'Failed to load categories');
      }
    });
  }

  /**
   * Load clauses with current filters and pagination
   */
  loadClauses(): void {
    this.isLoading = true;

    const filters = {
      category_id: this.selectedCategory || undefined,
      search: this.searchQuery || undefined,
      status: this.selectedStatus || undefined,
      risk_level: this.selectedRiskLevel || undefined,
      contract_types: this.selectedContractType ? [this.selectedContractType] : undefined,
      limit: this.pageSize,
      offset: (this.currentPage - 1) * this.pageSize
    };

    this.clauseLibraryService.getClauses(filters).subscribe({
      next: (response) => {
        this.clauses = response.clauses;
        this.totalClauses = response.total;
        this.totalPages = Math.ceil(this.totalClauses / this.pageSize);
        this.applySorting();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading clauses:', error);
        this.toastService.error('Load Failed', 'Failed to load clauses');
        this.isLoading = false;
      }
    });
  }

  /**
   * Apply sorting to clauses
   */
  applySorting(): void {
    this.clauses.sort((a, b) => {
      let comparison = 0;

      switch (this.sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'created_date':
          comparison = new Date(a.audit.created_date).getTime() - new Date(b.audit.created_date).getTime();
          break;
        case 'modified_date':
          comparison = new Date(a.audit.modified_date).getTime() - new Date(b.audit.modified_date).getTime();
          break;
        case 'usage':
          comparison = a.usage_stats.times_used - b.usage_stats.times_used;
          break;
      }

      return this.sortDirection === 'asc' ? comparison : -comparison;
    });
  }

  /**
   * Handle search input
   */
  onSearch(): void {
    this.currentPage = 1;
    this.loadClauses();
  }

  /**
   * Handle filter change
   */
  onFilterChange(): void {
    this.currentPage = 1;
    this.loadClauses();
  }

  /**
   * Handle category selection from tree
   */
  onCategorySelected(categoryId: string): void {
    this.selectedCategory = categoryId;
    this.currentPage = 1;
    this.loadClauses();
  }

  /**
   * Handle sort change
   */
  onSort(field: 'name' | 'created_date' | 'modified_date' | 'usage'): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applySorting();
  }

  /**
   * Toggle filters panel
   */
  toggleFilters(): void {
    this.showFilters = !this.showFilters;
  }

  /**
   * Clear all filters
   */
  clearFilters(): void {
    this.searchQuery = '';
    this.selectedCategory = '';
    this.selectedStatus = 'active';
    this.selectedRiskLevel = '';
    this.selectedComplexity = '';
    this.selectedContractType = '';
    this.currentPage = 1;
    this.loadClauses();
  }

  /**
   * Navigate to clause details/viewer
   */
  viewClause(clauseId: string): void {
    this.router.navigate(['/clause-library/view', clauseId]);
  }

  /**
   * Navigate to clause editor for editing
   */
  editClause(clauseId: string): void {
    this.router.navigate(['/clause-library/edit', clauseId]);
  }

  /**
   * Navigate to clause editor for creating new clause
   */
  createNewClause(): void {
    this.router.navigate(['/clause-library/new']);
  }

  /**
   * Delete a clause
   */
  deleteClause(clauseId: string, clauseName: string): void {
    if (!confirm(`Are you sure you want to delete "${clauseName}"?`)) {
      return;
    }

    this.clauseLibraryService.deleteClause(clauseId).subscribe({
      next: (response) => {
        this.toastService.success('Deleted', response.message);
        this.loadClauses();
      },
      error: (error) => {
        console.error('Error deleting clause:', error);
        this.toastService.error('Delete Failed', 'Failed to delete clause');
      }
    });
  }

  /**
   * Toggle clause selection
   */
  toggleSelection(clauseId: string): void {
    if (this.selectedClauses.has(clauseId)) {
      this.selectedClauses.delete(clauseId);
    } else {
      this.selectedClauses.add(clauseId);
    }
  }

  /**
   * Select all clauses on current page
   */
  selectAll(): void {
    this.clauses.forEach(clause => this.selectedClauses.add(clause.id));
  }

  /**
   * Deselect all clauses
   */
  deselectAll(): void {
    this.selectedClauses.clear();
  }

  /**
   * Bulk delete selected clauses
   */
  bulkDelete(): void {
    if (this.selectedClauses.size === 0) {
      this.toastService.warning('No Selection', 'Please select clauses to delete');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${this.selectedClauses.size} clause(s)?`)) {
      return;
    }

    // TODO: Implement bulk delete endpoint
    this.toastService.info('Not Implemented', 'Bulk delete feature coming soon');
  }

  /**
   * Toggle view mode between grid and list
   */
  toggleViewMode(): void {
    this.viewMode = this.viewMode === 'grid' ? 'list' : 'grid';
  }

  /**
   * Pagination: Go to page
   */
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
      this.loadClauses();
    }
  }

  /**
   * Pagination: Next page
   */
  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadClauses();
    }
  }

  /**
   * Pagination: Previous page
   */
  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadClauses();
    }
  }

  /**
   * Get risk level badge class
   */
  getRiskBadgeClass(riskLevel: string): string {
    switch (riskLevel) {
      case 'high': return 'badge-risk-high';
      case 'medium': return 'badge-risk-medium';
      case 'low': return 'badge-risk-low';
      default: return 'badge-risk-default';
    }
  }

  /**
   * Get complexity badge class
   */
  getComplexityBadgeClass(complexity: string): string {
    switch (complexity) {
      case 'high': return 'badge-complexity-high';
      case 'medium': return 'badge-complexity-medium';
      case 'low': return 'badge-complexity-low';
      default: return 'badge-complexity-default';
    }
  }

  /**
   * Get status badge class
   */
  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'active': return 'badge-status-active';
      case 'draft': return 'badge-status-draft';
      case 'archived': return 'badge-status-archived';
      default: return 'badge-status-default';
    }
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
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
    const maxPages = 7;

    if (this.totalPages <= maxPages) {
      for (let i = 1; i <= this.totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      if (this.currentPage > 3) {
        pages.push(-1); // Ellipsis
      }

      // Show pages around current page
      for (let i = Math.max(2, this.currentPage - 1); i <= Math.min(this.totalPages - 1, this.currentPage + 1); i++) {
        pages.push(i);
      }

      if (this.currentPage < this.totalPages - 2) {
        pages.push(-1); // Ellipsis
      }

      // Always show last page
      pages.push(this.totalPages);
    }

    return pages;
  }
}
