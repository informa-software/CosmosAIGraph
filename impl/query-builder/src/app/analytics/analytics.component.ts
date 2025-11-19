import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  UserPreferencesService,
  UsageSummary,
  CostSavings,
  UsageTimeline,
  ModelUsage
} from '../shared/services/user-preferences.service';
import { ToastService } from '../shared/services/toast.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './analytics.component.html',
  styleUrls: ['./analytics.component.scss']
})
export class AnalyticsComponent implements OnInit {
  // State
  isLoading = false;
  usageSummary: UsageSummary | null = null;
  costSavings: CostSavings | null = null;
  usageTimeline: UsageTimeline | null = null;

  // NEW: Enhanced analytics data
  operationBreakdown: any[] = [];
  tokenEfficiency: any[] = [];
  errorAnalysis: any | null = null;

  // User email - matches backend LLM tracking (system user until auth is implemented)
  userEmail: string = 'system';

  // Selected time period
  selectedPeriod: number = 30; // days
  periodOptions = [
    { value: 7, label: 'Last 7 Days' },
    { value: 30, label: 'Last 30 Days' },
    { value: 90, label: 'Last 90 Days' },
    { value: 365, label: 'Last Year' }
  ];

  constructor(
    private userPreferencesService: UserPreferencesService,
    private toastService: ToastService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.userEmail = this.userPreferencesService.getCurrentUserEmail();
    this.loadAnalytics();
  }

  /**
   * Load all analytics data
   */
  loadAnalytics(): void {
    this.isLoading = true;

    // Load usage summary
    this.userPreferencesService.getUsageSummary(this.userEmail, this.selectedPeriod).subscribe({
      next: (summary) => {
        this.usageSummary = summary;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading usage summary:', error);
        this.toastService.error('Load Failed', 'Failed to load usage statistics.');
        this.isLoading = false;
      }
    });

    // Load cost savings
    this.userPreferencesService.getCostSavings(this.userEmail, this.selectedPeriod).subscribe({
      next: (savings) => {
        this.costSavings = savings;
      },
      error: (error) => {
        console.error('Error loading cost savings:', error);
      }
    });

    // Load usage timeline
    this.userPreferencesService.getUsageTimeline(this.userEmail, this.selectedPeriod).subscribe({
      next: (timeline) => {
        this.usageTimeline = timeline;
      },
      error: (error) => {
        console.error('Error loading usage timeline:', error);
      }
    });

    // Load operation breakdown
    this.userPreferencesService.getOperationBreakdown(this.userEmail, this.selectedPeriod).subscribe({
      next: (breakdown) => {
        this.operationBreakdown = breakdown.operations || [];
      },
      error: (error) => {
        console.error('Error loading operation breakdown:', error);
      }
    });

    // Load token efficiency
    this.userPreferencesService.getTokenEfficiency(this.userEmail, this.selectedPeriod).subscribe({
      next: (efficiency) => {
        this.tokenEfficiency = efficiency.operations || [];
      },
      error: (error) => {
        console.error('Error loading token efficiency:', error);
      }
    });

    // Load error analysis
    this.userPreferencesService.getErrorAnalysis(this.userEmail, this.selectedPeriod).subscribe({
      next: (analysis) => {
        this.errorAnalysis = analysis;
      },
      error: (error) => {
        console.error('Error loading error analysis:', error);
      }
    });
  }

  /**
   * Handle period selection change
   */
  onPeriodChange(): void {
    this.loadAnalytics();
  }

  /**
   * Get model display name
   */
  getModelDisplayName(modelName: string): string {
    const nameMap: { [key: string]: string } = {
      'gpt-4.1': 'GPT-4.1',
      'gpt-4.1-mini': 'GPT-4.1-mini'
    };
    return nameMap[modelName] || modelName;
  }

  /**
   * Get model badge class
   */
  getModelBadgeClass(modelName: string): string {
    if (modelName.includes('mini')) {
      return 'badge-secondary';
    }
    return 'badge-primary';
  }

  /**
   * Format currency
   */
  formatCurrency(value: number): string {
    return `$${value.toFixed(4)}`;
  }

  /**
   * Format number with commas
   */
  formatNumber(value: number): string {
    if (value === null || value === undefined) {
      return '0';
    }
    return value.toLocaleString();
  }

  /**
   * Format time in seconds
   */
  formatTime(seconds: number): string {
    if (seconds === null || seconds === undefined) {
      return '0s';
    }
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  }

  /**
   * Get savings percentage color class
   */
  getSavingsColorClass(percentage: number): string {
    if (percentage >= 50) return 'text-success-high';
    if (percentage >= 30) return 'text-success-medium';
    if (percentage >= 10) return 'text-success-low';
    return 'text-neutral';
  }

  /**
   * Get recommendation icon
   */
  getRecommendationIcon(recommendation: string): string {
    if (recommendation.includes('Significant')) return '🎯';
    if (recommendation.includes('Moderate')) return '💡';
    if (recommendation.includes('Some')) return 'ℹ️';
    return '✅';
  }

  /**
   * Calculate percentage of total operations
   */
  getOperationsPercentage(operations: number): number {
    if (!this.usageSummary?.totals.total_operations) return 0;
    return (operations / this.usageSummary.totals.total_operations) * 100;
  }

  /**
   * Calculate percentage of total cost
   */
  getCostPercentage(cost: number): number {
    if (!this.usageSummary?.totals.total_cost) return 0;
    return (cost / this.usageSummary.totals.total_cost) * 100;
  }

  /**
   * Navigate back to contract workbench
   */
  goBack(): void {
    this.router.navigate(['/']);
  }

  /**
   * Navigate to preferences
   */
  goToPreferences(): void {
    this.router.navigate(['/preferences']);
  }

  /**
   * Get operation display name
   */
  getOperationDisplayName(operation: string): string {
    const nameMap: { [key: string]: string } = {
      'sparql_generation': 'SPARQL Generation',
      'contract_comparison': 'Contract Comparison',
      'compliance_evaluation': 'Compliance Evaluation',
      'compliance_recommendation': 'Compliance Recommendation',
      'clause_comparison': 'Clause Comparison',
      'clause_suggestion': 'Clause Suggestion',
      'query_planning': 'Query Planning',
      'rag_embedding': 'RAG Embedding',
      'generic_completion': 'Generic Completion',
      'word_addin_evaluation': 'Word Add-in Evaluation',
      'word_addin_comparison': 'Word Add-in Comparison'
    };
    return nameMap[operation] || operation;
  }

  /**
   * Get operation icon
   */
  getOperationIcon(operation: string): string {
    const icons: { [key: string]: string } = {
      'sparql_generation': '🔍',
      'contract_comparison': '📄',
      'compliance_evaluation': '✅',
      'compliance_recommendation': '💡',
      'clause_comparison': '📋',
      'clause_suggestion': '🎯',
      'query_planning': '🗺️',
      'rag_embedding': '🔢',
      'generic_completion': '🤖',
      'word_addin_evaluation': '📝',
      'word_addin_comparison': '🔄'
    };
    return icons[operation] || '📊';
  }

  /**
   * Get operation description for tooltip
   */
  getOperationDescription(operation: string): string {
    const descriptions: { [key: string]: string } = {
      'sparql_generation': 'Converts natural language questions into SPARQL queries to search the contract database',
      'contract_comparison': 'Compares multiple contracts to identify differences, similarities, and key provisions',
      'compliance_evaluation': 'Evaluates contract compliance against defined rules and regulatory requirements',
      'compliance_recommendation': 'Generates recommendations and suggested fixes for compliance issues found in contracts',
      'clause_comparison': 'Compares contract clauses against standard clause library to assess alignment',
      'clause_suggestion': 'Suggests improved clause wording and alternatives from the standard clause library',
      'query_planning': 'Plans and executes complex multi-step contract queries and analyses',
      'rag_embedding': 'Creates vector embeddings for semantic document search and retrieval operations',
      'generic_completion': 'General purpose AI text generation for various contract-related tasks',
      'word_addin_evaluation': 'Evaluates and analyzes contracts directly within Microsoft Word Add-in',
      'word_addin_comparison': 'Compares document versions and analyzes tracked changes within Word Add-in'
    };
    return descriptions[operation] || 'AI operation for contract analysis';
  }

  /**
   * Get success rate color class
   */
  getSuccessRateClass(rate: number): string {
    if (rate >= 99) return 'success-excellent';
    if (rate >= 95) return 'success-good';
    if (rate >= 90) return 'success-fair';
    if (rate >= 80) return 'success-poor';
    return 'success-critical';
  }

  /**
   * Get efficiency rating class
   */
  getEfficiencyClass(rating: string): string {
    if (rating === 'excellent') return 'text-success-high';
    if (rating === 'good') return 'text-success-medium';
    if (rating === 'fair') return 'text-success-low';
    return 'text-neutral';
  }
}
