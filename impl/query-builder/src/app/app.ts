import { Component, HostListener, OnInit, OnDestroy } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ToastComponent } from './shared/components/toast/toast.component';
import { JobNotificationService } from './shared/services/job-notification.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, ToastComponent],
  template: `
    <nav class="navbar">
      <div class="navbar-brand">
        <img src="/Informa Software Logo.svg" alt="Informa" class="navbar-logo">
        <h1>Contract Intelligence Workbench</h1>
      </div>
      <div class="navbar-links">
        <a routerLink="/contracts" routerLinkActive="active" class="nav-link">
          Contracts
        </a>
        <a routerLink="/compare-contracts" routerLinkActive="active" class="nav-link">
          Compare Contracts
        </a>
        <a routerLink="/query-contracts" routerLinkActive="active" class="nav-link">
          Query Contracts
        </a>
        <a routerLink="/compliance/dashboard" routerLinkActive="active" class="nav-link">
          Compliance Dashboard
        </a>
        <a routerLink="/clause-library" routerLinkActive="active" class="nav-link">
          Clause Library
        </a>
        <a routerLink="/jobs" routerLinkActive="active" class="nav-link nav-link-jobs">
          Jobs
          <span class="job-count-badge" *ngIf="activeJobCount > 0">{{ activeJobCount }}</span>
        </a>
        <div class="settings-dropdown" [class.open]="showSettingsDropdown">
          <button
            class="settings-button"
            (click)="toggleSettingsDropdown()"
            title="Settings">
            ⚙️
          </button>
          <div class="dropdown-menu" *ngIf="showSettingsDropdown">
            <a class="dropdown-item" (click)="navigateToPreferences()">
              <span class="menu-icon">👤</span>
              User Preferences
            </a>
            <a class="dropdown-item" (click)="navigateToAnalytics()">
              <span class="menu-icon">📊</span>
              Usage Analytics
            </a>
          </div>
        </div>
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
      align-items: center;
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

    .nav-link-jobs {
      position: relative;
    }

    .job-count-badge {
      position: absolute;
      top: 0.25rem;
      right: 0.5rem;
      background: #ff4444;
      color: white;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 0.15rem 0.4rem;
      border-radius: 10px;
      min-width: 1.2rem;
      text-align: center;
      line-height: 1;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
      }
      50% {
        transform: scale(1.1);
      }
    }

    .settings-dropdown {
      position: relative;
    }

    .settings-button {
      background: rgba(255,255,255,0.2);
      border: none;
      color: white;
      font-size: 1.5rem;
      width: 44px;
      height: 44px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .settings-button:hover {
      background: rgba(255,255,255,0.3);
      transform: scale(1.05);
    }

    .settings-button:active {
      transform: scale(0.95);
    }

    .dropdown-menu {
      position: absolute;
      top: calc(100% + 8px);
      right: 0;
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      min-width: 220px;
      z-index: 1000;
      animation: dropdownFadeIn 0.2s ease;
    }

    .dropdown-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      color: #333;
      text-decoration: none;
      cursor: pointer;
      transition: background-color 0.2s ease;
      border-bottom: 1px solid #f0f0f0;
    }

    .dropdown-item:first-child {
      border-radius: 8px 8px 0 0;
    }

    .dropdown-item:last-child {
      border-bottom: none;
      border-radius: 0 0 8px 8px;
    }

    .dropdown-item:hover {
      background-color: #f8f9fa;
    }

    .menu-icon {
      margin-right: 12px;
      font-size: 1.2rem;
    }

    @keyframes dropdownFadeIn {
      from {
        opacity: 0;
        transform: translateY(-8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `]
})
export class App implements OnInit, OnDestroy {
  title = 'query-builder';
  showSettingsDropdown = false;
  activeJobCount = 0;
  private jobCountsSubscription?: Subscription;

  constructor(
    private router: Router,
    private jobNotificationService: JobNotificationService
  ) {}

  ngOnInit(): void {
    // Subscribe to user jobs updates to get job counts
    this.jobNotificationService.subscribeToUserJobs('system');

    this.jobCountsSubscription = this.jobNotificationService.getJobCounts().subscribe({
      next: (counts) => {
        // Badge shows only active jobs (queued + processing)
        this.activeJobCount = counts.queued + counts.processing;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.jobCountsSubscription) {
      this.jobCountsSubscription.unsubscribe();
    }
    this.jobNotificationService.disconnectUserJobsStream();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    const clickedInsideSettings = target.closest('.settings-dropdown');

    if (!clickedInsideSettings) {
      this.showSettingsDropdown = false;
    }
  }

  toggleSettingsDropdown(): void {
    this.showSettingsDropdown = !this.showSettingsDropdown;
  }

  navigateToPreferences(): void {
    this.showSettingsDropdown = false;
    this.router.navigate(['/preferences']);
  }

  navigateToAnalytics(): void {
    this.showSettingsDropdown = false;
    this.router.navigate(['/analytics']);
  }
}
