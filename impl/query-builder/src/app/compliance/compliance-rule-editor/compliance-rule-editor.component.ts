import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  ComplianceRule,
  ComplianceRuleRequest,
  RuleSeverity,
  Category,
  RuleSet,
  PREDEFINED_CATEGORIES,
  SEVERITY_OPTIONS,
  getSeverityColor,
  formatDate
} from '../models/compliance.models';
import { ComplianceService } from '../services/compliance.service';
import { RuleSetService } from '../services/rule-set.service';
import { ToastService } from '../../shared/services/toast.service';

@Component({
  selector: 'app-compliance-rule-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './compliance-rule-editor.component.html',
  styleUrls: ['./compliance-rule-editor.component.scss']
})
export class ComplianceRuleEditorComponent implements OnInit {
  // Constants
  readonly SEVERITY_OPTIONS = SEVERITY_OPTIONS;
  readonly CATEGORIES = PREDEFINED_CATEGORIES;

  // State
  mode: 'create' | 'edit' = 'create';
  ruleId: string | null = null;
  loading: boolean = false;
  saving: boolean = false;
  categories: Category[] = [];
  ruleSets: RuleSet[] = [];
  selectedRuleSetIds: string[] = [];

  // Form model
  formData: ComplianceRuleRequest = {
    name: '',
    description: '',
    severity: 'medium',
    category: '',
    active: true,
    rule_set_ids: []
  };

  // Validation
  formErrors: {
    name?: string;
    description?: string;
    severity?: string;
    category?: string;
  } = {};

  // Original rule (for edit mode)
  originalRule: ComplianceRule | null = null;

  // Dropdown state
  ruleSetDropdownOpen: boolean = false;

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

    // Check if we're in edit mode
    this.route.params.subscribe(params => {
      const id = params['id'];
      if (id) {
        this.mode = 'edit';
        this.ruleId = id;
        this.loadRule(id);
      }
    });
  }

  /**
   * Load categories
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
   * Load available rule sets
   */
  loadRuleSets(): void {
    this.ruleSetService.getActiveRuleSets().subscribe({
      next: (response) => {
        this.ruleSets = response.rule_sets || [];
      },
      error: (error) => {
        console.error('Error loading rule sets:', error);
        this.toastService.error('Failed to load rule sets');
      }
    });
  }

  /**
   * Load existing rule for editing
   */
  loadRule(ruleId: string): void {
    this.loading = true;
    this.complianceService.getRule(ruleId).subscribe({
      next: (rule) => {
        if (rule) {
          this.originalRule = rule;
          this.formData = {
            name: rule.name,
            description: rule.description,
            severity: rule.severity,
            category: rule.category,
            active: rule.active,
            rule_set_ids: [...(rule.rule_set_ids || [])]
          };
          this.selectedRuleSetIds = [...(rule.rule_set_ids || [])];
        } else {
          this.toastService.error('Rule not found');
          this.goBack();
        }
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading rule:', error);
        this.toastService.error('Error loading rule');
        this.loading = false;
        this.goBack();
      }
    });
  }

  /**
   * Validate form
   */
  validateForm(): boolean {
    this.formErrors = {};
    let isValid = true;

    // Name validation
    if (!this.formData.name || this.formData.name.trim().length === 0) {
      this.formErrors.name = 'Rule name is required';
      isValid = false;
    } else if (this.formData.name.trim().length < 3) {
      this.formErrors.name = 'Rule name must be at least 3 characters';
      isValid = false;
    } else if (this.formData.name.trim().length > 200) {
      this.formErrors.name = 'Rule name must not exceed 200 characters';
      isValid = false;
    }

    // Description validation
    if (!this.formData.description || this.formData.description.trim().length === 0) {
      this.formErrors.description = 'Description is required';
      isValid = false;
    } else if (this.formData.description.trim().length < 10) {
      this.formErrors.description = 'Description must be at least 10 characters';
      isValid = false;
    } else if (this.formData.description.trim().length > 1000) {
      this.formErrors.description = 'Description must not exceed 1000 characters';
      isValid = false;
    }

    // Severity validation
    if (!this.formData.severity) {
      this.formErrors.severity = 'Severity is required';
      isValid = false;
    }

    // Category validation
    if (!this.formData.category || this.formData.category.trim().length === 0) {
      this.formErrors.category = 'Category is required';
      isValid = false;
    }

    return isValid;
  }

  /**
   * Save rule (create or update)
   */
  saveRule(): void {
    if (!this.validateForm()) {
      this.toastService.error('Please fix validation errors');
      return;
    }

    // Update formData with selected rule sets
    this.formData.rule_set_ids = this.selectedRuleSetIds;

    this.saving = true;

    if (this.mode === 'create') {
      this.createRule();
    } else {
      this.updateRule();
    }
  }

  /**
   * Create new rule
   */
  private createRule(): void {
    this.complianceService.createRule(this.formData).subscribe({
      next: (rule) => {
        if (rule) {
          this.toastService.success(`Rule "${rule.name}" created successfully`);
        } else {
          this.toastService.success('Rule created successfully');
        }
        this.router.navigate(['/compliance/rules']);
      },
      error: (error) => {
        console.error('Error creating rule:', error);
        const errorMsg = error.error?.detail || error.message || 'Failed to create rule';
        this.toastService.error('Error creating rule', errorMsg);
        this.saving = false;
      }
    });
  }

  /**
   * Update existing rule
   */
  private updateRule(): void {
    if (!this.ruleId) {
      this.toastService.error('Rule ID not found');
      this.saving = false;
      return;
    }

    // Only send changed fields
    const updates: Partial<ComplianceRuleRequest> = {};
    if (this.formData.name !== this.originalRule?.name) {
      updates.name = this.formData.name;
    }
    if (this.formData.description !== this.originalRule?.description) {
      updates.description = this.formData.description;
    }
    if (this.formData.severity !== this.originalRule?.severity) {
      updates.severity = this.formData.severity;
    }
    if (this.formData.category !== this.originalRule?.category) {
      updates.category = this.formData.category;
    }
    if (this.formData.active !== this.originalRule?.active) {
      updates.active = this.formData.active;
    }
    // Check if rule_set_ids changed
    const originalRuleSetIds = [...(this.originalRule?.rule_set_ids || [])];
    const newRuleSetIds = [...(this.formData.rule_set_ids || [])];
    if (JSON.stringify(originalRuleSetIds.sort()) !== JSON.stringify(newRuleSetIds.sort())) {
      updates.rule_set_ids = this.formData.rule_set_ids;
    }

    if (Object.keys(updates).length === 0) {
      this.toastService.info('No changes to save');
      this.saving = false;
      return;
    }

    this.complianceService.updateRule(this.ruleId, updates).subscribe({
      next: () => {
        this.toastService.success(`Rule "${this.formData.name}" updated successfully`);
        this.router.navigate(['/compliance/rules']);
      },
      error: (error) => {
        console.error('Error updating rule:', error);
        const errorMsg = error.error?.detail || error.message || 'Failed to update rule';
        this.toastService.error('Error updating rule', errorMsg);
        this.saving = false;
      }
    });
  }

  /**
   * Cancel and go back
   */
  cancel(): void {
    if (this.hasUnsavedChanges()) {
      if (confirm('You have unsaved changes. Are you sure you want to leave?')) {
        this.goBack();
      }
    } else {
      this.goBack();
    }
  }

  /**
   * Check if there are unsaved changes
   */
  hasUnsavedChanges(): boolean {
    if (this.mode === 'create') {
      return this.formData.name.trim().length > 0 ||
             this.formData.description.trim().length > 0;
    } else if (this.originalRule) {
      return this.formData.name !== this.originalRule.name ||
             this.formData.description !== this.originalRule.description ||
             this.formData.severity !== this.originalRule.severity ||
             this.formData.category !== this.originalRule.category ||
             this.formData.active !== this.originalRule.active;
    }
    return false;
  }

  /**
   * Navigate back to rules list
   */
  goBack(): void {
    this.router.navigate(['/compliance/rules']);
  }

  /**
   * Get category display name by name (category ID)
   */
  getCategoryName(categoryName: string): string {
    const category = this.categories.find(c => c.name === categoryName);
    return category ? category.display_name : categoryName;
  }

  /**
   * Get category description by name (category ID)
   */
  getCategoryDescription(categoryName: string): string {
    const category = this.categories.find(c => c.name === categoryName);
    return category ? category.description : '';
  }

  /**
   * Get severity color
   */
  getSeverityColor(severity: RuleSeverity): string {
    return getSeverityColor(severity);
  }

  /**
   * Format date string
   */
  formatDate(dateString: string): string {
    return formatDate(dateString);
  }

  /**
   * Get character count for text fields
   */
  getNameCharCount(): string {
    return `${this.formData.name.length} / 200`;
  }

  getDescriptionCharCount(): string {
    return `${this.formData.description.length} / 1000`;
  }

  /**
   * Toggle rule set dropdown
   */
  toggleRuleSetDropdown(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.ruleSetDropdownOpen = !this.ruleSetDropdownOpen;
  }

  /**
   * Close all dropdowns
   */
  closeAllDropdowns(): void {
    this.ruleSetDropdownOpen = false;
  }

  /**
   * Toggle rule set selection
   */
  toggleRuleSet(ruleSetId: string, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    const index = this.selectedRuleSetIds.indexOf(ruleSetId);
    if (index > -1) {
      this.selectedRuleSetIds.splice(index, 1);
    } else {
      this.selectedRuleSetIds.push(ruleSetId);
    }
  }

  /**
   * Check if rule set is selected
   */
  isRuleSetSelected(ruleSetId: string): boolean {
    return this.selectedRuleSetIds.includes(ruleSetId);
  }

  /**
   * Get rule set name by ID
   */
  getRuleSetName(ruleSetId: string): string {
    const ruleSet = this.ruleSets.find(rs => rs.id === ruleSetId);
    return ruleSet ? ruleSet.name : ruleSetId;
  }

  /**
   * Create new category (inline)
   */
  createNewCategory(): void {
    const categoryId = prompt('Enter category ID (lowercase with underscores):');
    if (!categoryId) return;

    const categoryName = prompt('Enter category name:');
    if (!categoryName) return;

    const categoryDescription = prompt('Enter category description:');
    if (!categoryDescription) return;

    this.complianceService.createCategory({
      id: categoryId.toLowerCase().replace(/\s+/g, '_'),
      name: categoryName,
      description: categoryDescription
    }).subscribe({
      next: () => {
        this.toastService.success('Category created successfully');
        this.loadCategories();
        this.formData.category = categoryId.toLowerCase().replace(/\s+/g, '_');
      },
      error: (error) => {
        console.error('Error creating category:', error);
        const errorMsg = error.error?.detail || error.message || 'Failed to create category';
        this.toastService.error('Error creating category', errorMsg);
      }
    });
  }
}
