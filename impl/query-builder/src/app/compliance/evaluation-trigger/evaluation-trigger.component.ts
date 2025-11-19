import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { ComplianceService } from '../services/compliance.service';
import { RuleSetService } from '../services/rule-set.service';
import { ToastService } from '../../shared/services/toast.service';
import { ContractSelectorComponent, ContractReference } from '../contract-selector/contract-selector.component';
import {
  ComplianceRule,
  EvaluateContractRequest,
  EvaluateRuleRequest,
  BatchEvaluateRequest,
  RuleSet,
  RuleSetWithRuleCount
} from '../models/compliance.models';

@Component({
  selector: 'app-evaluation-trigger',
  standalone: true,
  imports: [CommonModule, FormsModule, ContractSelectorComponent],
  templateUrl: './evaluation-trigger.component.html',
  styleUrls: ['./evaluation-trigger.component.scss']
})

export class EvaluationTriggerComponent implements OnInit {
  // Evaluation modes
  evaluationMode: 'contract' | 'rule' | 'batch' = 'contract';

  // Contract evaluation - contracts selected from selector
  selectedContractIds: string[] = [];
  selectedContractReferences: ContractReference[] = []; // Track full contract details for display
  selectedRuleSetId: string = '';
  selectedRuleIds: string[] = [];
  evaluateAllRules: boolean = true;
  asyncMode: boolean = false;

  // Rule evaluation
  selectedRuleId: string = '';

  // Batch evaluation - contracts selected from selector
  batchSelectedContractIds: string[] = [];
  batchContractReferences: ContractReference[] = []; // Track full contract details for display
  batchRuleIds: string[] = [];
  evaluateAllRulesInBatch: boolean = true;

  // Available rules and rule sets
  availableRules: ComplianceRule[] = [];
  availableRuleSets: RuleSetWithRuleCount[] = [];
  loading: boolean = false;
  evaluating: boolean = false;

  constructor(
    private complianceService: ComplianceService,
    private ruleSetService: RuleSetService,
    private toastService: ToastService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.loadRules();
    this.loadRuleSets();

    // Check for contract_id query parameter
    this.route.queryParams.subscribe(params => {
      const contractId = params['contract_id'];
      const contractTitle = params['contract_name']; // Still called contract_name in URL for backwards compatibility
      if (contractId) {
        // Pre-select the contract for evaluation
        this.selectedContractIds = [contractId];
        this.selectedContractReferences = [{ id: contractId, title: contractTitle || contractId }];
        this.evaluationMode = 'contract';
      }
    });
  }

  /**
   * Handle contract selection from contract selector
   */
  onContractsSelected(contracts: ContractReference[]): void {
    this.selectedContractReferences = contracts;
    this.selectedContractIds = contracts.map(c => c.id);
  }

  /**
   * Handle batch contract selection from contract selector
   */
  onBatchContractsSelected(contracts: ContractReference[]): void {
    this.batchContractReferences = contracts;
    this.batchSelectedContractIds = contracts.map(c => c.id);
  }

  /**
   * Load available rules for selection
   */
  loadRules(): void {
    this.loading = true;
    this.complianceService.getRules(true).subscribe({
      next: (rules: ComplianceRule[]) => {
        this.availableRules = rules;
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Error loading rules:', error);
        this.toastService.error('Failed to load rules');
        this.loading = false;
      }
    });
  }

  /**
   * Load available rule sets for selection (active only)
   */
  loadRuleSets(): void {
    this.ruleSetService.getRuleSetsWithCounts(true).subscribe({
      next: (ruleSets) => {
        this.availableRuleSets = ruleSets;
      },
      error: (error: any) => {
        console.error('Error loading rule sets:', error);
        this.toastService.error('Failed to load rule sets');
      }
    });
  }

  /**
   * Toggle rule selection
   */
  toggleRuleSelection(ruleId: string): void {
    const index = this.selectedRuleIds.indexOf(ruleId);
    if (index > -1) {
      this.selectedRuleIds.splice(index, 1);
    } else {
      this.selectedRuleIds.push(ruleId);
    }
  }

  /**
   * Toggle batch rule selection
   */
  toggleBatchRuleSelection(ruleId: string): void {
    const index = this.batchRuleIds.indexOf(ruleId);
    if (index > -1) {
      this.batchRuleIds.splice(index, 1);
    } else {
      this.batchRuleIds.push(ruleId);
    }
  }

  /**
   * Check if rule is selected for contract evaluation
   */
  isRuleSelected(ruleId: string): boolean {
    return this.selectedRuleIds.includes(ruleId);
  }

  /**
   * Check if rule is selected for batch evaluation
   */
  isBatchRuleSelected(ruleId: string): boolean {
    return this.batchRuleIds.includes(ruleId);
  }

  /**
   * Validate contract evaluation form
   */
  validateContractForm(): boolean {
    if (this.selectedContractIds.length === 0) {
      this.toastService.error('Please select a contract from the list');
      return false;
    }
    if (!this.evaluateAllRules && this.selectedRuleIds.length === 0) {
      this.toastService.error('Select at least one rule or choose "All Active Rules"');
      return false;
    }
    return true;
  }

  /**
   * Validate rule evaluation form
   */
  validateRuleForm(): boolean {
    if (!this.selectedRuleId) {
      this.toastService.error('Please select a rule to evaluate');
      return false;
    }
    return true;
  }

  /**
   * Validate batch evaluation form
   */
  validateBatchForm(): boolean {
    if (this.batchSelectedContractIds.length === 0) {
      this.toastService.error('Please select at least one contract from the list');
      return false;
    }
    if (!this.evaluateAllRulesInBatch && this.batchRuleIds.length === 0) {
      this.toastService.error('Select at least one rule or choose "All Active Rules"');
      return false;
    }
    return true;
  }

  /**
   * Execute contract evaluation
   */
  evaluateContract(): void {
    if (!this.validateContractForm()) return;

    // Check if background execution is selected
    if (this.asyncMode) {
      this.toastService.info(
        'Feature Not Yet Implemented',
        'Background Compliance Execution Feature Not Yet Implemented'
      );
      return;
    }

    // Use the first selected contract (single-select mode)
    const contractId = this.selectedContractIds[0];

    const request: EvaluateContractRequest = {
      contract_id: contractId,
      rule_set_id: this.selectedRuleSetId || undefined,
      rule_ids: this.evaluateAllRules ? undefined : this.selectedRuleIds,
      async_mode: this.asyncMode
    };

    this.evaluating = true;
    this.complianceService.evaluateContract(request).subscribe({
      next: (response: any) => {
        if (response.job_id) {
          this.toastService.success(`Evaluation job started: ${response.job_id}`);
          this.router.navigate(['/compliance/jobs', response.job_id]);
        } else {
          this.toastService.success(`Evaluation complete: ${response.summary.pass} passed, ${response.summary.fail} failed`);
        }
        this.evaluating = false;
        this.resetContractForm();
      },
      error: (error: any) => {
        console.error('Evaluation error:', error);
        this.toastService.error('Evaluation failed', error.message || 'Unknown error');
        this.evaluating = false;
      }
    });
  }

  /**
   * Execute rule evaluation
   */
  evaluateRule(): void {
    if (!this.validateRuleForm()) return;

    // Rule evaluation feature not yet implemented
    this.toastService.info(
      'Feature Not Yet Implemented',
      'Evaluate Rule Feature Not Yet Implemented'
    );
    return;

    const request: EvaluateRuleRequest = {
      rule_id: this.selectedRuleId,
      contract_ids: undefined // Evaluate against all contracts
    };

    this.evaluating = true;
    this.complianceService.evaluateRule(request).subscribe({
      next: (response: any) => {
        this.toastService.success(`Evaluation job started: ${response.job_id}`);
        this.router.navigate(['/compliance/jobs', response.job_id]);
        this.evaluating = false;
        this.resetRuleForm();
      },
      error: (error: any) => {
        console.error('Evaluation error:', error);
        this.toastService.error('Evaluation failed', error.message || 'Unknown error');
        this.evaluating = false;
      }
    });
  }

  /**
   * Execute batch evaluation
   */
  executeBatchEvaluation(): void {
    if (!this.validateBatchForm()) return;

    // Batch evaluation feature not yet implemented
    this.toastService.info(
      'Feature Not Yet Implemented',
      'Batch Compliance Evaluation Feature Not Yet Implemented'
    );
    return;

    const request: BatchEvaluateRequest = {
      contract_ids: this.batchSelectedContractIds,
      rule_ids: this.evaluateAllRulesInBatch ? undefined : this.batchRuleIds
    };

    this.evaluating = true;
    this.complianceService.batchEvaluate(request).subscribe({
      next: (response: any) => {
        this.toastService.success(`Batch evaluation started: ${response.job_id}`);
        this.router.navigate(['/compliance/jobs', response.job_id]);
        this.evaluating = false;
        this.resetBatchForm();
      },
      error: (error: any) => {
        console.error('Batch evaluation error:', error);
        this.toastService.error('Batch evaluation failed', error.message || 'Unknown error');
        this.evaluating = false;
      }
    });
  }

  /**
   * Reset contract evaluation form
   */
  resetContractForm(): void {
    this.selectedContractIds = [];
    this.selectedRuleIds = [];
    this.evaluateAllRules = true;
  }

  /**
   * Reset rule evaluation form
   */
  resetRuleForm(): void {
    this.selectedRuleId = '';
  }

  /**
   * Reset batch evaluation form
   */
  resetBatchForm(): void {
    this.batchSelectedContractIds = [];
    this.batchRuleIds = [];
    this.evaluateAllRulesInBatch = true;
  }

  /**
   * Navigate to dashboard
   */
  viewDashboard(): void {
    this.router.navigate(['/compliance/dashboard']);
  }

  /**
   * Navigate to jobs list
   */
  viewJobs(): void {
    this.router.navigate(['/compliance/jobs']);
  }

  /**
   * Get the selected rule for display
   */
  getSelectedRule(): ComplianceRule | undefined {
    return this.availableRules.find(rule => rule.id === this.selectedRuleId);
  }

  /**
   * Get count of contracts selected in batch mode
   */
  getBatchContractCount(): number {
    return this.batchSelectedContractIds.length;
  }

  /**
   * Get total evaluations for batch mode
   */
  getBatchTotalEvaluations(): number {
    const contractCount = this.getBatchContractCount();
    const ruleCount = this.evaluateAllRulesInBatch ? this.availableRules.length : this.batchRuleIds.length;
    return contractCount * ruleCount;
  }
}
