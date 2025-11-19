import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

export interface ModelPreference {
  default_model: string; // "primary" or "secondary"
  auto_select: boolean;
  cost_optimization: boolean;
}

export interface UserPreferences {
  id?: string;
  type: string;
  user_email: string;
  model_preference: ModelPreference;
  created_date?: string;
  modified_date?: string;
}

export interface UsageSummary {
  period_days: number;
  start_date: string;
  end_date: string;
  user_email: string;
  operations: OperationUsage[];  // NEW: Operation-level breakdown
  models: ModelUsage[];
  totals: UsageTotals;
}

export interface OperationUsage {
  operation: string;
  total_operations: number;
  successful_operations: number;
  failed_operations: number;
  success_rate: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost: number;
  avg_time: number;
  models_used: string[];
}

export interface ModelUsage {
  model: string;
  total_operations: number;
  total_tokens: number;
  total_cost: number;
  avg_time: number;
}

export interface UsageTotals {
  total_operations: number;
  total_success: number;  // NEW
  success_rate: number;  // NEW
  total_prompt_tokens: number;  // NEW
  total_completion_tokens: number;  // NEW
  total_tokens: number;
  total_cost: number;
}

export interface CostSavings {
  period_days: number;
  user_email: string;
  primary_model_usage: {
    operations: number;
    tokens: number;
    actual_cost: number;
  };
  if_using_secondary: {
    potential_cost: number;
    savings: number;
    savings_percentage: number;
  };
  operation_breakdown?: OperationSavings[];  // NEW: Per-operation savings
  recommendation: string;
}

export interface OperationSavings {
  operation: string;
  count: number;
  tokens: number;
  actual_cost: number;
  potential_cost: number;
  savings: number;
  savings_percentage: number;
}

export interface UsageTimeline {
  period_days: number;
  start_date: string;
  end_date: string;
  user_email: string;
  timeline: DailyUsage[];
}

export interface DailyUsage {
  date: string;
  model: string;
  operations: number;  // Count of all operations for this day/model
  tokens: number;
  cost: number;
}

@Injectable({
  providedIn: 'root'
})
export class UserPreferencesService {
  private apiUrl = 'https://localhost:8000/api';  // Backend API URL
  private baseUrl = `${this.apiUrl}/user-preferences`;
  private analyticsUrl = `${this.apiUrl}/analytics`;

  // Cache for user preferences
  private preferencesSubject = new BehaviorSubject<UserPreferences | null>(null);
  public preferences$ = this.preferencesSubject.asObservable();

  // Default user email - TODO: Replace with actual auth service
  // Using 'system' to match backend LLM tracking until user authentication is implemented
  private currentUserEmail = 'system';

  constructor(private http: HttpClient) {
    // Load preferences on initialization
    this.loadPreferences();
  }

  /**
   * Get current user email
   */
  getCurrentUserEmail(): string {
    return this.currentUserEmail;
  }

  /**
   * Set current user email (for testing/auth integration)
   */
  setCurrentUserEmail(email: string): void {
    this.currentUserEmail = email;
    this.loadPreferences();
  }

  /**
   * Load user preferences from backend
   */
  loadPreferences(): void {
    this.getModelPreference(this.currentUserEmail).subscribe({
      next: (prefs) => {
        this.preferencesSubject.next(prefs);
      },
      error: (error) => {
        console.error('Error loading preferences:', error);
        // Return default preferences
        this.preferencesSubject.next(this.getDefaultPreferences());
      }
    });
  }

  /**
   * Get model preference for a user
   */
  getModelPreference(userEmail: string): Observable<UserPreferences> {
    const params = new HttpParams().set('user_email', userEmail);

    return this.http.get<UserPreferences>(`${this.baseUrl}/model-preference`, { params }).pipe(
      catchError((error) => {
        console.error('Error getting model preference:', error);
        return of(this.getDefaultPreferences(userEmail));
      })
    );
  }

  /**
   * Save model preference for a user
   */
  saveModelPreference(userEmail: string, preference: ModelPreference): Observable<any> {
    const params = new HttpParams().set('user_email', userEmail);

    return this.http.post(`${this.baseUrl}/model-preference`, preference, { params }).pipe(
      tap(() => {
        // Update cached preferences
        this.loadPreferences();
      }),
      catchError((error) => {
        console.error('Error saving model preference:', error);
        throw error;
      })
    );
  }

  /**
   * Delete model preference for a user
   */
  deleteModelPreference(userEmail: string): Observable<any> {
    const params = new HttpParams().set('user_email', userEmail);

    return this.http.delete(`${this.baseUrl}/model-preference`, { params }).pipe(
      tap(() => {
        // Reset to default preferences
        this.preferencesSubject.next(this.getDefaultPreferences());
      }),
      catchError((error) => {
        console.error('Error deleting model preference:', error);
        throw error;
      })
    );
  }

  /**
   * Get usage summary for a period
   */
  getUsageSummary(userEmail: string, days: number = 30): Observable<UsageSummary> {
    const params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    return this.http.get<UsageSummary>(`${this.analyticsUrl}/usage-summary`, { params });
  }

  /**
   * Get cost savings analysis
   */
  getCostSavings(userEmail: string, days: number = 30): Observable<CostSavings> {
    const params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    return this.http.get<CostSavings>(`${this.analyticsUrl}/cost-savings`, { params });
  }

  /**
   * Get usage timeline for charting
   */
  getUsageTimeline(userEmail: string, days: number = 30): Observable<UsageTimeline> {
    const params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    return this.http.get<UsageTimeline>(`${this.analyticsUrl}/usage-timeline`, { params });
  }

  /**
   * Get operation breakdown with detailed metrics
   */
  getOperationBreakdown(userEmail: string, days: number = 30): Observable<any> {
    const params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    return this.http.get(`${this.analyticsUrl}/operation-breakdown`, { params });
  }

  /**
   * Get token efficiency analysis
   */
  getTokenEfficiency(userEmail: string, days: number = 30, operationFilter?: string): Observable<any> {
    let params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    if (operationFilter) {
      params = params.set('operation_filter', operationFilter);
    }

    return this.http.get(`${this.analyticsUrl}/token-efficiency`, { params });
  }

  /**
   * Get error analysis
   */
  getErrorAnalysis(userEmail: string, days: number = 30): Observable<any> {
    const params = new HttpParams()
      .set('user_email', userEmail)
      .set('days', days.toString());

    return this.http.get(`${this.analyticsUrl}/error-analysis`, { params });
  }

  /**
   * Get current selected model (from preferences or default)
   */
  getCurrentModelSelection(): string {
    const prefs = this.preferencesSubject.value;
    return prefs?.model_preference?.default_model || 'primary';
  }

  /**
   * Get default preferences
   */
  private getDefaultPreferences(userEmail?: string): UserPreferences {
    return {
      type: 'user_preferences',
      user_email: userEmail || this.currentUserEmail,
      model_preference: {
        default_model: 'primary',
        auto_select: false,
        cost_optimization: false
      }
    };
  }
}
