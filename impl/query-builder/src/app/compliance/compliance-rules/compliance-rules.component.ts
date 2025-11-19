import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import {
  ComplianceRule,
  RuleSeverity,
  Category,
  RuleSet,
  RuleSetWithRuleCount,
  PREDEFINED_CATEGORIES,
  SEVERITY_OPTIONS,
  getSeverityColor,
  formatDate
} from '../models/compliance.models';
import { ComplianceService } from '../services/compliance.service';
import { RuleSetService } from '../services/rule-set.service';
import { ToastService } from '../../shared/services/toast.service';

@Component({
  selector: 'app-compliance-rules',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './compliance-rules.component.html',
  styleUrls: ['./compliance-rules.component.scss']
})
export class ComplianceRulesComponent implements OnInit {
  // Constants
  readonly SEVERITY_OPTIONS = SEVERITY_OPTIONS;
  readonly CATEGORIES = PREDEFINED_CATEGORIES;
  readonly Math = Math; // Expose Math to template

  // State
  rules: ComplianceRule[] = [];
  filteredRules: ComplianceRule[] = [];
  loading: boolean = false;
  categories: Category[] = PREDEFINED_CATEGORIES; // Initialize with predefined categories
  ruleSets: RuleSetWithRuleCount[] = [];
  ruleSetMap: Map<string, RuleSetWithRuleCount> = new Map(); // Quick lookup by ID

  // Filters
  filterActiveOnly: boolean = true;
  filterCategory: string = '';
  filterSeverity: string = '';
  filterRuleSet: string = '';
  searchText: string = '';

  // Dropdown state
  openDropdown: string | null = null;

  // Sorting
  sortField: 'name' | 'severity' | 'category' | 'updated_date' = 'updated_date';
  sortDirection: 'asc' | 'desc' = 'desc';

  // Selection
  selectedRuleIds: Set<string> = new Set();

  // Pagination
  currentPage: number = 1;
  itemsPerPage: number = 20;
  totalPages: number = 1;

  constructor(
    private complianceService: ComplianceService,
    private ruleSetService: RuleSetService,
    private toastService: ToastService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadCategories();
    this.loadRuleSets();

    // Check for query parameters (e.g., from "View Rules" button on Rule Sets page)
    this.route.queryParams.subscribe(params => {
      if (params['rule_set_id']) {
        this.filterRuleSet = params['rule_set_id'];
      }
    });

    this.loadRules();
  }

  /**
   * Load all categories
   */
  loadCategories(): void {
    this.complianceService.getCategories().subscribe({
      next: (categories) => {
        this.categories = categories;
      },
      error: (error) => {
        console.error('Error loading categories:', error);
        // Use predefined categories as fallback
        this.categories = PREDEFINED_CATEGORIES;
      }
    });
  }

  /**
   * Load all rule sets with counts
   */
  loadRuleSets(): void {
    this.ruleSetService.getRuleSetsWithCounts(true).subscribe({
      next: (ruleSets) => {
        this.ruleSets = ruleSets;
        // Build map for quick lookup
        this.ruleSetMap.clear();
        this.ruleSets.forEach(rs => this.ruleSetMap.set(rs.id, rs));
      },
      error: (error) => {
        console.error('Error loading rule sets:', error);
      }
    });
  }

  /**
   * Load compliance rules with current filters
   */
  loadRules(): void {
    this.loading = true;
    this.complianceService.getRules(
      this.filterActiveOnly,
      this.filterCategory || undefined,
      this.filterSeverity || undefined
    ).subscribe({
      next: (rules) => {
        this.rules = rules;
        this.applyFiltersAndSort();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading rules:', error);
        this.toastService.error('Error loading compliance rules');
        this.loading = false;
      }
    });
  }

  /**
   * Apply search filter and sorting
   */
  applyFiltersAndSort(): void {
    let filtered = [...this.rules];

    // Apply search filter
    if (this.searchText.trim()) {
      const search = this.searchText.toLowerCase();
      filtered = filtered.filter(rule =>
        rule.name.toLowerCase().includes(search) ||
        rule.description.toLowerCase().includes(search) ||
        rule.category.toLowerCase().includes(search)
      );
    }

    // Apply rule set filter
    if (this.filterRuleSet) {
      filtered = filtered.filter(rule =>
        rule.rule_set_ids && rule.rule_set_ids.includes(this.filterRuleSet)
      );
    }

    // Sort
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (this.sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'severity':
          const severityOrder = { 'critical': 0, 'high': 1, 'medium': 2, 'low': 3 };
          comparison = severityOrder[a.severity] - severityOrder[b.severity];
          break;
        case 'category':
          comparison = a.category.localeCompare(b.category);
          break;
        case 'updated_date':
          comparison = new Date(a.updated_date).getTime() - new Date(b.updated_date).getTime();
          break;
      }

      return this.sortDirection === 'asc' ? comparison : -comparison;
    });

    this.filteredRules = filtered;
    this.updatePagination();
  }

  /**
   * Update pagination
   */
  updatePagination(): void {
    this.totalPages = Math.ceil(this.filteredRules.length / this.itemsPerPage);
    if (this.currentPage > this.totalPages) {
      this.currentPage = Math.max(1, this.totalPages);
    }
  }

  /**
   * Get paginated rules for current page
   */
  getPaginatedRules(): ComplianceRule[] {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    return this.filteredRules.slice(startIndex, endIndex);
  }

  /**
   * Sort by field
   */
  sortBy(field: 'name' | 'severity' | 'category' | 'updated_date'): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.applyFiltersAndSort();
  }

  /**
   * Filter changed - reload rules
   */
  onFilterChange(): void {
    this.currentPage = 1;
    this.loadRules();
  }

  /**
   * Search text changed
   */
  onSearchChange(): void {
    this.currentPage = 1;
    this.applyFiltersAndSort();
  }

  /**
   * Toggle rule selection
   */
  toggleSelection(ruleId: string): void {
    if (this.selectedRuleIds.has(ruleId)) {
      this.selectedRuleIds.delete(ruleId);
    } else {
      this.selectedRuleIds.add(ruleId);
    }
  }

  /**
   * Select all visible rules
   */
  selectAll(): void {
    this.getPaginatedRules().forEach(rule => {
      this.selectedRuleIds.add(rule.id);
    });
  }

  /**
   * Deselect all rules
   */
  deselectAll(): void {
    this.selectedRuleIds.clear();
  }

  /**
   * Navigate to create new rule
   */
  createRule(): void {
    this.router.navigate(['/compliance/rules/new']);
  }

  /**
   * Navigate to edit rule
   */
  editRule(rule: ComplianceRule): void {
    this.router.navigate(['/compliance/rules/edit', rule.id]);
  }

  /**
   * View rule details
   */
  viewRule(rule: ComplianceRule): void {
    this.router.navigate(['/compliance/rules/view', rule.id]);
  }

  /**
   * Delete a rule
   */
  deleteRule(rule: ComplianceRule): void {
    if (!confirm(`Are you sure you want to delete the rule "${rule.name}"?`)) {
      return;
    }

    this.complianceService.deleteRule(rule.id).subscribe({
      next: () => {
        this.toastService.success(`Rule "${rule.name}" deleted successfully`);
        this.loadRules();
      },
      error: (error) => {
        console.error('Error deleting rule:', error);
        this.toastService.error('Error deleting rule', error.message);
      }
    });
  }

  /**
   * Toggle rule active status
   */
  toggleRuleStatus(rule: ComplianceRule): void {
    const newStatus = !rule.active;
    this.complianceService.updateRule(rule.id, { active: newStatus }).subscribe({
      next: () => {
        rule.active = newStatus;
        this.toastService.success(
          `Rule "${rule.name}" ${newStatus ? 'activated' : 'deactivated'}`
        );
      },
      error: (error) => {
        console.error('Error updating rule status:', error);
        this.toastService.error('Error updating rule status', error.message);
      }
    });
  }

  /**
   * Delete selected rules
   */
  deleteSelected(): void {
    if (this.selectedRuleIds.size === 0) {
      this.toastService.warning('No rules selected');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${this.selectedRuleIds.size} selected rule(s)?`)) {
      return;
    }

    const deletePromises: Promise<any>[] = [];
    this.selectedRuleIds.forEach(ruleId => {
      deletePromises.push(
        this.complianceService.deleteRule(ruleId).toPromise()
      );
    });

    Promise.all(deletePromises).then(
      () => {
        this.toastService.success(`${this.selectedRuleIds.size} rule(s) deleted successfully`);
        this.selectedRuleIds.clear();
        this.loadRules();
      },
      (error) => {
        console.error('Error deleting rules:', error);
        this.toastService.error('Error deleting some rules', error.message);
        this.loadRules(); // Reload to show actual state
      }
    );
  }

  /**
   * Navigate to dashboard
   */
  viewDashboard(): void {
    this.router.navigate(['/compliance/dashboard']);
  }

  /**
   * Navigate to rule sets management page
   */
  manageRuleSets(): void {
    this.router.navigate(['/compliance/rule-sets']);
  }

  /**
   * Export rules to CSV
   */
  exportToCSV(): void {
    if (this.filteredRules.length === 0) {
      this.toastService.warning('No rules to export');
      return;
    }

    const headers = ['Name', 'Description', 'Severity', 'Category', 'Active', 'Created', 'Updated'];
    const rows = this.filteredRules.map(rule => [
      rule.name,
      rule.description,
      rule.severity,
      rule.category,
      rule.active ? 'Yes' : 'No',
      formatDate(rule.created_date),
      formatDate(rule.updated_date)
    ]);

    let csv = headers.join(',') + '\n';
    rows.forEach(row => {
      csv += row.map(cell => `"${cell}"`).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `compliance-rules-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);

    this.toastService.success('Rules exported to CSV');
  }

  /**
   * Refresh rules list
   */
  refresh(): void {
    this.loadRules();
  }

  // Helper methods for template
  getSeverityColor(severity: RuleSeverity): string {
    return getSeverityColor(severity);
  }

  formatDate(dateString: string): string {
    return formatDate(dateString);
  }

  getCategoryName(categoryId: string): string {
    const category = this.categories.find(c => c.name === categoryId);
    return category ? category.display_name : categoryId;
  }

  /**
   * Get rule set names for a rule
   */
  getRuleSetNames(rule: ComplianceRule): string[] {
    if (!rule.rule_set_ids || rule.rule_set_ids.length === 0) {
      return [];
    }
    return rule.rule_set_ids
      .map(id => this.ruleSetMap.get(id)?.name)
      .filter(name => name !== undefined) as string[];
  }

  /**
   * Get rule set name by ID
   */
  getRuleSetName(ruleSetId: string): string {
    return this.ruleSetMap.get(ruleSetId)?.name || ruleSetId;
  }

  // Dropdown management
  toggleDropdown(dropdownName: string, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.openDropdown = this.openDropdown === dropdownName ? null : dropdownName;
  }

  isDropdownOpen(dropdownName: string): boolean {
    return this.openDropdown === dropdownName;
  }

  closeAllDropdowns(): void {
    this.openDropdown = null;
  }

  // Pagination helpers
  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages) {
      this.currentPage = page;
    }
  }

  getPageNumbers(): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    const half = Math.floor(maxVisible / 2);

    let start = Math.max(1, this.currentPage - half);
    let end = Math.min(this.totalPages, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    return pages;
  }
}
