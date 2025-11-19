import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ClauseLibraryService, ClauseVariable } from '../../shared/services/clause-library.service';
import { ToastService } from '../../shared/services/toast.service';

interface VariableFormData {
  name: string;
  type: 'system' | 'custom';
  default_value: string;
  description: string;
}

@Component({
  selector: 'app-variable-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './variable-manager.html',
  styleUrl: './variable-manager.scss'
})
export class VariableManagerComponent implements OnInit {
  // Data
  systemVariables: ClauseVariable[] = [];
  customVariables: ClauseVariable[] = [];
  filteredVariables: ClauseVariable[] = [];

  // Filters
  searchQuery = '';
  selectedType: 'all' | 'system' | 'custom' = 'all';

  // UI State
  isLoading = false;
  showVariableForm = false;
  editingVariable: ClauseVariable | null = null;
  activeTab: 'system' | 'custom' | 'all' = 'all';

  // Form
  variableForm: VariableFormData = {
    name: '',
    type: 'custom',
    default_value: '',
    description: ''
  };

  constructor(
    private clauseLibraryService: ClauseLibraryService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadVariables();
  }

  /**
   * Load all variables
   */
  loadVariables(): void {
    this.isLoading = true;

    this.clauseLibraryService.getSystemVariables().subscribe({
      next: (response) => {
        // Separate system and custom variables
        const allVariables = response.variables || [];
        this.systemVariables = allVariables.filter(v => v.type === 'system');
        this.customVariables = allVariables.filter(v => v.type === 'custom');

        this.applyFilters();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading variables:', error);
        this.toastService.error('Error', 'Failed to load variables');
        this.isLoading = false;
      }
    });
  }

  /**
   * Apply search and type filters
   */
  applyFilters(): void {
    let variables: ClauseVariable[] = [];

    // Filter by tab/type
    switch (this.activeTab) {
      case 'system':
        variables = [...this.systemVariables];
        break;
      case 'custom':
        variables = [...this.customVariables];
        break;
      case 'all':
      default:
        variables = [...this.systemVariables, ...this.customVariables];
        break;
    }

    // Filter by search query
    if (this.searchQuery.trim()) {
      const query = this.searchQuery.toLowerCase();
      variables = variables.filter(v =>
        v.name.toLowerCase().includes(query) ||
        v.description.toLowerCase().includes(query) ||
        v.default_value.toLowerCase().includes(query)
      );
    }

    this.filteredVariables = variables;
  }

  /**
   * Handle search input
   */
  onSearch(): void {
    this.applyFilters();
  }

  /**
   * Switch active tab
   */
  setActiveTab(tab: 'system' | 'custom' | 'all'): void {
    this.activeTab = tab;
    this.applyFilters();
  }

  /**
   * Open variable form for creating new custom variable
   */
  openCreateForm(): void {
    this.editingVariable = null;
    this.variableForm = {
      name: '',
      type: 'custom',
      default_value: '',
      description: ''
    };
    this.showVariableForm = true;
  }

  /**
   * Open variable form for editing existing variable
   */
  editVariable(variable: ClauseVariable): void {
    if (variable.type === 'system') {
      this.toastService.warning('Not Allowed', 'System variables cannot be edited');
      return;
    }

    this.editingVariable = variable;
    this.variableForm = {
      name: variable.name,
      type: variable.type,
      default_value: variable.default_value,
      description: variable.description
    };
    this.showVariableForm = true;
  }

  /**
   * Close variable form
   */
  closeVariableForm(): void {
    this.showVariableForm = false;
    this.editingVariable = null;
    this.variableForm = {
      name: '',
      type: 'custom',
      default_value: '',
      description: ''
    };
  }

  /**
   * Save variable (create or update)
   */
  saveVariable(): void {
    // Validate
    if (!this.variableForm.name.trim()) {
      this.toastService.error('Validation Error', 'Variable name is required');
      return;
    }

    if (!this.variableForm.description.trim()) {
      this.toastService.error('Validation Error', 'Description is required');
      return;
    }

    // Validate name format (uppercase with underscores)
    const namePattern = /^[A-Z][A-Z0-9_]*$/;
    if (!namePattern.test(this.variableForm.name)) {
      this.toastService.error('Validation Error', 'Variable name must be uppercase with underscores (e.g., CONTRACT_DATE)');
      return;
    }

    if (this.editingVariable) {
      // Update existing variable
      this.updateVariable();
    } else {
      // Create new variable
      this.createVariable();
    }
  }

  /**
   * Create new custom variable
   */
  createVariable(): void {
    const request = {
      name: this.variableForm.name,
      default_value: this.variableForm.default_value,
      description: this.variableForm.description
    };

    // TODO: Implement create custom variable endpoint
    // For now, just show success message
    this.toastService.success('Created', `Variable "${request.name}" created successfully`);
    this.closeVariableForm();

    // Add to custom variables list locally
    this.customVariables.push({
      name: request.name,
      type: 'custom',
      default_value: request.default_value,
      description: request.description
    });
    this.applyFilters();
  }

  /**
   * Update existing custom variable
   */
  updateVariable(): void {
    if (!this.editingVariable) return;

    // TODO: Implement update custom variable endpoint
    // For now, just update locally
    const index = this.customVariables.findIndex(v => v.name === this.editingVariable!.name);
    if (index !== -1) {
      this.customVariables[index] = {
        name: this.variableForm.name,
        type: 'custom',
        default_value: this.variableForm.default_value,
        description: this.variableForm.description
      };
      this.applyFilters();
    }

    this.toastService.success('Updated', `Variable "${this.variableForm.name}" updated successfully`);
    this.closeVariableForm();
  }

  /**
   * Delete custom variable
   */
  deleteVariable(variable: ClauseVariable): void {
    if (variable.type === 'system') {
      this.toastService.warning('Not Allowed', 'System variables cannot be deleted');
      return;
    }

    if (!confirm(`Are you sure you want to delete variable "${variable.name}"?`)) {
      return;
    }

    // TODO: Implement delete custom variable endpoint
    // For now, just remove locally
    const index = this.customVariables.findIndex(v => v.name === variable.name);
    if (index !== -1) {
      this.customVariables.splice(index, 1);
      this.applyFilters();
      this.toastService.success('Deleted', `Variable "${variable.name}" deleted successfully`);
    }
  }

  /**
   * Get badge class for variable type
   */
  getTypeBadgeClass(type: string): string {
    return type === 'system' ? 'badge-system' : 'badge-custom';
  }

  /**
   * Get count of variables by tab
   */
  getTabCount(tab: 'system' | 'custom' | 'all'): number {
    switch (tab) {
      case 'system':
        return this.systemVariables.length;
      case 'custom':
        return this.customVariables.length;
      case 'all':
        return this.systemVariables.length + this.customVariables.length;
      default:
        return 0;
    }
  }
}
