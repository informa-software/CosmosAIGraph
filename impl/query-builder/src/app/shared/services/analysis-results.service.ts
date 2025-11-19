import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import {
  AnalysisResult,
  SaveComparisonRequest,
  SaveQueryRequest,
  SaveResultResponse,
  ResultListResponse,
  UserStatistics,
  EmailPDFRequest
} from '../models/analysis-results.models';

@Injectable({
  providedIn: 'root'
})
export class AnalysisResultsService {
  private baseUrl = 'https://localhost:8000/api/analysis-results';

  constructor(private http: HttpClient) {}

  // ========================================================================
  // Save Results
  // ========================================================================

  /**
   * Save comparison results to backend
   */
  saveComparisonResult(request: SaveComparisonRequest): Observable<SaveResultResponse> {
    return this.http.post<SaveResultResponse>(`${this.baseUrl}/comparison`, request).pipe(
      catchError(error => {
        console.error('Error saving comparison result:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to save comparison results'));
      })
    );
  }

  /**
   * Save query results to backend
   */
  saveQueryResult(request: SaveQueryRequest): Observable<SaveResultResponse> {
    return this.http.post<SaveResultResponse>(`${this.baseUrl}/query`, request).pipe(
      catchError(error => {
        console.error('Error saving query result:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to save query results'));
      })
    );
  }

  // ========================================================================
  // Retrieve Results
  // ========================================================================

  /**
   * Get a specific result by ID
   */
  getResult(resultId: string, userId: string): Observable<AnalysisResult> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.get<AnalysisResult>(`${this.baseUrl}/results/${resultId}`, { params }).pipe(
      catchError(error => {
        console.error('Error fetching result:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to fetch result'));
      })
    );
  }

  /**
   * List all results for a user
   */
  listUserResults(
    userId: string,
    resultType?: 'comparison' | 'query',
    limit: number = 50,
    offset: number = 0
  ): Observable<ResultListResponse> {
    let params = new HttpParams()
      .set('result_type', resultType || '')
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    return this.http.get<ResultListResponse>(`${this.baseUrl}/user/${userId}/results`, { params }).pipe(
      catchError(error => {
        console.error('Error listing results:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to list results'));
      })
    );
  }

  /**
   * Get user statistics
   */
  getUserStatistics(userId: string): Observable<UserStatistics> {
    return this.http.get<UserStatistics>(`${this.baseUrl}/user/${userId}/statistics`).pipe(
      catchError(error => {
        console.error('Error fetching statistics:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to fetch statistics'));
      })
    );
  }

  // ========================================================================
  // PDF Generation
  // ========================================================================

  /**
   * Generate and download PDF for a result
   * Returns a Blob that can be downloaded
   */
  generatePDF(resultId: string, userId: string): Observable<Blob> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.get(`${this.baseUrl}/results/${resultId}/pdf`, {
      params,
      responseType: 'blob',
      observe: 'response'
    }).pipe(
      map(response => {
        // Return the blob from the response
        return response.body as Blob;
      }),
      catchError(error => {
        console.error('Error generating PDF:', error);
        return throwError(() => new Error('Failed to generate PDF'));
      })
    );
  }

  /**
   * Helper method to trigger PDF download in browser
   */
  downloadPDF(resultId: string, userId: string, filename?: string): void {
    this.generatePDF(resultId, userId).subscribe({
      next: (blob) => {
        // Create a download link and trigger it
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || `report_${resultId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      },
      error: (error) => {
        console.error('Error downloading PDF:', error);
        throw error;
      }
    });
  }

  // ========================================================================
  // Email (Placeholder for Phase 3)
  // ========================================================================

  /**
   * Email PDF to recipients
   * NOTE: Not yet implemented - Phase 3
   */
  emailPDF(resultId: string, request: EmailPDFRequest): Observable<any> {
    return this.http.post(`${this.baseUrl}/results/${resultId}/email`, request).pipe(
      catchError(error => {
        console.error('Error sending email:', error);
        return throwError(() => new Error(error.error?.detail || 'Email functionality not yet implemented'));
      })
    );
  }

  // ========================================================================
  // Delete
  // ========================================================================

  /**
   * Delete a result
   */
  deleteResult(resultId: string, userId: string): Observable<any> {
    const params = new HttpParams().set('user_id', userId);
    return this.http.delete(`${this.baseUrl}/results/${resultId}`, { params }).pipe(
      catchError(error => {
        console.error('Error deleting result:', error);
        return throwError(() => new Error(error.error?.detail || 'Failed to delete result'));
      })
    );
  }
}
