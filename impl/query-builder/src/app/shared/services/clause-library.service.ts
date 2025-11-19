import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

// Data models matching backend schemas
export interface ClauseContent {
  html: string;
  plain_text: string;
  word_compatible_xml?: string;
}

export interface ClauseVariable {
  name: string;
  type: 'system' | 'custom';
  default_value: string;
  description: string;
}

export interface ClauseMetadata {
  tags: string[];
  contract_types: string[];
  jurisdictions: string[];
  risk_level: 'low' | 'medium' | 'high';
  complexity: 'low' | 'medium' | 'high';
}

export interface ClauseVersion {
  version_number: number;
  version_label: string;
  is_current: boolean;
  parent_version_id?: string;
  created_by: string;
  created_date: string;
  change_notes?: string;
}

export interface ClauseUsageStats {
  times_used: number;
  last_used_date?: string;
  average_comparison_score?: number;
}

export interface ClauseAudit {
  created_by: string;
  created_date: string;
  modified_by: string;
  modified_date: string;
}

export interface Clause {
  id: string;
  type: 'clause';
  name: string;
  description: string;
  category_id: string;
  category_path: string[];
  category_path_display: string;
  content: ClauseContent;
  variables: ClauseVariable[];
  metadata: ClauseMetadata;
  version: ClauseVersion;
  usage_stats: ClauseUsageStats;
  embedding?: number[];
  audit: ClauseAudit;
  status: 'active' | 'archived' | 'draft';
}

export interface Category {
  id: string;
  type: 'category';
  name: string;
  description: string;
  parent_id: string | null;
  path: string[];
  display_path: string;  // Changed from path_display to match API
  level: number;
  order?: number;  // Added to match API response
  icon?: string;  // Added to match API response
  is_predefined?: boolean;  // Added to match API response
  clause_count: number;
  subcategories?: string[];  // Made optional
  metadata?: {  // Made optional to match API
    icon?: string;
    color?: string;
    sort_order: number;
  };
  audit: ClauseAudit | null;  // Made nullable to match API
  status?: 'active' | 'inactive';  // Made optional
}

export interface ClauseComparisonResult {
  clause_id: string;
  clause_name: string;
  contract_clause_text: string;
  library_clause_text: string;
  similarity_score: number;
  differences: Array<{
    type: 'addition' | 'deletion' | 'modification';
    location: string;
    description: string;
    severity: 'minor' | 'moderate' | 'major';
  }>;
  risk_analysis: {
    overall_risk: 'low' | 'medium' | 'high';
    risk_factors: Array<{
      factor: string;
      description: string;
      severity: 'low' | 'medium' | 'high';
    }>;
  };
  recommendations: Array<{
    action: string;
    description: string;
    priority: 'low' | 'medium' | 'high';
    suggested_text?: string;
  }>;
}

export interface ClauseSuggestion {
  clause_id: string;
  clause_name: string;
  similarity_score: number;
  reason: string;
  clause_preview: string;
}

@Injectable({
  providedIn: 'root'
})
export class ClauseLibraryService {
  private apiUrl = 'https://localhost:8000';

  constructor(private http: HttpClient) {}

  // ========== Clause CRUD Operations ==========

  /**
   * Get all clauses with optional filters
   */
  getClauses(filters?: {
    category_id?: string;
    search?: string;
    status?: string;
    tags?: string[];
    risk_level?: string;
    contract_types?: string[];
    limit?: number;
    offset?: number;
  }): Observable<{ clauses: Clause[]; total: number }> {
    let params = new HttpParams();

    if (filters) {
      if (filters.category_id) params = params.set('category_id', filters.category_id);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.status) params = params.set('status', filters.status);
      if (filters.risk_level) params = params.set('risk_level', filters.risk_level);
      if (filters.limit) params = params.set('limit', filters.limit.toString());
      if (filters.offset) params = params.set('offset', filters.offset.toString());
      if (filters.tags && filters.tags.length > 0) {
        params = params.set('tags', filters.tags.join(','));
      }
      if (filters.contract_types && filters.contract_types.length > 0) {
        params = params.set('contract_types', filters.contract_types.join(','));
      }
    }

    return this.http.get<{ clauses: Clause[]; total_count: number }>(
      `${this.apiUrl}/api/clause-library/clauses`,
      { params }
    ).pipe(
      map(response => ({
        clauses: response.clauses,
        total: response.total_count
      }))
    );
  }

  /**
   * Get a single clause by ID
   */
  getClause(clauseId: string): Observable<Clause> {
    return this.http.get<Clause>(`${this.apiUrl}/api/clause-library/clauses/${clauseId}`);
  }

  /**
   * Create a new clause
   */
  createClause(clause: Partial<Clause>): Observable<{ success: boolean; clause_id: string; message: string }> {
    return this.http.post<{ success: boolean; clause_id: string; message: string }>(
      `${this.apiUrl}/api/clause-library/clauses`,
      clause
    );
  }

  /**
   * Update an existing clause
   */
  updateClause(clauseId: string, updates: Partial<Clause>): Observable<{ success: boolean; message: string }> {
    return this.http.put<{ success: boolean; message: string }>(
      `${this.apiUrl}/api/clause-library/clauses/${clauseId}`,
      updates
    );
  }

  /**
   * Delete a clause
   */
  deleteClause(clauseId: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(
      `${this.apiUrl}/api/clause-library/clauses/${clauseId}`
    );
  }

  // ========== Category Operations ==========

  /**
   * Get all categories
   */
  getCategories(): Observable<{ categories: Category[] }> {
    return this.http.get<Category[]>(
      `${this.apiUrl}/api/clause-library/categories`
    ).pipe(
      map(categories => ({ categories }))
    );
  }

  /**
   * Get a single category by ID
   */
  getCategory(categoryId: string): Observable<Category> {
    return this.http.get<Category>(
      `${this.apiUrl}/api/clause-library/categories/${categoryId}`
    );
  }

  /**
   * Create a new category
   */
  createCategory(category: Partial<Category>): Observable<{ success: boolean; category_id: string; message: string }> {
    return this.http.post<{ success: boolean; category_id: string; message: string }>(
      `${this.apiUrl}/api/clause-library/categories`,
      category
    );
  }

  /**
   * Update a category
   */
  updateCategory(categoryId: string, updates: Partial<Category>): Observable<{ success: boolean; message: string }> {
    return this.http.put<{ success: boolean; message: string }>(
      `${this.apiUrl}/api/clause-library/categories/${categoryId}`,
      updates
    );
  }

  /**
   * Delete a category
   */
  deleteCategory(categoryId: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(
      `${this.apiUrl}/api/clause-library/categories/${categoryId}`
    );
  }

  // ========== AI Comparison Operations ==========

  /**
   * Compare contract clause with library clause
   */
  compareClause(
    contractClauseText: string,
    libraryClauseId: string,
    modelSelection: 'primary' | 'secondary' = 'primary',
    userEmail: string = 'system'
  ): Observable<ClauseComparisonResult> {
    return this.http.post<ClauseComparisonResult>(
      `${this.apiUrl}/api/clause-library/compare`,
      {
        contract_clause_text: contractClauseText,
        library_clause_id: libraryClauseId,
        model_selection: modelSelection,
        user_email: userEmail
      }
    );
  }

  /**
   * Get AI-powered clause suggestions based on text
   */
  getSuggestions(
    text: string,
    topN: number = 5,
    categoryId?: string
  ): Observable<{ suggestions: ClauseSuggestion[] }> {
    let params = new HttpParams()
      .set('text', text)
      .set('top_n', topN.toString());

    if (categoryId) {
      params = params.set('category_id', categoryId);
    }

    return this.http.get<{ suggestions: ClauseSuggestion[] }>(
      `${this.apiUrl}/api/clause-library/suggest`,
      { params }
    );
  }

  // ========== Variable Operations ==========

  /**
   * Get system variables
   */
  getSystemVariables(): Observable<{ variables: ClauseVariable[] }> {
    return this.http.get<{ variables: ClauseVariable[] }>(
      `${this.apiUrl}/api/clause-library/variables`
    );
  }

  /**
   * Get custom variables for a clause
   */
  getClauseVariables(clauseId: string): Observable<{ variables: ClauseVariable[] }> {
    return this.http.get<{ variables: ClauseVariable[] }>(
      `${this.apiUrl}/api/clause-library/clauses/${clauseId}/variables`
    );
  }

  // ========== Version Operations ==========

  /**
   * Get version history for a clause
   */
  getVersionHistory(clauseId: string): Observable<{ versions: Clause[] }> {
    return this.http.get<Clause[]>(
      `${this.apiUrl}/api/clause-library/clauses/${clauseId}/versions`
    ).pipe(
      map(versions => ({ versions }))
    );
  }

  /**
   * Create new version of a clause
   */
  createVersion(
    clauseId: string,
    changeNotes: string
  ): Observable<Clause> {
    return this.http.post<Clause>(
      `${this.apiUrl}/api/clause-library/clauses/${clauseId}/versions`,
      {
        change_notes: changeNotes
      }
    );
  }

  // ========== Utility Methods ==========

  /**
   * Search clauses by text
   */
  searchClauses(query: string, limit: number = 20): Observable<{ clauses: Clause[]; total: number }> {
    return this.getClauses({ search: query, limit });
  }

  /**
   * Get clauses by category
   */
  getClausesByCategory(categoryId: string, limit: number = 100): Observable<{ clauses: Clause[]; total: number }> {
    return this.getClauses({ category_id: categoryId, limit });
  }
}
