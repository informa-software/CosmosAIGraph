/**
 * API Service for backend communication
 * Handles HTTP requests to the Python FastAPI backend
 */

import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, firstValueFrom } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

import {
  RuleSet,
  RuleSetWithCount,
  RuleSetListResponse,
  ComplianceRule,
  EvaluateContractRequest,
  EvaluateContractResponse,
  EvaluationJob,
  ComplianceResultData,
  ContractEvaluationResults
} from '../models/compliance.models';

import {
  TrackChangesComparisonRequest,
  TrackChangesComparisonResponse
} from '../models/track-changes.models';

import {
  WordAddinEvaluationSession,
  CreateSessionRequest,
  UpdateSessionRequest
} from '../word-addin/models/session.models';

import {
  Contract,
  ContractListResponse,
  ClauseType,
  CompareWithStandardRequest,
  CompareWithOriginalRequest,
  ComparisonResponse
} from '../models/comparison.models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  // Backend API base URL - configurable via environment
  private readonly API_BASE_URL = 'https://localhost:8000';

  private readonly httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json'
    })
  };

  constructor(private http: HttpClient) {}

  // ============================================================================
  // Rule Sets
  // ============================================================================

  /**
   * Get all rule sets
   */
  async getRuleSets(): Promise<RuleSetListResponse> {
    const url = `${this.API_BASE_URL}/api/rule_sets`;
    return firstValueFrom(
      this.http.get<RuleSetListResponse>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Get rule sets with rule counts
   */
  async getRuleSetsWithCounts(): Promise<RuleSetWithCount[]> {
    const url = `${this.API_BASE_URL}/api/rule_sets/with-counts`;
    return firstValueFrom(
      this.http.get<RuleSetWithCount[]>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Get a specific rule set by ID
   */
  async getRuleSet(ruleSetId: string): Promise<RuleSet> {
    const url = `${this.API_BASE_URL}/api/rule_sets/${ruleSetId}`;
    return firstValueFrom(
      this.http.get<RuleSet>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Get rule IDs in a rule set
   */
  async getRuleSetRules(ruleSetId: string): Promise<string[]> {
    const url = `${this.API_BASE_URL}/api/rule_sets/${ruleSetId}/rules`;
    return firstValueFrom(
      this.http.get<string[]>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  // ============================================================================
  // Compliance Rules
  // ============================================================================

  /**
   * Get all compliance rules
   */
  async getRules(categoryFilter?: string, activeOnly: boolean = true): Promise<ComplianceRule[]> {
    let url = `${this.API_BASE_URL}/api/compliance/rules?active=${activeOnly}`;
    if (categoryFilter) {
      url += `&category=${categoryFilter}`;
    }
    return firstValueFrom(
      this.http.get<ComplianceRule[]>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Get a specific rule by ID
   */
  async getRule(ruleId: string): Promise<ComplianceRule> {
    const url = `${this.API_BASE_URL}/api/compliance/rules/${ruleId}`;
    return firstValueFrom(
      this.http.get<ComplianceRule>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  // ============================================================================
  // Contract Evaluation
  // ============================================================================

  /**
   * Submit a contract for compliance evaluation
   */
  async evaluateContract(request: EvaluateContractRequest): Promise<EvaluateContractResponse> {
    const url = `${this.API_BASE_URL}/api/compliance/evaluate/contract/${request.contract_id}`;
    return firstValueFrom(
      this.http.post<EvaluateContractResponse>(url, request, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  /**
   * Get evaluation job status
   */
  async getJob(jobId: string): Promise<EvaluationJob> {
    const url = `${this.API_BASE_URL}/api/compliance/jobs/${jobId}`;
    return firstValueFrom(
      this.http.get<EvaluationJob>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Get evaluation results for a contract
   */
  async getContractResults(contractId: string, ruleId?: string): Promise<ContractEvaluationResults> {
    let url = `${this.API_BASE_URL}/api/compliance/results/contract/${contractId}`;
    if (ruleId) {
      url += `?rule_id=${ruleId}`;
    }
    return firstValueFrom(
      this.http.get<ContractEvaluationResults>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Poll job status until completion
   * @param jobId Job ID to poll
   * @param intervalMs Polling interval in milliseconds (default: 1000)
   * @param maxAttempts Maximum polling attempts (default: 60)
   */
  async pollJobCompletion(
    jobId: string,
    intervalMs: number = 1000,
    maxAttempts: number = 60
  ): Promise<EvaluationJob> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const job = await this.getJob(jobId);

      // Check if job is complete
      if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        return job;
      }

      // Wait before next poll
      await this.delay(intervalMs);
    }

    throw new Error(`Job ${jobId} did not complete within ${maxAttempts} attempts`);
  }

  // ============================================================================
  // Track Changes Comparison
  // ============================================================================

  /**
   * Compare original and revised text from track changes
   * Uses the inline text mode of the compare-contracts endpoint
   */
  async compareTrackChanges(originalText: string, revisedText: string): Promise<TrackChangesComparisonResponse> {
    const url = `${this.API_BASE_URL}/api/compare-contracts`;
    const request: TrackChangesComparisonRequest = {
      originalText,
      revisedText,
      comparisonMode: 'full'
    };
    return firstValueFrom(
      this.http.post<TrackChangesComparisonResponse>(url, request, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  // ============================================================================
  // Contract Comparison
  // ============================================================================

  /**
   * Get all contracts for selection in dropdown
   */
  async getContracts(): Promise<Contract[]> {
    const url = `${this.API_BASE_URL}/api/contracts`;
    const response = await firstValueFrom(
      this.http.get<ContractListResponse>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
    return response.contracts;
  }

  /**
   * Get clauses available in a standard contract
   */
  async getContractClauses(contractId: string): Promise<ClauseType[]> {
    const url = `${this.API_BASE_URL}/api/contracts/${contractId}/clauses`;
    return firstValueFrom(
      this.http.get<ClauseType[]>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  /**
   * Compare Word document with standard contract
   * Supports both full contract and clause-by-clause comparison
   */
  async compareWithStandard(request: CompareWithStandardRequest): Promise<ComparisonResponse> {
    const url = `${this.API_BASE_URL}/api/compare-contracts`;
    return firstValueFrom(
      this.http.post<ComparisonResponse>(url, request, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  /**
   * Compare original vs revised text (track changes mode)
   * This is an alias for compareTrackChanges for consistency
   */
  async compareWithOriginal(request: CompareWithOriginalRequest): Promise<ComparisonResponse> {
    const url = `${this.API_BASE_URL}/api/compare-contracts`;
    return firstValueFrom(
      this.http.post<ComparisonResponse>(url, request, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  // ============================================================================
  // Word Add-in Session Tracking
  // ============================================================================

  /**
   * Create a new evaluation session
   */
  async createSession(request: CreateSessionRequest): Promise<WordAddinEvaluationSession> {
    const url = `${this.API_BASE_URL}/api/word-addin/sessions`;
    return firstValueFrom(
      this.http.post<WordAddinEvaluationSession>(url, request, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  /**
   * Update an existing evaluation session
   */
  async updateSession(evaluationId: string, update: UpdateSessionRequest): Promise<WordAddinEvaluationSession> {
    const url = `${this.API_BASE_URL}/api/word-addin/sessions/${evaluationId}`;
    return firstValueFrom(
      this.http.patch<WordAddinEvaluationSession>(url, update, this.httpOptions)
        .pipe(catchError(this.handleError))
    );
  }

  /**
   * Get a specific evaluation session
   */
  async getSession(evaluationId: string): Promise<WordAddinEvaluationSession> {
    const url = `${this.API_BASE_URL}/api/word-addin/sessions/${evaluationId}`;
    return firstValueFrom(
      this.http.get<WordAddinEvaluationSession>(url)
        .pipe(retry(2), catchError(this.handleError))
    );
  }

  // ============================================================================
  // Utility Methods
  // ============================================================================

  /**
   * Delay helper for polling
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side or network error
      errorMessage = `Client Error: ${error.error.message}`;
    } else {
      // Backend error
      errorMessage = `Server Error (${error.status}): ${error.message}`;

      // Try to extract more detailed error from backend
      if (error.error && typeof error.error === 'object') {
        if (error.error.detail) {
          errorMessage = error.error.detail;
        } else if (error.error.message) {
          errorMessage = error.error.message;
        }
      }
    }

    console.error('API Error:', errorMessage, error);
    return throwError(() => new Error(errorMessage));
  }
}
