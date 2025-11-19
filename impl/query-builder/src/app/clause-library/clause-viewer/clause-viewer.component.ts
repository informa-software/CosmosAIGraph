import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ClauseLibraryService, Clause } from '../../shared/services/clause-library.service';
import { ToastService } from '../../shared/services/toast.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-clause-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './clause-viewer.component.html',
  styleUrls: ['./clause-viewer.component.scss']
})
export class ClauseViewerComponent implements OnInit {
  // Data
  clause: Clause | null = null;
  versionHistory: Clause[] = [];

  // UI State
  isLoading = false;
  isLoadingVersions = false;
  activeTab: 'content' | 'metadata' | 'variables' | 'versions' | 'usage' = 'content';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private clauseLibraryService: ClauseLibraryService,
    private toastService: ToastService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    // Get clause ID from route
    const clauseId = this.route.snapshot.paramMap.get('id');
    if (clauseId) {
      this.loadClause(clauseId);
    } else {
      this.toastService.error('Error', 'No clause ID provided');
      this.goBack();
    }
  }

  /**
   * Load clause details
   */
  loadClause(clauseId: string): void {
    this.isLoading = true;

    this.clauseLibraryService.getClause(clauseId).subscribe({
      next: (clause) => {
        this.clause = clause;
        this.isLoading = false;

        // Load version history
        this.loadVersionHistory(clauseId);
      },
      error: (error) => {
        console.error('Error loading clause:', error);
        this.toastService.error('Load Failed', 'Failed to load clause details');
        this.isLoading = false;
        this.goBack();
      }
    });
  }

  /**
   * Load version history
   */
  loadVersionHistory(clauseId: string): void {
    this.isLoadingVersions = true;

    this.clauseLibraryService.getVersionHistory(clauseId).subscribe({
      next: (response) => {
        this.versionHistory = response.versions;
        this.isLoadingVersions = false;
      },
      error: (error) => {
        console.error('Error loading version history:', error);
        this.isLoadingVersions = false;
      }
    });
  }

  /**
   * Get sanitized HTML content
   */
  getSafeHtml(html: string): SafeHtml {
    return this.sanitizer.sanitize(1, html) || '';
  }

  /**
   * Switch active tab
   */
  setActiveTab(tab: 'content' | 'metadata' | 'variables' | 'versions' | 'usage'): void {
    this.activeTab = tab;
  }

  /**
   * Navigate back to clause list
   */
  goBack(): void {
    this.router.navigate(['/clause-library']);
  }

  /**
   * Navigate to edit page
   */
  editClause(): void {
    if (this.clause) {
      this.router.navigate(['/clause-library/edit', this.clause.id]);
    }
  }

  /**
   * Delete clause
   */
  deleteClause(): void {
    if (!this.clause) return;

    if (!confirm(`Are you sure you want to delete "${this.clause.name}"?`)) {
      return;
    }

    this.clauseLibraryService.deleteClause(this.clause.id).subscribe({
      next: (response) => {
        this.toastService.success('Deleted', response.message);
        this.goBack();
      },
      error: (error) => {
        console.error('Error deleting clause:', error);
        this.toastService.error('Delete Failed', 'Failed to delete clause');
      }
    });
  }

  /**
   * Create new version
   */
  createNewVersion(): void {
    if (!this.clause) return;

    const changeNotes = prompt('Enter change notes for the new version:');
    if (!changeNotes) return;

    this.clauseLibraryService.createVersion(
      this.clause.id,
      changeNotes
    ).subscribe({
      next: (newVersion) => {
        this.toastService.success('Version Created', `New version ${newVersion.version.version_label} created successfully`);
        // Navigate to the new version
        this.router.navigate(['/clause-library/view', newVersion.id]);
      },
      error: (error) => {
        console.error('Error creating version:', error);
        this.toastService.error('Failed', 'Failed to create new version');
      }
    });
  }

  /**
   * View specific version
   */
  viewVersion(versionId: string): void {
    this.router.navigate(['/clause-library/view', versionId]);
  }

  /**
   * Format date
   */
  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Get risk badge class
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
   * Get variable type badge class
   */
  getVariableTypeBadgeClass(type: string): string {
    return type === 'system' ? 'badge-var-system' : 'badge-var-custom';
  }
}
