import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
  ComplianceRule,
  ComplianceRuleRequest,
  ComplianceResult,
  ContractEvaluationResults,
  RuleEvaluationResults,
  ComplianceSummary,
  StaleRule,
  EvaluationJob,
  EvaluateContractRequest,
  EvaluateContractResponse,
  EvaluateRuleRequest,
  EvaluateRuleResponse,
  BatchEvaluateRequest,
  BatchEvaluateResponse,
  Category,
  CategoryRequest
} from '../models/compliance.models';

@Injectable({
  providedIn: 'root'
})
export class ComplianceService {
  private apiUrl = 'https://localhost:8000/api/compliance';

  constructor(private http: HttpClient) {}

  // ============================================================================
  // RULES CRUD OPERATIONS
  // ============================================================================

  /**
   * Get all compliance rules with optional filtering
   */
  getRules(
    activeOnly?: boolean,
    category?: string,
    severity?: string
  ): Observable<ComplianceRule[]> {
    let params = new HttpParams();

    if (activeOnly !== undefined) {
      params = params.set('active_only', activeOnly.toString());
    }
    if (category) {
      params = params.set('category', category);
    }
    if (severity) {
      params = params.set('severity', severity);
    }

    return this.http.get<ComplianceRule[]>(`${this.apiUrl}/rules`, { params }).pipe(
      catchError(error => {
        console.error('Error fetching compliance rules:', error);
        return of([]);
      })
    );
  }

  /**
   * Get a single compliance rule by ID
   */
  getRule(ruleId: string): Observable<ComplianceRule | null> {
    return this.http.get<ComplianceRule>(`${this.apiUrl}/rules/${ruleId}`).pipe(
      catchError(error => {
        console.error(`Error fetching rule ${ruleId}:`, error);
        return of(null);
      })
    );
  }

  /**
   * Create a new compliance rule
   */
  createRule(rule: ComplianceRuleRequest): Observable<ComplianceRule | null> {
    return this.http.post<ComplianceRule>(`${this.apiUrl}/rules`, rule).pipe(
      catchError(error => {
        console.error('Error creating compliance rule:', error);
        throw error; // Re-throw to allow component to handle
      })
    );
  }

  /**
   * Update an existing compliance rule
   */
  updateRule(ruleId: string, updates: Partial<ComplianceRuleRequest>): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/rules/${ruleId}`, updates).pipe(
      catchError(error => {
        console.error(`Error updating rule ${ruleId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Delete a compliance rule
   */
  deleteRule(ruleId: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/rules/${ruleId}`).pipe(
      catchError(error => {
        console.error(`Error deleting rule ${ruleId}:`, error);
        throw error;
      })
    );
  }

  // ============================================================================
  // EVALUATION OPERATIONS
  // ============================================================================

  /**
   * Evaluate a specific contract against all active rules or selected rules
   */
  evaluateContract(request: EvaluateContractRequest): Observable<EvaluateContractResponse> {
    return this.http.post<EvaluateContractResponse>(
      `${this.apiUrl}/evaluate/contract/${request.contract_id}`,
      request
    ).pipe(
      catchError(error => {
        console.error(`Error evaluating contract ${request.contract_id}:`, error);
        throw error;
      })
    );
  }

  /**
   * Evaluate a specific rule against contracts
   */
  evaluateRule(request: EvaluateRuleRequest): Observable<EvaluateRuleResponse> {
    return this.http.post<EvaluateRuleResponse>(
      `${this.apiUrl}/evaluate/rule/${request.rule_id}`,
      request
    ).pipe(
      catchError(error => {
        console.error(`Error evaluating rule ${request.rule_id}:`, error);
        throw error;
      })
    );
  }

  /**
   * Re-evaluate stale results for a specific rule
   */
  reevaluateStaleRule(ruleId: string): Observable<EvaluateRuleResponse> {
    return this.http.post<EvaluateRuleResponse>(
      `${this.apiUrl}/reevaluate/stale/${ruleId}`,
      {}
    ).pipe(
      catchError(error => {
        console.error(`Error re-evaluating stale rule ${ruleId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Batch evaluate multiple contracts against rules
   */
  batchEvaluate(request: BatchEvaluateRequest): Observable<BatchEvaluateResponse> {
    return this.http.post<BatchEvaluateResponse>(
      `${this.apiUrl}/evaluate/batch`,
      request
    ).pipe(
      catchError(error => {
        console.error('Error batch evaluating:', error);
        throw error;
      })
    );
  }

  // ============================================================================
  // RESULTS OPERATIONS
  // ============================================================================

  /**
   * Get all evaluation results across all contracts and rules
   */
  getAllResults(
    resultFilter?: string,
    limit?: number
  ): Observable<ComplianceResult[]> {
    let params = new HttpParams();
    if (resultFilter) {
      params = params.set('result_filter', resultFilter);
    }
    if (limit) {
      params = params.set('limit', limit.toString());
    }

    return this.http.get<ComplianceResult[]>(
      `${this.apiUrl}/results`,
      { params }
    ).pipe(
      catchError(error => {
        console.error('Error fetching all results:', error);
        return of([]);
      })
    );
  }

  /**
   * Get all evaluation results for a specific contract
   */
  getContractResults(
    contractId: string,
    includeStale?: boolean
  ): Observable<ContractEvaluationResults> {
    let params = new HttpParams();
    if (includeStale !== undefined) {
      params = params.set('include_stale', includeStale.toString());
    }

    return this.http.get<ContractEvaluationResults>(
      `${this.apiUrl}/results/contract/${contractId}`,
      { params }
    ).pipe(
      catchError(error => {
        console.error(`Error fetching results for contract ${contractId}:`, error);
        return of({
          contract_id: contractId,
          results: [],
          summary: { total: 0, pass: 0, fail: 0, partial: 0, not_applicable: 0 }
        });
      })
    );
  }

  /**
   * Get all evaluation results for a specific rule
   */
  getRuleResults(
    ruleId: string,
    resultFilter?: string
  ): Observable<RuleEvaluationResults> {
    let params = new HttpParams();
    if (resultFilter) {
      params = params.set('result_filter', resultFilter);
    }

    return this.http.get<RuleEvaluationResults>(
      `${this.apiUrl}/results/rule/${ruleId}`,
      { params }
    ).pipe(
      catchError(error => {
        console.error(`Error fetching results for rule ${ruleId}:`, error);
        throw error;
      })
    );
  }

  /**
   * Get compliance summary dashboard data
   */
  getSummary(): Observable<ComplianceSummary> {
    return this.http.get<ComplianceSummary>(`${this.apiUrl}/summary`).pipe(
      catchError(error => {
        console.error('Error fetching compliance summary:', error);
        return of({
          total_rules: 0,
          active_rules: 0,
          total_contracts_evaluated: 0,
          overall_pass_rate: 0,
          rules_summary: []
        });
      })
    );
  }

  /**
   * Get all rules with stale results
   */
  getStaleRules(): Observable<StaleRule[]> {
    return this.http.get<StaleRule[]>(`${this.apiUrl}/stale-rules`).pipe(
      catchError(error => {
        console.error('Error fetching stale rules:', error);
        return of([]);
      })
    );
  }

  // ============================================================================
  // JOB TRACKING OPERATIONS
  // ============================================================================

  /**
   * Get evaluation job status
   */
  getJob(jobId: string): Observable<EvaluationJob | null> {
    return this.http.get<any>(`${this.apiUrl}/jobs/${jobId}`).pipe(
      map(response => {
        if (!response) return null;

        // Ensure rule_ids, contract_ids, and result_ids are arrays
        const job = response.job || response;
        if (job) {
          job.rule_ids = Array.isArray(job.rule_ids) ? job.rule_ids : [];
          job.contract_ids = Array.isArray(job.contract_ids) ? job.contract_ids : [];
          job.result_ids = Array.isArray(job.result_ids) ? job.result_ids : [];
        }
        return job;
      }),
      catchError(error => {
        console.error(`Error fetching job ${jobId}:`, error);
        return of(null);
      })
    );
  }

  /**
   * Cancel a running evaluation job
   */
  cancelJob(jobId: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/jobs/${jobId}`).pipe(
      catchError(error => {
        console.error(`Error canceling job ${jobId}:`, error);
        throw error;
      })
    );
  }

  /**
   * List evaluation jobs with optional filtering
   */
  getJobs(
    status?: string,
    jobType?: string,
    limit: number = 50
  ): Observable<EvaluationJob[]> {
    let params = new HttpParams();
    params = params.set('limit', limit.toString());

    if (status) {
      params = params.set('status', status);
    }
    if (jobType) {
      params = params.set('job_type', jobType);
    }

    return this.http.get<any>(`${this.apiUrl}/jobs`, { params }).pipe(
      map(response => {
        // Handle both array response and object with jobs property
        let jobs: any[];
        if (Array.isArray(response)) {
          jobs = response;
        } else if (response && Array.isArray(response.jobs)) {
          jobs = response.jobs;
        } else {
          console.warn('Unexpected jobs response format:', response);
          return [];
        }

        // Ensure each job has array properties
        return jobs.map(job => {
          if (job) {
            job.rule_ids = Array.isArray(job.rule_ids) ? job.rule_ids : [];
            job.contract_ids = Array.isArray(job.contract_ids) ? job.contract_ids : [];
            job.result_ids = Array.isArray(job.result_ids) ? job.result_ids : [];
          }
          return job;
        });
      }),
      catchError(error => {
        console.error('Error fetching jobs:', error);
        return of([]);
      })
    );
  }

  // ============================================================================
  // CATEGORY OPERATIONS
  // ============================================================================

  /**
   * Get all compliance rule categories
   */
  getCategories(): Observable<Category[]> {
    return this.http.get<{ categories: Category[] }>(`${this.apiUrl}/categories`).pipe(
      map(response => response.categories || []),
      catchError(error => {
        console.error('Error fetching categories:', error);
        return of([]);
      })
    );
  }

  /**
   * Create or validate a new category
   */
  createCategory(category: CategoryRequest): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/categories`, category).pipe(
      catchError(error => {
        console.error('Error creating category:', error);
        throw error;
      })
    );
  }

  // ============================================================================
  // HELPER METHODS
  // ============================================================================

  /**
   * Poll job status until completion
   * Returns observable that emits job status updates
   */
  pollJobStatus(jobId: string, intervalMs: number = 2000): Observable<EvaluationJob | null> {
    return new Observable(observer => {
      const poll = () => {
        this.getJob(jobId).subscribe({
          next: (job) => {
            if (!job) {
              observer.error('Job not found');
              return;
            }

            observer.next(job);

            // Check if job is complete
            if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
              observer.complete();
            } else {
              // Continue polling
              setTimeout(poll, intervalMs);
            }
          },
          error: (error) => {
            observer.error(error);
          }
        });
      };

      // Start polling
      poll();
    });
  }

  /**
   * Get statistics for a specific rule
   */
  getRuleStatistics(ruleId: string): Observable<any> {
    return this.getRuleResults(ruleId).pipe(
      map(results => ({
        rule_id: ruleId,
        rule_name: results.rule_name,
        total_evaluated: results.summary.total,
        pass_count: results.summary.pass,
        fail_count: results.summary.fail,
        partial_count: results.summary.partial,
        not_applicable_count: results.summary.not_applicable,
        pass_rate: results.summary.total > 0
          ? (results.summary.pass / results.summary.total) * 100
          : 0
      }))
    );
  }

  /**
   * Get active rules count
   */
  getActiveRulesCount(): Observable<number> {
    return this.getRules(true).pipe(
      map(rules => rules.length)
    );
  }

  /**
   * Check if any rules have stale results
   */
  hasStaleResults(): Observable<boolean> {
    return this.getStaleRules().pipe(
      map(staleRules => staleRules.length > 0)
    );
  }

  // ============================================================================
  // CONTRACT OPERATIONS
  // ============================================================================

  /**
   * Get contracts from the Contracts collection
   * Note: This calls a separate contracts API endpoint
   */
  getContracts(): Observable<any[]> {
    // TODO: Update this URL to match your actual contracts API endpoint
    // For now, using a placeholder that should work with the existing backend
    return this.http.get<any[]>('https://localhost:8000/api/contracts').pipe(
      catchError(error => {
        console.error('Error fetching contracts:', error);
        return of([]);
      })
    );
  }
}
