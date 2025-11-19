import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  ComplianceSummary,
  RuleSummary,
  Category,
  RuleSeverity,
  PREDEFINED_CATEGORIES,
  SEVERITY_OPTIONS,
  getSeverityColor
} from '../models/compliance.models';
import { ComplianceService } from '../services/compliance.service';
import { ToastService } from '../../shared/services/toast.service';

@Component({
  selector: 'app-compliance-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './compliance-dashboard.component.html',
  styleUrls: ['./compliance-dashboard.component.scss']
})
export class ComplianceDashboardComponent implements OnInit {
  // Constants
  readonly SEVERITY_OPTIONS = SEVERITY_OPTIONS;
  readonly CATEGORIES = PREDEFINED_CATEGORIES;

  // State
  summary: ComplianceSummary | null = null;
  loading: boolean = false;
  categories: Category[] = PREDEFINED_CATEGORIES;

  // Filters
  filterCategory: string = '';
  filterSeverity: string = '';

  // Filtered data
  filteredRulesSummary: RuleSummary[] = [];

  constructor(
    private complianceService: ComplianceService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  /**
   * Load dashboard summary data
   */
  loadDashboard(): void {
    this.loading = true;
    this.complianceService.getSummary().subscribe({
      next: (summary: ComplianceSummary) => {
        this.summary = summary;
        this.applyFilters();
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading dashboard:', error);
        this.toastService.error('Error loading dashboard data');
        this.loading = false;
      }
    });
  }

  /**
   * Apply category and severity filters
   */
  applyFilters(): void {
    if (!this.summary) {
      this.filteredRulesSummary = [];
      return;
    }

    let filtered = [...this.summary.rules_summary];

    // Apply category filter
    if (this.filterCategory) {
      filtered = filtered.filter(r => r.category === this.filterCategory);
    }

    // Apply severity filter
    if (this.filterSeverity) {
      filtered = filtered.filter(r => r.severity === this.filterSeverity);
    }

    this.filteredRulesSummary = filtered;
  }

  /**
   * Handle filter change
   */
  onFilterChange(): void {
    this.applyFilters();
  }

  /**
   * Refresh dashboard
   */
  refresh(): void {
    this.loadDashboard();
  }

  /**
   * Navigate to rules list
   */
  viewAllRules(): void {
    this.router.navigate(['/compliance/rules']);
  }

  /**
   * Navigate to rule editor
   */
  viewRule(ruleId: string): void {
    this.router.navigate(['/compliance/rules/view', ruleId]);
  }

  /**
   * Navigate to rule editor for editing
   */
  editRule(ruleId: string): void {
    this.router.navigate(['/compliance/rules/edit', ruleId]);
  }

  /**
   * Navigate to evaluation trigger page
   */
  startEvaluation(): void {
    this.router.navigate(['/compliance/evaluate']);
  }

  /**
   * Navigate to job monitoring page
   */
  viewJobs(): void {
    this.router.navigate(['/compliance/jobs']);
  }

  /**
   * Navigate to results viewer page
   */
  viewResults(): void {
    this.router.navigate(['/compliance/results']);
  }

  /**
   * Navigate to create new rule
   */
  createRule(): void {
    this.router.navigate(['/compliance/rules/new']);
  }

  /**
   * Get severity color class
   */
  getSeverityColor(severity: RuleSeverity): string {
    return getSeverityColor(severity);
  }

  /**
   * Get category name from ID
   */
  getCategoryName(categoryId: string): string {
    const category = this.categories.find(c => c.name === categoryId);
    return category ? category.display_name : categoryId;
  }

  /**
   * Calculate percentage
   */
  getPercentage(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  /**
   * Get pass rate color class
   */
  getPassRateColor(passRate: number): string {
    if (passRate >= 90) return 'success';
    if (passRate >= 70) return 'warning';
    return 'danger';
  }

  /**
   * Get stale results badge variant
   */
  getStaleResultsBadge(staleCount: number): string {
    if (staleCount === 0) return 'success';
    if (staleCount < 5) return 'warning';
    return 'danger';
  }

  /**
   * Get overall stats for filtered results
   */
  getFilteredStats(): { total: number; evaluated: number; pass: number; fail: number; passRate: number } {
    if (this.filteredRulesSummary.length === 0) {
      return { total: 0, evaluated: 0, pass: 0, fail: 0, passRate: 0 };
    }

    const total = this.filteredRulesSummary.reduce((sum, r) => sum + r.total_evaluated, 0);
    const pass = this.filteredRulesSummary.reduce((sum, r) => sum + r.pass_count, 0);
    const fail = this.filteredRulesSummary.reduce((sum, r) => sum + r.fail_count, 0);
    const passRate = total > 0 ? Math.round((pass / total) * 100) : 0;

    return {
      total: this.filteredRulesSummary.length,
      evaluated: total,
      pass,
      fail,
      passRate
    };
  }

  /**
   * Get total stale results count
   */
  getTotalStaleResults(): number {
    if (!this.summary) return 0;
    return this.summary.rules_summary.reduce((sum, r) => sum + r.stale_count, 0);
  }

  /**
   * Get rules with stale results
   */
  getRulesWithStaleResults(): RuleSummary[] {
    if (!this.filteredRulesSummary) return [];
    return this.filteredRulesSummary.filter(r => r.stale_count > 0);
  }

  /**
   * Sort rules by pass rate (ascending)
   */
  sortByPassRate(): void {
    this.filteredRulesSummary.sort((a, b) => {
      const aRate = a.total_evaluated > 0 ? (a.pass_count / a.total_evaluated) : 0;
      const bRate = b.total_evaluated > 0 ? (b.pass_count / b.total_evaluated) : 0;
      return aRate - bRate;
    });
  }

  /**
   * Sort rules by fail count (descending)
   */
  sortByFailCount(): void {
    this.filteredRulesSummary.sort((a, b) => b.fail_count - a.fail_count);
  }
}
