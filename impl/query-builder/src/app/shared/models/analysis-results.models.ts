/**
 * TypeScript models for Analysis Results
 *
 * These models match the backend Pydantic models for storing and retrieving
 * analysis results (comparisons and queries) with PDF generation support.
 */

// ============================================================================
// Common Models
// ============================================================================

export interface AnalysisMetadata {
  title: string;
  description?: string;
  execution_time_seconds?: number;
}

export interface PDFMetadata {
  generated_at: string; // ISO datetime
  file_size_bytes: number;
  page_count?: number;
  blob_url?: string;
}

// ============================================================================
// Comparison-Specific Models
// ============================================================================

export interface ComparisonData {
  standard_contract_id: string;
  compare_contract_ids: string[];
  comparison_mode: 'full' | 'clauses';
  selected_clauses?: string[];
  results: any; // Full comparison response
}

export interface SaveComparisonRequest {
  user_id: string;
  standard_contract_id: string;
  compare_contract_ids: string[];
  comparison_mode: 'full' | 'clauses';
  selected_clauses?: string[];
  results: any;
  metadata?: AnalysisMetadata;
}

// ============================================================================
// Query-Specific Models
// ============================================================================

export interface ContractQueried {
  contract_id: string;
  filename: string;
  contract_title?: string;
}

export interface QueryData {
  query_text: string;
  query_type: string;
  contracts_queried: ContractQueried[];
  results: any;
}

export interface SaveQueryRequest {
  user_id: string;
  query_text: string;
  query_type: string;
  contracts_queried: ContractQueried[];
  results: any;
  metadata?: AnalysisMetadata;
}

// ============================================================================
// Main Storage Model
// ============================================================================

export interface AnalysisResult {
  id: string;
  result_id: string;
  result_type: 'comparison' | 'query';
  user_id: string;
  created_at: string; // ISO datetime
  status: 'completed' | 'in_progress' | 'failed';
  metadata: AnalysisMetadata;
  comparison_data?: ComparisonData;
  query_data?: QueryData;
  pdf_metadata?: PDFMetadata;
}

// ============================================================================
// API Response Models
// ============================================================================

export interface SaveResultResponse {
  result_id: string;
  message: string;
}

export interface ResultListResponse {
  results: AnalysisResult[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface UserStatistics {
  total_results: number;
  by_type: {
    comparison?: number;
    query?: number;
  };
  last_30_days: number;
}

export interface EmailPDFRequest {
  recipients: string[];
  subject?: string;
  message?: string;
}
