/**
 * TypeScript models for compliance evaluation system
 * These match the backend Pydantic models
 */

export type RuleSeverity = 'critical' | 'high' | 'medium' | 'low';

export type EvaluationResult = 'pass' | 'fail' | 'partial' | 'not_applicable';

export type JobStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

export type JobType = 'evaluate_contract' | 'evaluate_rule' | 'reevaluate_stale' | 'batch_evaluate';

/**
 * Compliance rule model
 */
export interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  severity: RuleSeverity;
  category: string;
  active: boolean;
  rule_set_ids: string[];
  created_date: string;
  updated_date: string;
  created_by: string;
}

/**
 * Rule set model
 */
export interface RuleSet {
  id: string;
  doctype: string;
  name: string;
  description?: string;
  suggested_contract_types?: string[];
  rule_ids: string[];
  is_active: boolean;
  created_date: string;
  modified_date: string;
  created_by: string;
}

/**
 * Rule set with rule count
 */
export interface RuleSetWithCount extends RuleSet {
  rule_count: number;
}

/**
 * AI-generated recommendation for fixing a failed/partial compliance rule
 */
export interface RecommendationData {
  original_text: string;
  proposed_text: string;
  explanation: string;
  location_context: string;
  confidence: number;
}

/**
 * Compliance evaluation result
 */
export interface ComplianceResultData {
  id: string;
  contract_id: string;
  rule_id: string;
  rule_name: string;
  rule_description: string;
  rule_version_date: string;
  evaluation_result: EvaluationResult;
  confidence: number;
  explanation: string;
  evidence: string[];
  recommendation?: RecommendationData;
  evaluated_by: string;
  evaluated_date: string;
}

/**
 * Evaluation job model
 */
export interface EvaluationJob {
  id: string;
  job_type: JobType;
  status: JobStatus;
  progress: number;
  total_items: number;
  completed_items: number;
  failed_items: number;
  contract_id?: string;
  rule_ids: string[];
  contract_ids: string[];
  started_date: string;
  completed_date?: string;
  error_message?: string;
  result_ids: string[];
}

/**
 * Request to evaluate a contract
 */
export interface EvaluateContractRequest {
  contract_id: string;
  contract_text?: string;
  rule_set_id?: string;
  rule_ids?: string[];
  async_mode: boolean;
}

/**
 * API response for evaluate contract endpoint
 */
export interface EvaluateContractResponse {
  job_id?: string;
  message: string;
  results?: ComplianceResultData[];
}

/**
 * Rule set list response
 */
export interface RuleSetListResponse {
  rule_sets: RuleSet[];
  total: number;
}

/**
 * Category model
 */
export interface Category {
  name: string;
  display_name: string;
  description?: string;
}

/**
 * Summary statistics for evaluation results
 */
export interface EvaluationSummary {
  total_results: number;
  pass_count: number;
  fail_count: number;
  partial_count: number;
  not_applicable_count: number;
  average_confidence: number;
  by_severity: Record<RuleSeverity, {
    pass: number;
    fail: number;
    partial: number;
    not_applicable: number;
  }>;
}

/**
 * Contract evaluation results response from API
 */
export interface ContractEvaluationResults {
  contract_id: string;
  results: ComplianceResultData[];
  summary: {
    total: number;
    pass: number;
    fail: number;
    partial: number;
    not_applicable: number;
  };
}
