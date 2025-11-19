import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import {
  ComplianceResult,
  ContractEvaluationResults,
  RuleEvaluationResults,
  EvaluationResult,
  RuleSeverity,
  getResultColor,
  getSeverityColor,
  formatDate,
  RESULT_OPTIONS
} from '../models/compliance.models';
import { ComplianceService } from '../services/compliance.service';
import { ToastService } from '../../shared/services/toast.service';

/**
 * View modes for the results viewer
 */
type ViewMode = 'contract' | 'rule' | 'all';

@Component({
  selector: 'app-results-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './results-viewer.component.html',
  styleUrls: ['./results-viewer.component.scss']
})
export class ResultsViewerComponent implements OnInit {
  // View mode and filters
  viewMode: ViewMode = 'all';
  selectedContractId: string = '';
  selectedRuleId: string = '';
  resultFilter: EvaluationResult | '' = '';
  searchQuery: string = '';

  // Data
  contractResults: ContractEvaluationResults | null = null;
  ruleResults: RuleEvaluationResults | null = null;
  allResults: ComplianceResult[] = [];
  filteredResults: ComplianceResult[] = [];

  // Contract titles cache
  private contractTitles: Map<string, string> = new Map();
  private contractTitlesLoaded: boolean = false;

  // Available contracts for dropdown
  availableContracts: Array<{ id: string; title: string }> = [];

  // Available rules for dropdown
  availableRules: Array<{ id: string; name: string }> = [];
  private rulesLoaded: boolean = false;

  // UI state
  loading: boolean = false;
  selectedResult: ComplianceResult | null = null;
  showDetailModal: boolean = false;

  // Constants
  readonly RESULT_OPTIONS = RESULT_OPTIONS;

  constructor(
    private complianceService: ComplianceService,
    private toastService: ToastService,
    private route: ActivatedRoute,
    public router: Router
  ) {}

  ngOnInit(): void {
    // Check for query parameters to determine initial view mode
    this.route.queryParams.subscribe(params => {
      if (params['contract_id']) {
        this.selectedContractId = params['contract_id'];
        this.viewMode = 'contract';
        this.loadContractResults();
      } else if (params['rule_id']) {
        this.selectedRuleId = params['rule_id'];
        this.viewMode = 'rule';
        this.loadRuleResults();
      } else {
        this.viewMode = 'all';
        this.loadAllResults();
      }
    });
  }

  /**
   * Load all results across all contracts and rules
   */
  loadAllResults(): void {
    this.loading = true;
    this.loadContractTitles(); // Load contract titles for display
    this.complianceService.getAllResults().subscribe({
      next: (results: ComplianceResult[]) => {
        this.allResults = results;
        this.applyFilters();
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading results:', error);
        this.toastService.error('Failed to load results');
        this.loading = false;
      }
    });
  }

  /**
   * Load results for a specific contract
   */
  loadContractResults(): void {
    if (!this.selectedContractId) return;

    this.loading = true;
    this.loadContractTitles(); // Load contract titles for display
    this.complianceService.getContractResults(this.selectedContractId).subscribe({
      next: (results: ContractEvaluationResults) => {
        this.contractResults = results;
        this.allResults = results.results;
        this.applyFilters();
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading contract results:', error);
        this.toastService.error('Failed to load contract results');
        this.loading = false;
      }
    });
  }

  /**
   * Load results for a specific rule
   */
  loadRuleResults(): void {
    if (!this.selectedRuleId) return;

    this.loading = true;
    this.loadContractTitles(); // Load contract titles for display
    this.complianceService.getRuleResults(this.selectedRuleId).subscribe({
      next: (results: RuleEvaluationResults) => {
        this.ruleResults = results;
        this.allResults = results.results;
        this.applyFilters();
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading rule results:', error);
        this.toastService.error('Failed to load rule results');
        this.loading = false;
      }
    });
  }

  /**
   * Apply filters to results
   */
  applyFilters(): void {
    let filtered = [...this.allResults];

    // Filter by result status
    if (this.resultFilter) {
      filtered = filtered.filter(r => r.evaluation_result === this.resultFilter);
    }

    // Filter by search query (rule name, explanation, or evidence)
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(r =>
        r.rule_name.toLowerCase().includes(query) ||
        r.explanation.toLowerCase().includes(query) ||
        r.evidence.some(e => e.toLowerCase().includes(query))
      );
    }

    this.filteredResults = filtered;
  }

  /**
   * Change view mode
   */
  changeViewMode(mode: ViewMode): void {
    this.viewMode = mode;
    this.resultFilter = '';
    this.searchQuery = '';
    this.selectedResult = null;

    if (mode === 'all') {
      this.loadAllResults();
    } else if (mode === 'contract') {
      this.selectedContractId = '';
      this.contractResults = null;
      this.allResults = [];
      this.filteredResults = [];
      this.loadContractTitles(); // Load contracts for dropdown
    } else if (mode === 'rule') {
      this.selectedRuleId = '';
      this.ruleResults = null;
      this.allResults = [];
      this.filteredResults = [];
      this.loadRules(); // Load rules for dropdown
    }
  }

  /**
   * View result details
   */
  viewResultDetails(result: ComplianceResult): void {
    this.selectedResult = result;
    this.showDetailModal = true;
  }

  /**
   * Close detail modal
   */
  closeDetailModal(): void {
    this.showDetailModal = false;
    this.selectedResult = null;
  }

  /**
   * Get result color class
   */
  getResultColor(result: EvaluationResult): string {
    return getResultColor(result);
  }

  /**
   * Get severity color class
   */
  getSeverityColor(severity: RuleSeverity): string {
    return getSeverityColor(severity);
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string | null): string {
    return formatDate(dateString);
  }

  /**
   * Get result icon
   */
  getResultIcon(result: EvaluationResult): string {
    switch (result) {
      case 'pass': return '✅';
      case 'fail': return '❌';
      case 'partial': return '⚠️';
      case 'not_applicable': return 'ℹ️';
      default: return '❓';
    }
  }

  /**
   * Navigate to rule results
   */
  viewRule(ruleId: string): void {
    this.viewMode = 'rule';
    this.selectedRuleId = ruleId;
    this.loadRules(); // Ensure rules are loaded for the dropdown
    this.loadRuleResults();
  }

  /**
   * Navigate to contract results
   */
  viewContract(contractId: string): void {
    this.viewMode = 'contract';
    this.selectedContractId = contractId;
    this.loadContractTitles(); // Ensure contracts are loaded for the dropdown
    this.loadContractResults();
  }

  /**
   * Export results to CSV
   */
  exportResults(): void {
    if (this.filteredResults.length === 0) {
      this.toastService.warning('No results to export');
      return;
    }

    const csv = this.generateCSV(this.filteredResults);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `compliance-results-${new Date().toISOString()}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  /**
   * Generate CSV content from results
   */
  private generateCSV(results: ComplianceResult[]): string {
    const headers = [
      'Contract ID',
      'Rule Name',
      'Result',
      'Confidence',
      'Evaluated Date',
      'Explanation',
      'Evidence'
    ];

    const rows = results.map(r => [
      r.contract_id,
      r.rule_name,
      r.evaluation_result,
      r.confidence.toString(),
      r.evaluated_date,
      r.explanation.replace(/"/g, '""'),
      r.evidence.join('; ').replace(/"/g, '""')
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    return csvContent;
  }

  /**
   * Calculate pass rate for current view
   */
  getPassRate(): number {
    if (this.filteredResults.length === 0) return 0;
    const passCount = this.filteredResults.filter(r => r.evaluation_result === 'pass').length;
    return Math.round((passCount / this.filteredResults.length) * 100);
  }

  /**
   * Get result counts
   */
  getResultCounts(): { pass: number; fail: number; partial: number; not_applicable: number } {
    return {
      pass: this.filteredResults.filter(r => r.evaluation_result === 'pass').length,
      fail: this.filteredResults.filter(r => r.evaluation_result === 'fail').length,
      partial: this.filteredResults.filter(r => r.evaluation_result === 'partial').length,
      not_applicable: this.filteredResults.filter(r => r.evaluation_result === 'not_applicable').length
    };
  }

  /**
   * Get average confidence
   */
  getAverageConfidence(): number {
    if (this.filteredResults.length === 0) return 0;
    const sum = this.filteredResults.reduce((acc, r) => acc + r.confidence, 0);
    return Math.round((sum / this.filteredResults.length) * 100) / 100;
  }

  /**
   * Load contract titles from the backend
   * Builds a map of contract ID -> title for fast lookup
   * Also populates the availableContracts array for dropdowns
   */
  private loadContractTitles(): void {
    if (this.contractTitlesLoaded) return;

    this.complianceService.getContracts().subscribe({
      next: (response: any) => {
        // Handle different response formats
        let contracts: any[] = [];
        if (Array.isArray(response)) {
          contracts = response;
        } else if (response && Array.isArray(response.contracts)) {
          contracts = response.contracts;
        } else if (response && Array.isArray(response.data)) {
          contracts = response.data;
        }

        // Build the title map and available contracts list
        this.availableContracts = [];
        contracts.forEach(contract => {
          if (contract.id && contract.title) {
            this.contractTitles.set(contract.id, contract.title);
            this.availableContracts.push({
              id: contract.id,
              title: contract.title
            });
          }
        });

        // Sort by title for easier selection
        this.availableContracts.sort((a, b) => a.title.localeCompare(b.title));

        this.contractTitlesLoaded = true;
        console.log(`Loaded ${this.contractTitles.size} contract titles`);
      },
      error: (error: any) => {
        console.error('Error loading contract titles:', error);
        this.contractTitlesLoaded = true; // Mark as loaded to prevent retries
      }
    });
  }

  /**
   * Get the title for a contract ID
   * Returns the title if found, otherwise returns the ID itself
   */
  getContractTitle(contractId: string): string {
    return this.contractTitles.get(contractId) || contractId;
  }

  /**
   * Load rules from the backend for dropdown
   * Populates the availableRules array with active rules
   */
  private loadRules(): void {
    if (this.rulesLoaded) return;

    this.complianceService.getRules(true).subscribe({
      next: (rules: any[]) => {
        this.availableRules = rules.map(rule => ({
          id: rule.id,
          name: rule.name
        }));

        // Sort by name for easier selection
        this.availableRules.sort((a, b) => a.name.localeCompare(b.name));

        this.rulesLoaded = true;
        console.log(`Loaded ${this.availableRules.length} rules`);
      },
      error: (error: any) => {
        console.error('Error loading rules:', error);
        this.rulesLoaded = true; // Mark as loaded to prevent retries
      }
    });
  }
}
