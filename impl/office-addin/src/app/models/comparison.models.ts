/**
 * Models for Contract Comparison functionality
 * Used for comparing contracts in both full and clause-by-clause modes
 */

export type ComparisonMode = 'full' | 'clauses';
export type RiskLevel = 'low' | 'medium' | 'high';

/**
 * Contract metadata for dropdown selection
 */
export interface Contract {
  id: string;
  title: string;
  contract_type?: string;
  file_name?: string;
}

/**
 * Contract list response from API
 */
export interface ContractListResponse {
  contracts: Contract[];
  total: number;
}

/**
 * Clause type information
 */
export interface ClauseType {
  type: string;
  display_name: string;
  description?: string;
}

/**
 * Request for comparing Word document with standard contract
 */
export interface CompareWithStandardRequest {
  standardContractId: string;
  currentDocumentText: string;
  comparisonMode: ComparisonMode;
  selectedClauses?: string[] | 'all';
  modelSelection?: 'primary' | 'secondary';
  userEmail?: string;
}

/**
 * Request for comparing original vs revised text (track changes)
 */
export interface CompareWithOriginalRequest {
  originalText: string;
  revisedText: string;
  comparisonMode: 'full';
  modelSelection?: 'primary' | 'secondary';
  userEmail?: string;
}

/**
 * Unified comparison response
 */
export interface ComparisonResponse {
  success: boolean;
  standardContractId: string;
  compareContractIds: string[];
  comparisonMode: string;
  selectedClauses?: string[] | null;
  results: ComparisonResults;
  error?: string;
}

/**
 * Comparison results container
 */
export interface ComparisonResults {
  comparisons: ContractComparison[];
}

/**
 * Individual contract comparison analysis
 */
export interface ContractComparison {
  contract_id: string;
  overall_similarity_score: number;
  risk_level: RiskLevel;
  clause_analyses?: ClauseAnalysis[];
  missing_clauses?: string[];
  additional_clauses?: string[];
  critical_findings: string[];
  summary?: string;
  error?: string;
}

/**
 * Clause-level analysis
 */
export interface ClauseAnalysis {
  clause_type: string;
  standard_clause_id: string | null;
  compared_clause_id: string | null;
  exists_in_standard: boolean;
  exists_in_compared: boolean;
  similarity_score: number;
  risk_level?: RiskLevel;
  key_differences: string[];
  risks?: string[];
  recommendations?: string[];
  summary: string;
}

/**
 * Clause library clause (for inserting missing clauses)
 */
export interface ClauseLibraryClause {
  id: string;
  clause_type: string;
  title: string;
  content: string;
  category?: string;
  tags?: string[];
}

/**
 * UI state for comparison tab
 */
export interface ComparisonState {
  mode: 'select' | 'compare-original' | 'compare-standard';
  selectedStandardContractId?: string;
  comparisonMode: ComparisonMode;
  selectedClauses: string[] | 'all';
  isLoading: boolean;
  error?: string;
  results?: ComparisonResponse;
}
