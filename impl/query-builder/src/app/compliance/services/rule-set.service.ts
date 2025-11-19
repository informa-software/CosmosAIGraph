import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import {
  RuleSet,
  RuleSetCreate,
  RuleSetUpdate,
  RuleSetListResponse,
  RuleSetWithRuleCount,
  AddRulesToSetRequest,
  RemoveRulesFromSetRequest,
  CloneRuleSetRequest
} from '../models/compliance.models';

@Injectable({
  providedIn: 'root'
})
export class RuleSetService {
  private apiUrl = 'https://localhost:8000/api/rule_sets';

  constructor(private http: HttpClient) {}

  // ============================================================================
  // RULE SET CRUD OPERATIONS
  // ============================================================================

  /**
   * Get all rule sets with optional filtering
   */
  getRuleSets(includeInactive: boolean = false): Observable<RuleSetListResponse> {
    let params = new HttpParams();
    if (includeInactive) {
      params = params.set('include_inactive', 'true');
    }

    return this.http.get<RuleSetListResponse>(this.apiUrl, { params }).pipe(
      catchError(error => {
        console.error('Error fetching rule sets:', error);
        return of({ rule_sets: [], total: 0 });
      })
    );
  }

  /**
   * Get all rule sets with rule counts
   */
  getRuleSetsWithCounts(includeInactive: boolean = false): Observable<RuleSetWithRuleCount[]> {
    let params = new HttpParams();
    if (includeInactive) {
      params = params.set('include_inactive', 'true');
    }

    return this.http.get<RuleSetWithRuleCount[]>(`${this.apiUrl}/with-counts`, { params }).pipe(
      catchError(error => {
        console.error('Error fetching rule sets with counts:', error);
        return of([]);
      })
    );
  }

  /**
   * Get a single rule set by ID
   */
  getRuleSet(ruleSetId: string): Observable<RuleSet | null> {
    return this.http.get<RuleSet>(`${this.apiUrl}/${ruleSetId}`).pipe(
      catchError(error => {
        console.error(`Error fetching rule set ${ruleSetId}:`, error);
        return of(null);
      })
    );
  }

  /**
   * Create a new rule set
   */
  createRuleSet(ruleSet: RuleSetCreate): Observable<RuleSet> {
    return this.http.post<RuleSet>(this.apiUrl, ruleSet).pipe(
      catchError(error => {
        console.error('Error creating rule set:', error);
        throw error; // Re-throw to allow component to handle
      })
    );
  }

  /**
   * Update an existing rule set
   */
  updateRuleSet(ruleSetId: string, updates: RuleSetUpdate): Observable<RuleSet> {
    return this.http.put<RuleSet>(`${this.apiUrl}/${ruleSetId}`, updates).pipe(
      catchError(error => {
        console.error(`Error updating rule set ${ruleSetId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Delete a rule set
   */
  deleteRuleSet(ruleSetId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${ruleSetId}`).pipe(
      catchError(error => {
        console.error(`Error deleting rule set ${ruleSetId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Clone an existing rule set
   */
  cloneRuleSet(ruleSetId: string, request: CloneRuleSetRequest): Observable<RuleSet> {
    return this.http.post<RuleSet>(`${this.apiUrl}/${ruleSetId}/clone`, request).pipe(
      catchError(error => {
        console.error(`Error cloning rule set ${ruleSetId}:`, error);
        throw error;
      })
    );
  }

  // ============================================================================
  // RULE MANAGEMENT OPERATIONS
  // ============================================================================

  /**
   * Get all rule IDs in a rule set
   */
  getRulesInSet(ruleSetId: string): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/${ruleSetId}/rules`).pipe(
      catchError(error => {
        console.error(`Error fetching rules in set ${ruleSetId}:`, error);
        return of([]);
      })
    );
  }

  /**
   * Add rules to a rule set
   */
  addRulesToSet(ruleSetId: string, request: AddRulesToSetRequest): Observable<RuleSet> {
    return this.http.post<RuleSet>(`${this.apiUrl}/${ruleSetId}/rules`, request).pipe(
      catchError(error => {
        console.error(`Error adding rules to set ${ruleSetId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Remove rules from a rule set
   */
  removeRulesFromSet(ruleSetId: string, request: RemoveRulesFromSetRequest): Observable<RuleSet> {
    return this.http.delete<RuleSet>(`${this.apiUrl}/${ruleSetId}/rules`, {
      body: request
    }).pipe(
      catchError(error => {
        console.error(`Error removing rules from set ${ruleSetId}:`, error);
        throw error;
      })
    );
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  /**
   * Get active rule sets only
   */
  getActiveRuleSets(): Observable<RuleSetListResponse> {
    return this.getRuleSets(false);
  }

  /**
   * Get all rule sets including inactive
   */
  getAllRuleSets(): Observable<RuleSetListResponse> {
    return this.getRuleSets(true);
  }
}
