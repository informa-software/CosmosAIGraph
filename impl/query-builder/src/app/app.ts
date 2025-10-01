import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ToastComponent } from './shared/components/toast/toast.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, ToastComponent],
  template: `
    <nav class="navbar">
      <div class="navbar-brand">
        <img src="/Informa Software Logo.svg" alt="Informa" class="navbar-logo">
        <h1>Intelligent Contract Analysis</h1>
      </div>
      <div class="navbar-links">
        <a routerLink="/query-builder" routerLinkActive="active" class="nav-link">
          Query Builder
        </a>
        <a routerLink="/contract-workbench" routerLinkActive="active" class="nav-link">
          Contract Workbench
        </a>
      </div>
    </nav>
    <router-outlet></router-outlet>
    <app-toast></app-toast>
  `,
  styles: [`
    .navbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 2rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .navbar-brand {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .navbar-logo {
      height: 80px;
      width: auto;
    }

    .navbar-brand h1 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
    }

    .navbar-links {
      display: flex;
      gap: 1rem;
    }

    .nav-link {
      padding: 0.5rem 1rem;
      color: white;
      text-decoration: none;
      border-radius: 6px;
      transition: background 0.2s;
    }

    .nav-link:hover {
      background: rgba(255,255,255,0.1);
    }

    .nav-link.active {
      background: rgba(255,255,255,0.2);
      font-weight: 500;
    }
  `]
})
export class App {
  title = 'query-builder';
}
