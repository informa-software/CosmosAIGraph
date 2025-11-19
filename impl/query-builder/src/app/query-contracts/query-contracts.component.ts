import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ContractWorkbenchComponent } from '../contract-workbench/contract-workbench';

@Component({
  selector: 'app-query-contracts',
  standalone: true,
  imports: [CommonModule, ContractWorkbenchComponent],
  template: `
    <app-contract-workbench #workbench></app-contract-workbench>
  `
})
export class QueryContractsComponent implements OnInit {
  @ViewChild('workbench', { static: false }) workbench!: ContractWorkbenchComponent;

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    // Check for resultId query parameter to load saved results
    this.route.queryParams.subscribe(params => {
      const resultId = params['resultId'];
      if (resultId) {
        // Will load results after view initialization
        setTimeout(() => {
          if (this.workbench) {
            this.workbench.loadSavedQueryResult(resultId);
          }
        }, 100);
      }
    });
  }

  ngAfterViewInit(): void {
    // Set the workbench to question mode after view initialization
    if (this.workbench) {
      this.workbench.workbenchMode = 'question';
      this.workbench.pageTitle = 'Query Contracts';
      this.workbench.pageIcon = '🔍';
      this.workbench.updateTabForMode();
    }
  }
}
