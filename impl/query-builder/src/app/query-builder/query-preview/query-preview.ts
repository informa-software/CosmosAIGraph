import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { StructuredQuery } from '../models/query.models';
import { QueryBuilderService } from '../services/query-builder.service';
import { MockDataService } from '../services/mock-data.service';

@Component({
  selector: 'app-query-preview',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTabsModule,
    MatIconModule,
    MatButtonModule,
    MatListModule,
    MatProgressBarModule,
    MatTooltipModule
  ],
  templateUrl: './query-preview.html',
  styleUrls: ['./query-preview.scss'],
  providers: [QueryBuilderService, MockDataService]
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
      console.log('Copied to clipboard');
    });
  }

  getStrategyDescription(): string {
    if (!this.query) return '';
    
    switch (this.query.template) {
      case 'COMPARE_CLAUSES':
        return 'This query will use the orchestrated search strategy.';
      case 'FIND_CONTRACTS':
        return 'This query will use the database search strategy.';
      case 'ANALYZE_CONTRACT':
        return 'This query will use vector search.';
      case 'COMPARE_CONTRACTS':
        return 'This query will use a combination of strategies.';
      default:
        return '';
    }
  }
}
