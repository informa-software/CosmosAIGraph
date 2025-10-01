import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, Toast } from '../../services/toast.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container">
      <div *ngFor="let toast of toasts" 
           class="toast"
           [class.toast-error]="toast.type === 'error'"
           [class.toast-success]="toast.type === 'success'"
           [class.toast-warning]="toast.type === 'warning'"
           [class.toast-info]="toast.type === 'info'"
           [@slideIn]>
        <div class="toast-header">
          <span class="toast-icon">
            {{ getIcon(toast.type) }}
          </span>
          <strong class="toast-title">{{ toast.title }}</strong>
          <button (click)="removeToast(toast)" class="toast-close">×</button>
        </div>
        <div *ngIf="toast.message" class="toast-body">
          {{ toast.message }}
        </div>
      </div>
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
    }

    .toast {
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      padding: 12px;
      min-width: 300px;
      animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    .toast-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .toast-icon {
      font-size: 1.2rem;
    }

    .toast-title {
      flex: 1;
      font-size: 14px;
      font-weight: 600;
    }

    .toast-close {
      background: transparent;
      border: none;
      font-size: 1.5rem;
      cursor: pointer;
      color: #999;
      padding: 0;
      margin: -4px -4px 0 0;
    }

    .toast-close:hover {
      color: #333;
    }

    .toast-body {
      font-size: 13px;
      margin-left: 28px;
      color: #666;
    }

    .toast-error {
      border-left: 4px solid #dc3545;
    }

    .toast-error .toast-icon {
      color: #dc3545;
    }

    .toast-success {
      border-left: 4px solid #28a745;
    }

    .toast-success .toast-icon {
      color: #28a745;
    }

    .toast-warning {
      border-left: 4px solid #ffc107;
    }

    .toast-warning .toast-icon {
      color: #ffc107;
    }

    .toast-info {
      border-left: 4px solid #17a2b8;
    }

    .toast-info .toast-icon {
      color: #17a2b8;
    }
  `]
})
export class ToastComponent implements OnInit, OnDestroy {
  toasts: Toast[] = [];
  private subscription!: Subscription;
  private timeouts = new Map<string, any>();

  constructor(private toastService: ToastService) {}

  ngOnInit(): void {
    this.subscription = this.toastService.toasts$.subscribe(toast => {
      this.addToast(toast);
    });
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
    // Clear all timeouts
    this.timeouts.forEach(timeout => clearTimeout(timeout));
  }

  addToast(toast: Toast): void {
    this.toasts.push(toast);
    
    // Auto remove after duration
    if (toast.duration && toast.id) {
      const timeout = setTimeout(() => {
        this.removeToast(toast);
      }, toast.duration);
      this.timeouts.set(toast.id, timeout);
    }
  }

  removeToast(toast: Toast): void {
    const index = this.toasts.indexOf(toast);
    if (index > -1) {
      this.toasts.splice(index, 1);
      if (toast.id && this.timeouts.has(toast.id)) {
        clearTimeout(this.timeouts.get(toast.id));
        this.timeouts.delete(toast.id);
      }
    }
  }

  getIcon(type: string): string {
    switch (type) {
      case 'error': return '❌';
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'info': return 'ℹ️';
      default: return 'ℹ️';
    }
  }
}