import { Component, Input } from '@angular/core';
import { StructuredQuery } from '../../models/query.models';
import { QueryBuilderService } from '../../services/query-builder.service';

@Component({
  selector: 'app-query-preview',
  templateUrl: './query-preview.component.html',
  styleUrls: ['./query-preview.component.scss']
})
export class QueryPreviewComponent {
  @Input() query: StructuredQuery | null = null;
  
  selectedTabIndex = 0;

  constructor(private queryService: QueryBuilderService) {}

  get naturalLanguage(): string {
    return this.queryService.toNaturalLanguage(this.query);
  }

  get expectations(): string[] {
    return this.queryService.generateExpectations(this.query);
  }

  get formattedJson(): string {
    if (!this.query) return '{}';
    
    // Create a clean version for display
    const displayQuery = {
      template: this.query.template,
      operation: this.query.operation,
      target: this.query.target,
      filters: this.query.filters,
      displayNames: this.query.displayNames,
      options: this.query.options
    };
    
    return JSON.stringify(displayQuery, null, 2);
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      // Could show a snackbar notification here
      console.log('Copied to clipboard');
    });
  }

  getStrategyDescription(): string {
    if (!this.query) return '';
    
    switch (this.query.template) {
      case 'COMPARE_CLAUSES':
        return 'This query will use the orchestrated search strategy, combining database lookups, vector search, and graph traversal to find and compare the specified clauses.';
      case 'FIND_CONTRACTS':
        return 'This query will use the database search strategy to efficiently filter contracts based on metadata fields.';
      case 'ANALYZE_CONTRACT':
        return 'This query will use vector search to retrieve relevant contract chunks and apply AI analysis to extract insights.';
      case 'COMPARE_CONTRACTS':
        return 'This query will use a combination of database and vector search to load full contract details for comparison.';
      default:
        return '';
    }
  }
}