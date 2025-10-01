import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export interface Toast {
  id?: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  private toastSubject = new Subject<Toast>();
  toasts$ = this.toastSubject.asObservable();

  show(toast: Toast): void {
    // Generate unique ID
    toast.id = Math.random().toString(36).substr(2, 9);
    
    // Default duration is 5 seconds for errors, 3 seconds for others
    if (!toast.duration) {
      toast.duration = toast.type === 'error' ? 5000 : 3000;
    }
    
    this.toastSubject.next(toast);
  }

  error(title: string, message?: string): void {
    this.show({ type: 'error', title, message });
  }

  success(title: string, message?: string): void {
    this.show({ type: 'success', title, message });
  }

  warning(title: string, message?: string): void {
    this.show({ type: 'warning', title, message });
  }

  info(title: string, message?: string): void {
    this.show({ type: 'info', title, message });
  }
}