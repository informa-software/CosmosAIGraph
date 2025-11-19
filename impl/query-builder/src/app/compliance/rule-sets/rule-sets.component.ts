import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RuleSetService } from '../services/rule-set.service';
import { ComplianceService } from '../services/compliance.service';
import { RuleSetEditorComponent } from '../rule-set-editor/rule-set-editor.component';
import {
  RuleSet,
  RuleSetWithRuleCount,
  CloneRuleSetRequest,
  ComplianceRule
} from '../models/compliance.models';

@Component({
  selector: 'app-rule-sets',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RuleSetEditorComponent],
  templateUrl: './rule-sets.component.html',
  styleUrls: ['./rule-sets.component.scss']
})
export class RuleSetsComponent implements OnInit {
  ruleSets: RuleSetWithRuleCount[] = [];
  filteredRuleSets: RuleSetWithRuleCount[] = [];
  loading = false;
  error: string | null = null;

  // Filters
  filterActiveOnly = true;
  searchText = '';

  // Selection
  selectedRuleSetIds = new Set<string>();

  // Editor state
  showEditor = false;
  editingRuleSet: RuleSet | null = null;
  editorMode: 'create' | 'edit' = 'create';

  constructor(
    private ruleSetService: RuleSetService,
    private complianceService: ComplianceService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadRuleSets();
  }

  // ============================================================================
  // DATA LOADING
  // ============================================================================

  /**
   * Load all rule sets with counts
   */
  loadRuleSets(): void {
    this.loading = true;
    this.error = null;

    this.ruleSetService.getRuleSetsWithCounts(!this.filterActiveOnly).subscribe({
      next: (ruleSets) => {
        this.ruleSets = ruleSets;
        this.applyFilters();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading rule sets:', error);
        this.error = 'Failed to load rule sets. Please try again.';
        this.loading = false;
      }
    });
  }

  /**
   * Refresh the list
   */
  refresh(): void {
    this.loadRuleSets();
  }

  // ============================================================================
  // FILTERING AND SEARCH
  // ============================================================================

  /**
   * Apply filters to the rule sets list
   */
  applyFilters(): void {
    let filtered = [...this.ruleSets];

    // Apply search filter
    if (this.searchText.trim()) {
      const search = this.searchText.toLowerCase();
      filtered = filtered.filter(rs =>
        rs.name.toLowerCase().includes(search) ||
        (rs.description && rs.description.toLowerCase().includes(search)) ||
        rs.suggested_contract_types.some(type => type.toLowerCase().includes(search))
      );
    }

    this.filteredRuleSets = filtered;
  }

  /**
   * Handle filter change
   */
  onFilterChange(): void {
    this.loadRuleSets();
  }

  /**
   * Handle search change
   */
  onSearchChange(): void {
    this.applyFilters();
  }

  // ============================================================================
  // RULE SET ACTIONS
  // ============================================================================

  /**
   * Open editor to create a new rule set
   */
  createRuleSet(): void {
    this.editingRuleSet = null;
    this.editorMode = 'create';
    this.showEditor = true;
  }

  /**
   * Open editor to edit an existing rule set
   */
  editRuleSet(ruleSet: RuleSet): void {
    this.editingRuleSet = ruleSet;
    this.editorMode = 'edit';
    this.showEditor = true;
  }

  /**
   * Clone a rule set
   */
  async cloneRuleSet(ruleSet: RuleSet): Promise<void> {
    const newName = prompt(`Enter name for cloned rule set:`, `${ruleSet.name} (Copy)`);
    if (!newName) return;

    const cloneRules = confirm('Do you want to copy the rules from the original rule set?');

    const request: CloneRuleSetRequest = {
      new_name: newName,
      clone_rules: cloneRules
    };

    try {
      await this.ruleSetService.cloneRuleSet(ruleSet.id, request).toPromise();
      alert('Rule set cloned successfully!');
      this.loadRuleSets();
    } catch (error) {
      console.error('Error cloning rule set:', error);
      alert('Failed to clone rule set. Please try again.');
    }
  }

  /**
   * Delete a rule set
   */
  async deleteRuleSet(ruleSet: RuleSet): Promise<void> {
    const confirmed = confirm(
      `Are you sure you want to delete the rule set "${ruleSet.name}"?\n\n` +
      `This will NOT delete the individual rules, only the rule set collection.`
    );

    if (!confirmed) return;

    try {
      await this.ruleSetService.deleteRuleSet(ruleSet.id).toPromise();
      alert('Rule set deleted successfully!');
      this.loadRuleSets();
    } catch (error) {
      console.error('Error deleting rule set:', error);
      alert('Failed to delete rule set. Please try again.');
    }
  }

  /**
   * Toggle rule set active status
   */
  async toggleActive(ruleSet: RuleSet): Promise<void> {
    try {
      await this.ruleSetService.updateRuleSet(ruleSet.id, {
        is_active: !ruleSet.is_active
      }).toPromise();
      this.loadRuleSets();
    } catch (error) {
      console.error('Error toggling rule set status:', error);
      alert('Failed to update rule set status.');
    }
  }

  /**
   * Manage rules in a rule set
   */
  /**
   * View rules in this rule set
   */
  viewRules(ruleSet: RuleSet): void {
    this.router.navigate(['/compliance/rules'], {
      queryParams: { rule_set_id: ruleSet.id }
    });
  }

  manageRules(ruleSet: RuleSet): void {
    // TODO: Open rule management dialog
    alert(`Rule management for "${ruleSet.name}" will be implemented in the next phase.`);
  }

  // ============================================================================
  // SELECTION
  // ============================================================================

  /**
   * Toggle selection of a rule set
   */
  toggleSelection(ruleSetId: string): void {
    if (this.selectedRuleSetIds.has(ruleSetId)) {
      this.selectedRuleSetIds.delete(ruleSetId);
    } else {
      this.selectedRuleSetIds.add(ruleSetId);
    }
  }

  /**
   * Select all visible rule sets
   */
  selectAll(): void {
    this.filteredRuleSets.forEach(rs => this.selectedRuleSetIds.add(rs.id));
  }

  /**
   * Clear all selections
   */
  clearSelection(): void {
    this.selectedRuleSetIds.clear();
  }

  /**
   * Check if a rule set is selected
   */
  isSelected(ruleSetId: string): boolean {
    return this.selectedRuleSetIds.has(ruleSetId);
  }

  // ============================================================================
  // NAVIGATION
  // ============================================================================

  /**
   * Navigate to compliance dashboard
   */
  viewDashboard(): void {
    this.router.navigate(['/compliance/dashboard']);
  }

  // ============================================================================
  // EDITOR CALLBACKS
  // ============================================================================

  /**
   * Handle editor save
   */
  onEditorSave(): void {
    this.showEditor = false;
    this.loadRuleSets();
  }

  /**
   * Handle editor cancel
   */
  onEditorCancel(): void {
    this.showEditor = false;
    this.editingRuleSet = null;
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Format suggested contract types for display
   */
  formatContractTypes(types: string[]): string {
    if (!types || types.length === 0) return 'Any';
    return types.join(', ');
  }

  /**
   * Get badge class for rule count
   */
  getRuleCountBadgeClass(count: number): string {
    if (count === 0) return 'badge-secondary';
    if (count < 5) return 'badge-warning';
    return 'badge-success';
  }

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }
}
