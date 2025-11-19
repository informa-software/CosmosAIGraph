import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  {
    path: 'home',
    loadComponent: () => import('./home/home.component').then(m => m.HomeComponent)
  },
  {
    path: 'word',
    loadComponent: () => import('./word-addin/word-addin.component').then(m => m.WordAddinComponent)
  }
  // Future routes: excel, powerpoint, outlook, etc.
];
