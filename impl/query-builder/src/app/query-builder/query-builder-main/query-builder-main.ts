import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

// Material Modules
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

// Components
import { TemplateSelectorComponent } from '../template-selector/template-selector';
import { EntitySelectorComponent } from '../entity-selector/entity-selector';
import { QueryPreviewComponent } from '../query-preview/query-preview';

// Models and Services
import { QueryTemplate, StructuredQuery, Entity, ClauseType, QueryResult, ValidationResult } from '../models/query.models';
import { QueryBuilderService } from '../services/query-builder.service';
import { MockDataService } from '../services/mock-data.service';
import { EntityService } from '../services/entity.service';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-query-builder-main',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatToolbarModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatChipsModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TemplateSelectorComponent,
    EntitySelectorComponent,
    QueryPreviewComponent
  ],
  templateUrl: './query-builder-main.html',
  styleUrls: ['./query-builder-main.scss'],
  providers: [QueryBuilderService]
})
export class QueryBuilderMainComponent implements OnInit, OnDestroy {
  private destroy = new Subject<void>();
  
  currentStep = 0;
  selectedTemplate: QueryTemplate | null = null;
  currentQuery: StructuredQuery | null = null;
  queryForm: FormGroup;
  clauseTypes: ClauseType[] = [];
  isExecuting = false;
  queryResult: QueryResult | null = null;
  validationResult: ValidationResult = { valid: false, errors: [], warnings: [] };

  constructor(
    private fb: FormBuilder,
    private queryService: QueryBuilderService,
    private mockData: MockDataService,
    private apiService: ApiService
  ) {
    this.queryForm = this.createQueryForm();
    // Load clause types from API
    this.loadClauseTypes();
  }

  ngOnInit(): void {
    this.queryService.currentQuery$
      .pipe(takeUntil(this.destroy))
      .subscribe(query => {
        this.currentQuery = query;
        if (query) {
          this.validationResult = this.queryService.validateQuery(query);
        }
      });
    
    this.queryService.selectedTemplate$
      .pipe(takeUntil(this.destroy))
      .subscribe(template => {
        this.selectedTemplate = template;
        if (template) {
          this.setupFormForTemplate(template);
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy.next();
    this.destroy.complete();
  }

  createQueryForm(): FormGroup {
    return this.fb.group({
      clauseType: [''],
      contractingParty: [null],
      contractorParties: [[]],
      governingLaw: [null],
      contractType: [null]
    });
  }

  setupFormForTemplate(template: QueryTemplate): void {
    this.queryForm.reset();
    
    switch (template.id) {
      case 'COMPARE_CLAUSES':
        this.queryForm.get('clauseType')?.setValidators([Validators.required]);
        this.queryForm.get('contractorParties')?.setValidators([Validators.required]);
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

  executeQuery(): void {
    if (!this.currentQuery || !this.validationResult.valid) {
      return;
    }
    
    this.isExecuting = true;
    this.queryResult = null;
    
    this.queryService.executeQuery(this.currentQuery)
      .pipe(takeUntil(this.destroy))
      .subscribe({
        next: (result) => {
          this.queryResult = result;
          this.isExecuting = false;
          this.currentStep = 3;
        },
        error: (error) => {
          console.error('Query execution error:', error);
          this.isExecuting = false;
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

  private loadClauseTypes(): void {
    this.apiService.getClauseTypes()
      .pipe(takeUntil(this.destroy))
      .subscribe(
        clauseTypes => {
          this.clauseTypes = clauseTypes;
          console.log('Loaded clause types from API:', clauseTypes);
        },
        error => {
          console.error('Failed to load clause types, using mock data:', error);
          // Fallback to mock data
          this.clauseTypes = this.mockData.getClauseTypes();
        }
      );
  }
}
