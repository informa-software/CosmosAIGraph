import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ContractWorkbenchComponent } from '../contract-workbench/contract-workbench';

@Component({
  selector: 'app-compare-contracts',
  standalone: true,
  imports: [CommonModule, ContractWorkbenchComponent],
  template: `
    <app-contract-workbench #workbench></app-contract-workbench>
  `
})
export class CompareContractsComponent implements OnInit {
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
            this.workbench.loadSavedResult(resultId);
          }
        }, 100);
      }
    });
  }

  ngAfterViewInit(): void {
    // Set the workbench to comparison mode after view initialization
    if (this.workbench) {
      this.workbench.workbenchMode = 'comparison';
      this.workbench.pageTitle = 'Compare Contracts';
      this.workbench.pageIcon = '📊';
      this.workbench.updateTabForMode();
    }
  }
}
