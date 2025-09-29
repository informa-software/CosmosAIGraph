import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { 
  QueryTemplate, 
  StructuredQuery, 
  Entity, 
  ClauseType,
  QueryResult,
  ValidationResult 
} from '../../models/query.models';
import { QueryBuilderService } from '../../services/query-builder.service';
import { MockDataService } from '../../services/mock-data.service';

@Component({
  selector: 'app-query-builder-main',
  templateUrl: './query-builder-main.component.html',
  styleUrls: ['./query-builder-main.component.scss']
})
export class QueryBuilderMainComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  // Stepper control
  currentStep = 0;
  
  // Template selection
  selectedTemplate: QueryTemplate | null = null;
  
  // Query state
  currentQuery: StructuredQuery | null = null;
  queryForm: FormGroup;
  
  // Available options
  clauseTypes: ClauseType[] = [];
  
  // Query execution
  isExecuting = false;
  queryResult: QueryResult | null = null;
  
  // Validation
  validationResult: ValidationResult = { valid: false, errors: [], warnings: [] };

  constructor(
    private fb: FormBuilder,
    private queryService: QueryBuilderService,
    private mockData: MockDataService
  ) {
    this.queryForm = this.createQueryForm();
    this.clauseTypes = this.mockData.getClauseTypes();
  }

  ngOnInit(): void {
    // Subscribe to query changes
    this.queryService.currentQuery$
      .pipe(takeUntil(this.destroy$))
      .subscribe(query => {
        this.currentQuery = query;
        if (query) {
          this.validationResult = this.queryService.validateQuery(query);
        }
      });
    
    // Subscribe to template changes
    this.queryService.selectedTemplate$
      .pipe(takeUntil(this.destroy$))
      .subscribe(template => {
        this.selectedTemplate = template;
        if (template) {
          this.setupFormForTemplate(template);
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  createQueryForm(): FormGroup {
    return this.fb.group({
      clauseType: [''],
      contractingParty: [null],
      contractorParties: [[]],
      governingLaw: [null],
      contractType: [null],
      contractId: [''],
      analysisType: ['full'],
      includeChunks: [false],
      dateRange: [null],
      valueRange: [null],
      contracts: [[]],
      comparisonAspects: [[]]
    });
  }

  setupFormForTemplate(template: QueryTemplate): void {
    // Reset form
    this.queryForm.reset();
    
    // Set validators based on template requirements
    switch (template.id) {
      case 'COMPARE_CLAUSES':
        this.queryForm.get('clauseType')?.setValidators([Validators.required]);
        this.queryForm.get('contractorParties')?.setValidators([Validators.required]);
        break;
        
      case 'ANALYZE_CONTRACT':
        // Either contractId OR both parties required
        break;
        
      case 'FIND_CONTRACTS':
        // All fields optional
        break;
        
      case 'COMPARE_CONTRACTS':
        this.queryForm.get('contracts')?.setValidators([Validators.required]);
        break;
    }
    
    this.queryForm.updateValueAndValidity();
  }

  onTemplateSelected(template: QueryTemplate): void {
    this.queryService.selectTemplate(template);
    this.currentStep = 1;
    this.queryResult = null;
  }

  onClauseTypeChange(clauseType: string): void {
    this.queryService.updateQuery('clauseType', clauseType);
  }

  onEntitySelected(field: string, entity: Entity | Entity[]): void {
    this.queryService.updateQuery(field, entity);
  }

  onContractorSelected(entity: Entity): void {
    const current = this.currentQuery?.filters['contractorParties'] || [];
    if (!current.includes(entity.normalizedName)) {
      const updated = [...current, entity];
      this.queryService.updateQuery('contractorParties', updated);
    }
  }

  removeContractor(entity: Entity): void {
    const current = this.currentQuery?.filters['contractorParties'] || [];
    const updated = current.filter((name: string) => name !== entity.normalizedName);
    this.queryService.updateQuery('contractorParties', updated.map(name => ({
      normalizedName: name,
      displayName: this.currentQuery?.displayNames[name] || name,
      type: 'contractor' as const,
      contractCount: 0
    })));
  }

  getSelectedContractors(): Entity[] {
    const contractorNames = this.currentQuery?.filters['contractorParties'] || [];
    return contractorNames.map((name: string) => ({
      normalizedName: name,
      displayName: this.currentQuery?.displayNames[name] || name,
      type: 'contractor' as const,
      contractCount: 0
    }));
  }

  executeQuery(): void {
    if (!this.currentQuery || !this.validationResult.valid) {
      return;
    }
    
    this.isExecuting = true;
    this.queryResult = null;
    
    this.queryService.executeQuery(this.currentQuery)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.queryResult = result;
          this.isExecuting = false;
          this.currentStep = 3;
        },
        error: (error) => {
          console.error('Query execution error:', error);
          this.isExecuting = false;
          // In production, show error in snackbar
        }
      });
  }

  resetQuery(): void {
    this.queryService.clearQuery();
    this.selectedTemplate = null;
    this.currentQuery = null;
    this.queryResult = null;
    this.queryForm.reset();
    this.currentStep = 0;
  }

  goToStep(step: number): void {
    this.currentStep = step;
  }

  canProceedToReview(): boolean {
    return this.validationResult.valid && !this.isExecuting;
  }

  getStepLabel(step: number): string {
    switch (step) {
      case 0: return 'Select Template';
      case 1: return 'Configure Query';
      case 2: return 'Review & Execute';
      case 3: return 'View Results';
      default: return '';
    }
  }

  getStepIcon(step: number): string {
    switch (step) {
      case 0: return 'category';
      case 1: return 'tune';
      case 2: return 'preview';
      case 3: return 'assessment';
      default: return 'circle';
    }
  }
}