import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { 
  StructuredQuery, 
  QueryTemplate, 
  ValidationResult, 
  Entity,
  QueryResult
} from '../models/query.models';
import { MockDataService } from './mock-data.service';

@Injectable({
  providedIn: 'root'
})
export class QueryBuilderService {
  private currentQuerySubject = new BehaviorSubject<StructuredQuery | null>(null);
  private selectedTemplateSubject = new BehaviorSubject<QueryTemplate | null>(null);
  
  public currentQuery$ = this.currentQuerySubject.asObservable();
  public selectedTemplate$ = this.selectedTemplateSubject.asObservable();

  constructor(private mockData: MockDataService) {}

  selectTemplate(template: QueryTemplate): void {
    this.selectedTemplateSubject.next(template);
    this.initializeQuery(template);
  }

  initializeQuery(template: QueryTemplate): void {
    const query: StructuredQuery = {
      template: template.id,
      operation: template.operation,
      target: template.target,
      filters: {},
      displayNames: {},
      options: {
        limit: 10,
        includeChunks: false,
        includeContext: true
      }
    };
    this.currentQuerySubject.next(query);
  }

  updateQuery(field: string, value: any): void {
    const current = this.currentQuerySubject.value;
    if (!current) return;

    const updated = { ...current };
    
    // Handle entity fields specially
    if (value && typeof value === 'object' && 'normalizedName' in value) {
      updated.filters[field] = value.normalizedName;
      updated.displayNames[value.normalizedName] = value.displayName;
    } else if (Array.isArray(value)) {
      // Handle arrays of entities
      const normalized: string[] = [];
      value.forEach((item: any) => {
        if (item && typeof item === 'object' && 'normalizedName' in item) {
          normalized.push(item.normalizedName);
          updated.displayNames[item.normalizedName] = item.displayName;
        } else {
          normalized.push(item);
        }
      });
      updated.filters[field] = normalized;
    } else {
      updated.filters[field] = value;
    }
    
    this.currentQuerySubject.next(updated);
  }

  toNaturalLanguage(query: StructuredQuery | null): string {
    if (!query) return '';
    
    const parts: string[] = [];
    
    switch (query.template) {
      case 'COMPARE_CLAUSES':
        parts.push('Compare');
        if (query.filters['clauseType']) {
          parts.push(query.filters['clauseType']);
        }
        parts.push('clauses');
        
        if (query.filters['contractingParty']) {
          const display = query.displayNames[query.filters['contractingParty']] || query.filters['contractingParty'];
          parts.push(`in contracts with ${display}`);
        }
        
        if (query.filters['contractorParties']?.length) {
          const contractors = query.filters['contractorParties']
            .map((c: string) => query.displayNames[c] || c)
            .join(' and ');
          parts.push(`between ${contractors}`);
        }
        break;
        
      case 'FIND_CONTRACTS':
        parts.push('Find contracts');
        
        const filters: string[] = [];
        if (query.filters['contractingParty']) {
          const display = query.displayNames[query.filters['contractingParty']] || query.filters['contractingParty'];
          filters.push(`with contracting party ${display}`);
        }
        if (query.filters['contractorParty']) {
          const display = query.displayNames[query.filters['contractorParty']] || query.filters['contractorParty'];
          filters.push(`with contractor ${display}`);
        }
        if (query.filters['governingLaw']) {
          const display = query.displayNames[query.filters['governingLaw']] || query.filters['governingLaw'];
          filters.push(`governed by ${display} law`);
        }
        if (query.filters['contractType']) {
          const display = query.displayNames[query.filters['contractType']] || query.filters['contractType'];
          filters.push(`of type ${display}`);
        }
        
        if (filters.length > 0) {
          parts.push(filters.join(' and '));
        }
        break;
        
      case 'ANALYZE_CONTRACT':
        parts.push('Analyze contract');
        if (query.filters['contractId']) {
          parts.push(query.filters['contractId']);
        } else if (query.filters['contractingParty'] && query.filters['contractorParty']) {
          const contracting = query.displayNames[query.filters['contractingParty']] || query.filters['contractingParty'];
          const contractor = query.displayNames[query.filters['contractorParty']] || query.filters['contractorParty'];
          parts.push(`between ${contracting} and ${contractor}`);
        }
        
        if (query.filters['analysisType']) {
          parts.push(`(${query.filters['analysisType']} analysis)`);
        }
        break;
        
      case 'COMPARE_CONTRACTS':
        parts.push('Compare contracts');
        if (query.filters['contracts']?.length) {
          parts.push(`(${query.filters['contracts'].length} contracts selected)`);
        }
        
        if (query.filters['comparisonAspects']?.length) {
          const aspects = query.filters['comparisonAspects'].join(', ');
          parts.push(`focusing on ${aspects}`);
        }
        break;
    }
    
    return parts.join(' ') || 'Build your query...';
  }

  validateQuery(query: StructuredQuery | null): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    
    if (!query) {
      return { valid: false, errors: ['No query defined'], warnings: [] };
    }
    
    const template = this.mockData.getTemplates().find(t => t.id === query.template);
    if (!template) {
      return { valid: false, errors: ['Invalid template'], warnings: [] };
    }
    
    // Check required fields
    template.requiredFields.forEach(field => {
      if (!query.filters[field] || 
          (Array.isArray(query.filters[field]) && query.filters[field].length === 0)) {
        errors.push(`${field} is required`);
      }
    });
    
    // Template-specific validation
    switch (query.template) {
      case 'COMPARE_CLAUSES':
        if (query.filters['contractorParties'] && 
            Array.isArray(query.filters['contractorParties']) && 
            query.filters['contractorParties'].length < 2) {
          errors.push('At least 2 contractors required for comparison');
        }
        break;
        
      case 'COMPARE_CONTRACTS':
        if (query.filters['contracts'] && 
            Array.isArray(query.filters['contracts']) && 
            query.filters['contracts'].length < 2) {
          errors.push('At least 2 contracts required for comparison');
        }
        break;
        
      case 'FIND_CONTRACTS':
        // At least one filter should be specified
        const hasFilter = ['contractingParty', 'contractorParty', 'governingLaw', 'contractType']
          .some(field => query.filters[field]);
        if (!hasFilter) {
          warnings.push('No filters specified - this may return many results');
        }
        break;
    }
    
    return { 
      valid: errors.length === 0, 
      errors, 
      warnings 
    };
  }

  executeQuery(query: StructuredQuery): Observable<QueryResult> {
    // In Phase 1, return mock results
    return new Observable(observer => {
      // Simulate API delay
      setTimeout(() => {
        const result = this.mockData.getMockQueryResults(query);
        observer.next(result);
        observer.complete();
      }, 1500);
    });
  }

  generateExpectations(query: StructuredQuery | null): string[] {
    if (!query) return [];
    
    const expectations: string[] = [];
    
    switch (query.template) {
      case 'COMPARE_CLAUSES':
        expectations.push('Extract specified clause types from contracts');
        expectations.push('Align clauses for side-by-side comparison');
        expectations.push('Highlight key differences and similarities');
        expectations.push('Provide confidence scores for each extraction');
        break;
        
      case 'FIND_CONTRACTS':
        expectations.push('Search across all contract metadata');
        expectations.push('Return matching contracts with key details');
        expectations.push('Sort by relevance or date');
        expectations.push('Include contract summary information');
        break;
        
      case 'ANALYZE_CONTRACT':
        expectations.push('Extract all key terms and conditions');
        expectations.push('Identify risks and obligations');
        expectations.push('Analyze governing law implications');
        expectations.push('Provide actionable insights');
        break;
        
      case 'COMPARE_CONTRACTS':
        expectations.push('Load full contract details');
        expectations.push('Compare selected aspects across contracts');
        expectations.push('Generate comparison matrix');
        expectations.push('Highlight significant differences');
        break;
    }
    
    return expectations;
  }

  clearQuery(): void {
    this.currentQuerySubject.next(null);
    this.selectedTemplateSubject.next(null);
  }
}