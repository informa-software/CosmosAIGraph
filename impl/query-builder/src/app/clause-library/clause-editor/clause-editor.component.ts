import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { QuillModule, QuillEditorComponent } from 'ngx-quill';
import Quill from 'quill';
import { ClauseLibraryService, Clause, Category, ClauseVariable } from '../../shared/services/clause-library.service';
import { ToastService } from '../../shared/services/toast.service';

@Component({
  selector: 'app-clause-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, QuillModule],
  templateUrl: './clause-editor.component.html',
  styleUrls: ['./clause-editor.component.scss']
})
export class ClauseEditorComponent implements OnInit {
  // Quill Editor Reference
  @ViewChild('quillEditor', { static: false }) quillEditor?: QuillEditorComponent;

  // Mode
  isEditMode = false;
  clauseId: string | null = null;

  // Data
  categories: Category[] = [];
  systemVariables: ClauseVariable[] = [];

  // Form Data
  clauseForm = {
    name: '',
    description: '',
    category_id: '',
    status: 'draft' as 'active' | 'draft' | 'archived',
    content_html: '',
    content_plain_text: '',
    variables: [] as ClauseVariable[],
    tags: [] as string[],
    contract_types: [] as string[],
    jurisdictions: [] as string[],
    risk_level: 'medium' as 'low' | 'medium' | 'high',
    complexity: 'medium' as 'low' | 'medium' | 'high'
  };

  // Temporary input fields for arrays
  newTag = '';
  newContractType = '';
  newJurisdiction = '';

  // Variable form
  showVariableForm = false;
  variableForm = {
    name: '',
    type: 'custom' as 'system' | 'custom',
    default_value: '',
    description: ''
  };
  editingVariableIndex: number | null = null;

  // UI State
  isLoading = false;
  isSaving = false;
  activeTab: 'basic' | 'content' | 'metadata' | 'variables' = 'basic';

  // Options
  statusOptions = [
    { value: 'draft', label: 'Draft' },
    { value: 'active', label: 'Active' },
    { value: 'archived', label: 'Archived' }
  ];

  riskLevelOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' }
  ];

  complexityOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' }
  ];

  // Quill Editor Configuration
  quillModules = {
    toolbar: [
      ['bold', 'italic', 'underline'],        // Basic formatting
      [{ 'header': [1, 2, 3, false] }],       // Headers
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],  // Lists
      [{ 'indent': '-1'}, { 'indent': '+1' }],  // Indentation
      ['link'],                                // Links
      ['clean']                                // Remove formatting
    ]
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private clauseLibraryService: ClauseLibraryService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    // Load categories and system variables
    this.loadCategories();
    this.loadSystemVariables();

    // Check if editing existing clause
    const clauseId = this.route.snapshot.paramMap.get('id');
    if (clauseId) {
      this.isEditMode = true;
      this.clauseId = clauseId;
      this.loadClause(clauseId);
    }
  }

  /**
   * Load categories
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
   * Load system variables
   */
  loadSystemVariables(): void {
    this.clauseLibraryService.getSystemVariables().subscribe({
      next: (response) => {
        this.systemVariables = response.variables;
      },
      error: (error) => {
        console.error('Error loading system variables:', error);
      }
    });
  }

  /**
   * Load existing clause for editing
   */
  loadClause(clauseId: string): void {
    this.isLoading = true;

    this.clauseLibraryService.getClause(clauseId).subscribe({
      next: (clause) => {
        this.clauseForm = {
          name: clause.name,
          description: clause.description,
          category_id: clause.category_id,
          status: clause.status,
          content_html: clause.content.html,
          content_plain_text: clause.content.plain_text,
          variables: [...clause.variables],
          tags: [...clause.metadata.tags],
          contract_types: [...clause.metadata.contract_types],
          jurisdictions: [...clause.metadata.jurisdictions],
          risk_level: clause.metadata.risk_level,
          complexity: clause.metadata.complexity
        };
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading clause:', error);
        this.toastService.error('Load Failed', 'Failed to load clause');
        this.isLoading = false;
        this.goBack();
      }
    });
  }

  /**
   * Switch active tab
   */
  setActiveTab(tab: 'basic' | 'content' | 'metadata' | 'variables'): void {
    this.activeTab = tab;
  }

  /**
   * Save clause
   */
  saveClause(): void {
    // Validation
    if (!this.clauseForm.name.trim()) {
      this.toastService.error('Validation Error', 'Clause name is required');
      return;
    }

    if (!this.clauseForm.category_id) {
      this.toastService.error('Validation Error', 'Please select a category');
      return;
    }

    if (!this.clauseForm.content_html.trim() && !this.clauseForm.content_plain_text.trim()) {
      this.toastService.error('Validation Error', 'Clause content is required');
      return;
    }

    // Auto-generate plain text if not provided
    if (!this.clauseForm.content_plain_text.trim() && this.clauseForm.content_html.trim()) {
      this.clauseForm.content_plain_text = this.stripHtml(this.clauseForm.content_html);
    }

    // Auto-generate HTML if not provided
    if (!this.clauseForm.content_html.trim() && this.clauseForm.content_plain_text.trim()) {
      this.clauseForm.content_html = `<p>${this.clauseForm.content_plain_text.replace(/\n/g, '</p><p>')}</p>`;
    }

    this.isSaving = true;

    if (this.isEditMode && this.clauseId) {
      // Update existing clause
      this.updateClause();
    } else {
      // Create new clause
      this.createClause();
    }
  }

  /**
   * Create new clause
   */
  createClause(): void {
    const clauseData = this.buildClauseData();

    this.clauseLibraryService.createClause(clauseData).subscribe({
      next: (response) => {
        this.toastService.success('Success', 'Clause created successfully');
        this.isSaving = false;
        this.router.navigate(['/clause-library/view', response.clause_id]);
      },
      error: (error) => {
        console.error('Error creating clause:', error);
        this.toastService.error('Save Failed', 'Failed to create clause');
        this.isSaving = false;
      }
    });
  }

  /**
   * Update existing clause
   */
  updateClause(): void {
    const clauseData = this.buildClauseData();

    this.clauseLibraryService.updateClause(this.clauseId!, clauseData).subscribe({
      next: (response) => {
        this.toastService.success('Success', 'Clause updated successfully');
        this.isSaving = false;
        this.router.navigate(['/clause-library/view', this.clauseId]);
      },
      error: (error) => {
        console.error('Error updating clause:', error);
        this.toastService.error('Save Failed', 'Failed to update clause');
        this.isSaving = false;
      }
    });
  }

  /**
   * Build clause data object for API
   */
  buildClauseData(): any {
    return {
      name: this.clauseForm.name.trim(),
      description: this.clauseForm.description.trim(),
      category_id: this.clauseForm.category_id,
      status: this.clauseForm.status,
      content: {
        html: this.clauseForm.content_html,
        plain_text: this.clauseForm.content_plain_text
      },
      variables: this.clauseForm.variables,
      metadata: {
        tags: this.clauseForm.tags,
        contract_types: this.clauseForm.contract_types,
        jurisdictions: this.clauseForm.jurisdictions,
        risk_level: this.clauseForm.risk_level,
        complexity: this.clauseForm.complexity
      }
    };
  }

  /**
   * Cancel and go back
   */
  cancel(): void {
    if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
      this.goBack();
    }
  }

  /**
   * Navigate back
   */
  goBack(): void {
    if (this.isEditMode && this.clauseId) {
      this.router.navigate(['/clause-library/view', this.clauseId]);
    } else {
      this.router.navigate(['/clause-library']);
    }
  }

  // ========== Tag Management ==========

  addTag(): void {
    const tag = this.newTag.trim().toLowerCase();
    if (tag && !this.clauseForm.tags.includes(tag)) {
      this.clauseForm.tags.push(tag);
      this.newTag = '';
    }
  }

  removeTag(tag: string): void {
    this.clauseForm.tags = this.clauseForm.tags.filter(t => t !== tag);
  }

  // ========== Contract Type Management ==========

  addContractType(): void {
    const type = this.newContractType.trim().toUpperCase();
    if (type && !this.clauseForm.contract_types.includes(type)) {
      this.clauseForm.contract_types.push(type);
      this.newContractType = '';
    }
  }

  removeContractType(type: string): void {
    this.clauseForm.contract_types = this.clauseForm.contract_types.filter(t => t !== type);
  }

  // ========== Jurisdiction Management ==========

  addJurisdiction(): void {
    const jurisdiction = this.newJurisdiction.trim();
    if (jurisdiction && !this.clauseForm.jurisdictions.includes(jurisdiction)) {
      this.clauseForm.jurisdictions.push(jurisdiction);
      this.newJurisdiction = '';
    }
  }

  removeJurisdiction(jurisdiction: string): void {
    this.clauseForm.jurisdictions = this.clauseForm.jurisdictions.filter(j => j !== jurisdiction);
  }

  // ========== Variable Management ==========

  openVariableForm(): void {
    this.showVariableForm = true;
    this.editingVariableIndex = null;
    this.resetVariableForm();
  }

  editVariable(index: number): void {
    const variable = this.clauseForm.variables[index];
    this.variableForm = { ...variable };
    this.editingVariableIndex = index;
    this.showVariableForm = true;
  }

  saveVariable(): void {
    // Validation
    if (!this.variableForm.name.trim()) {
      this.toastService.error('Validation Error', 'Variable name is required');
      return;
    }

    const variable: ClauseVariable = {
      name: this.variableForm.name.trim().toUpperCase(),
      type: this.variableForm.type,
      default_value: this.variableForm.default_value.trim(),
      description: this.variableForm.description.trim()
    };

    if (this.editingVariableIndex !== null) {
      // Update existing variable
      this.clauseForm.variables[this.editingVariableIndex] = variable;
    } else {
      // Add new variable
      if (this.clauseForm.variables.some(v => v.name === variable.name)) {
        this.toastService.error('Validation Error', 'Variable with this name already exists');
        return;
      }
      this.clauseForm.variables.push(variable);
    }

    this.closeVariableForm();
  }

  deleteVariable(index: number): void {
    if (confirm('Are you sure you want to delete this variable?')) {
      this.clauseForm.variables.splice(index, 1);
    }
  }

  closeVariableForm(): void {
    this.showVariableForm = false;
    this.resetVariableForm();
    this.editingVariableIndex = null;
  }

  resetVariableForm(): void {
    this.variableForm = {
      name: '',
      type: 'custom',
      default_value: '',
      description: ''
    };
  }

  /**
   * Handle system variable selection
   */
  onSystemVariableSelected(variableName: string): void {
    const systemVar = this.systemVariables.find(v => v.name === variableName);
    if (systemVar) {
      this.variableForm = { ...systemVar };
    }
  }

  /**
   * Handle variable type change
   */
  onVariableTypeChange(): void {
    if (this.variableForm.type === 'system') {
      // Reset form when switching to system type
      this.variableForm.name = '';
      this.variableForm.default_value = '';
      this.variableForm.description = '';
    } else {
      // Reset form when switching to custom type
      this.variableForm.name = '';
      this.variableForm.default_value = '';
      this.variableForm.description = '';
    }
  }

  // ========== Utility Methods ==========

  /**
   * Strip HTML tags from content
   */
  stripHtml(html: string): string {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  }

  /**
   * Insert variable placeholder into content at cursor position
   */
  insertVariable(variableName: string): void {
    if (!this.quillEditor) {
      console.error('Quill editor not initialized');
      return;
    }

    const quill = this.quillEditor.quillEditor;
    if (!quill) {
      console.error('Quill instance not available');
      return;
    }

    // Get current cursor position
    const range = quill.getSelection();
    const cursorPosition = range ? range.index : quill.getLength();

    // Create the variable placeholder
    const placeholder = `{{${variableName}}}`;

    // Insert the placeholder at cursor position with code formatting
    quill.insertText(cursorPosition, placeholder, 'code', true);
    quill.insertText(cursorPosition + placeholder.length, ' '); // Add space after

    // Move cursor after the inserted text
    quill.setSelection(cursorPosition + placeholder.length + 1, 0);

    // Focus back on the editor
    quill.focus();
  }
}
