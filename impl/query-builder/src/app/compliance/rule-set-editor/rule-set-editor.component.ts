import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RuleSetService } from '../services/rule-set.service';
import {
  RuleSet,
  RuleSetCreate,
  RuleSetUpdate
} from '../models/compliance.models';

@Component({
  selector: 'app-rule-set-editor',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './rule-set-editor.component.html',
  styleUrls: ['./rule-set-editor.component.scss']
})
export class RuleSetEditorComponent implements OnInit {
  @Input() ruleSet: RuleSet | null = null;
  @Input() mode: 'create' | 'edit' = 'create';
  @Output() save = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();

  // Form fields
  name = '';
  description = '';
  suggestedContractTypesInput = '';
  isActive = true;

  // UI state
  saving = false;
  error: string | null = null;

  // Common contract types for suggestions
  commonContractTypes = [
    'MSA',
    'NDA',
    'SOW',
    'Service Agreement',
    'Subscription',
    'Purchase Order',
    'Employment Agreement',
    'Consulting Agreement',
    'License Agreement',
    'Partnership Agreement'
  ];

  constructor(private ruleSetService: RuleSetService) {}

  ngOnInit(): void {
    if (this.ruleSet && this.mode === 'edit') {
      this.loadRuleSet();
    }
  }

  /**
   * Load existing rule set data into form
   */
  loadRuleSet(): void {
    if (!this.ruleSet) return;

    this.name = this.ruleSet.name;
    this.description = this.ruleSet.description || '';
    this.suggestedContractTypesInput = this.ruleSet.suggested_contract_types.join(', ');
    this.isActive = this.ruleSet.is_active;
  }

  /**
   * Parse suggested contract types from comma-separated input
   */
  parseSuggestedContractTypes(): string[] {
    if (!this.suggestedContractTypesInput.trim()) {
      return [];
    }

    return this.suggestedContractTypesInput
      .split(',')
      .map(type => type.trim())
      .filter(type => type.length > 0);
  }

  /**
   * Add a common contract type to the input
   */
  addContractType(type: string): void {
    const current = this.parseSuggestedContractTypes();
    if (!current.includes(type)) {
      current.push(type);
      this.suggestedContractTypesInput = current.join(', ');
    }
  }

  /**
   * Validate form
   */
  isValid(): boolean {
    if (!this.name.trim()) {
      this.error = 'Name is required';
      return false;
    }

    if (this.name.length > 200) {
      this.error = 'Name must be less than 200 characters';
      return false;
    }

    this.error = null;
    return true;
  }

  /**
   * Save rule set (create or update)
   */
  async onSave(): Promise<void> {
    if (!this.isValid()) {
      return;
    }

    this.saving = true;
    this.error = null;

    try {
      const suggestedContractTypes = this.parseSuggestedContractTypes();

      if (this.mode === 'create') {
        // Create new rule set
        const createData: RuleSetCreate = {
          name: this.name.trim(),
          description: this.description.trim() || null,
          suggested_contract_types: suggestedContractTypes,
          is_active: this.isActive,
          rule_ids: []
        };

        await this.ruleSetService.createRuleSet(createData).toPromise();
      } else {
        // Update existing rule set
        if (!this.ruleSet) {
          throw new Error('No rule set to update');
        }

        const updateData: RuleSetUpdate = {
          name: this.name.trim(),
          description: this.description.trim() || null,
          suggested_contract_types: suggestedContractTypes,
          is_active: this.isActive
        };

        await this.ruleSetService.updateRuleSet(this.ruleSet.id, updateData).toPromise();
      }

      this.saving = false;
      this.save.emit();
    } catch (error: any) {
      console.error('Error saving rule set:', error);
      this.error = error.error?.detail || 'Failed to save rule set. Please try again.';
      this.saving = false;
    }
  }

  /**
   * Cancel editing
   */
  onCancel(): void {
    this.cancel.emit();
  }

  /**
   * Get title based on mode
   */
  getTitle(): string {
    return this.mode === 'create' ? 'Create New Rule Set' : 'Edit Rule Set';
  }

  /**
   * Get save button text based on mode
   */
  getSaveButtonText(): string {
    if (this.saving) {
      return this.mode === 'create' ? 'Creating...' : 'Saving...';
    }
    return this.mode === 'create' ? 'Create Rule Set' : 'Save Changes';
  }
}
