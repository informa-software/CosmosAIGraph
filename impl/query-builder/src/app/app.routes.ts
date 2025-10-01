import { Routes } from '@angular/router';
import { QueryBuilderMainComponent } from './query-builder/query-builder-main/query-builder-main';
import { ContractWorkbenchComponent } from './contract-workbench/contract-workbench';

export const routes: Routes = [
  { path: '', redirectTo: '/query-builder', pathMatch: 'full' },
  { path: 'query-builder', component: QueryBuilderMainComponent },
  { path: 'contract-workbench', component: ContractWorkbenchComponent }
];
