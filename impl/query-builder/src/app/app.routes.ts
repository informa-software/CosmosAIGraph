import { Routes } from '@angular/router';
import { QueryBuilderMainComponent } from './query-builder/query-builder-main/query-builder-main';
import { ContractWorkbenchComponent } from './contract-workbench/contract-workbench';
import { CompareContractsComponent } from './compare-contracts/compare-contracts.component';
import { QueryContractsComponent } from './query-contracts/query-contracts.component';
import { ContractsListComponent } from './contracts/contracts-list/contracts-list.component';
import { ComplianceRulesComponent } from './compliance/compliance-rules/compliance-rules.component';
import { ComplianceRuleEditorComponent } from './compliance/compliance-rule-editor/compliance-rule-editor.component';
import { ComplianceDashboardComponent } from './compliance/compliance-dashboard/compliance-dashboard.component';
import { EvaluationTriggerComponent } from './compliance/evaluation-trigger/evaluation-trigger.component';
import { JobMonitorComponent } from './compliance/job-monitor/job-monitor.component';
import { ResultsViewerComponent } from './compliance/results-viewer/results-viewer.component';
import { RuleSetsComponent } from './compliance/rule-sets/rule-sets.component';
import { PreferencesComponent } from './preferences/preferences.component';
import { AnalyticsComponent } from './analytics/analytics.component';
import { ClauseListComponent } from './clause-library/clause-list/clause-list.component';
import { ClauseViewerComponent } from './clause-library/clause-viewer/clause-viewer.component';
import { ClauseEditorComponent } from './clause-library/clause-editor/clause-editor.component';
import { VariableManagerComponent } from './clause-library/variable-manager/variable-manager';
import { JobsPageComponent } from './jobs/jobs-page.component';

export const routes: Routes = [
  { path: '', redirectTo: '/contracts', pathMatch: 'full' },
  { path: 'contracts', component: ContractsListComponent },
  { path: 'compare-contracts', component: CompareContractsComponent },
  { path: 'query-contracts', component: QueryContractsComponent },
  { path: 'query-builder', component: QueryBuilderMainComponent },
  { path: 'contract-workbench', component: ContractWorkbenchComponent },
  { path: 'jobs', component: JobsPageComponent },

  // Settings Routes
  { path: 'preferences', component: PreferencesComponent },
  { path: 'analytics', component: AnalyticsComponent },

  // Clause Library Routes
  { path: 'clause-library', component: ClauseListComponent },
  { path: 'clause-library/new', component: ClauseEditorComponent },
  { path: 'clause-library/view/:id', component: ClauseViewerComponent },
  { path: 'clause-library/edit/:id', component: ClauseEditorComponent },
  { path: 'clause-library/variables', component: VariableManagerComponent },

  // Compliance Routes
  { path: 'compliance/dashboard', component: ComplianceDashboardComponent },
  { path: 'compliance/rules', component: ComplianceRulesComponent },
  { path: 'compliance/rules/new', component: ComplianceRuleEditorComponent },
  { path: 'compliance/rules/edit/:id', component: ComplianceRuleEditorComponent },
  { path: 'compliance/rules/view/:id', component: ComplianceRuleEditorComponent },
  { path: 'compliance/rule-sets', component: RuleSetsComponent },
  { path: 'compliance/evaluate', component: EvaluationTriggerComponent },
  { path: 'compliance/jobs', component: JobMonitorComponent },
  { path: 'compliance/jobs/:id', component: JobMonitorComponent },
  { path: 'compliance/results', component: ResultsViewerComponent }
];
