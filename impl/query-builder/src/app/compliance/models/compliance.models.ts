// Compliance Models

/**
 * Severity levels for compliance rules
 */
export type RuleSeverity = 'critical' | 'high' | 'medium' | 'low';

/**
 * Evaluation result types
 */
export type EvaluationResult = 'pass' | 'fail' | 'partial' | 'not_applicable';

/**
 * Job status types
 */
export type JobStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

/**
 * Compliance Rule model
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
 * Request model for creating/updating a rule
 */
export interface ComplianceRuleRequest {
  name: string;
  description: string;
  severity: RuleSeverity;
  category: string;
  active: boolean;
  rule_set_ids?: string[];
}

/**
 * Compliance evaluation result for a specific contract/rule combination
 */
export interface ComplianceResult {
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
  evaluated_date: string;
}

/**
 * Summary statistics for results
 */
export interface ResultSummary {
  total: number;
  pass: number;
  fail: number;
  partial: number;
  not_applicable: number;
}

/**
 * Contract evaluation results with summary
 */
export interface ContractEvaluationResults {
  contract_id: string;
  results: ComplianceResult[];
  summary: ResultSummary;
}

/**
 * Rule evaluation results with summary
 */
export interface RuleEvaluationResults {
  rule_id: string;
  rule_name: string;
  results: ComplianceResult[];
  summary: ResultSummary & { rule_name: string };
}

/**
 * Per-rule summary for dashboard
 */
export interface RuleSummary {
  rule_id: string;
  rule_name: string;
  severity: RuleSeverity;
  category: string;
  total_evaluated: number;
  pass_count: number;
  fail_count: number;
  partial_count: number;
  not_applicable_count: number;
  pass_rate: number;
  stale_count: number;
  last_evaluated: string | null;
}

/**
 * Overall compliance dashboard summary
 */
export interface ComplianceSummary {
  total_rules: number;
  active_rules: number;
  total_contracts_evaluated: number;
  overall_pass_rate: number;
  rules_summary: RuleSummary[];
}

/**
 * Stale rule information
 */
export interface StaleRule {
  rule_id: string;
  rule_name: string;
  stale_result_count: number;
  last_updated: string;
}

/**
 * Evaluation job tracking
 */
export interface EvaluationJob {
  id: string;
  job_type: string;
  status: JobStatus;
  total_items: number;
  completed_items: number;
  failed_items: number;
  progress_percentage: number;
  started_date: string;
  completed_date: string | null;
  error_message: string | null;
  contract_id: string | null;
  rule_ids: string[];
  contract_ids: string[];
  result_ids: string[];
}

/**
 * Request to evaluate a contract
 * Note: contract_text is fetched from Contracts collection by backend
 */
export interface EvaluateContractRequest {
  contract_id: string;
  rule_set_id?: string;
  rule_ids?: string[];
  async_mode?: boolean;
}

/**
 * Response from contract evaluation
 */
export interface EvaluateContractResponse {
  job_id: string | null;
  results: ComplianceResult[];
  summary: ResultSummary;
}

/**
 * Request to evaluate a rule against contracts
 */
export interface EvaluateRuleRequest {
  rule_id: string;
  contract_ids?: string[];
}

/**
 * Response from rule evaluation
 */
export interface EvaluateRuleResponse {
  job_id: string;
  message: string;
}

/**
 * Batch evaluation request
 */
export interface BatchEvaluateRequest {
  contract_ids: string[];
  rule_ids?: string[];
}

/**
 * Batch evaluation response
 */
export interface BatchEvaluateResponse {
  job_id: string;
  message: string;
}

/**
 * Category model (matches backend response)
 */
export interface Category {
  name: string;           // Category ID (e.g., "compliance")
  display_name: string;   // Display name (e.g., "Compliance")
  description: string;    // Category description
  rule_count?: number;    // Optional: number of rules in this category
}

/**
 * Request to create a new category
 */
export interface CategoryRequest {
  id: string;
  name: string;
  description: string;
}

/**
 * Predefined categories (fallback - matches backend format)
 */
export const PREDEFINED_CATEGORIES: Category[] = [
  {
    name: 'payment_terms',
    display_name: 'Payment Terms',
    description: 'Rules related to payment schedules, terms, and conditions'
  },
  {
    name: 'confidentiality',
    display_name: 'Confidentiality',
    description: 'Rules related to confidentiality and non-disclosure'
  },
  {
    name: 'data_protection',
    display_name: 'Data Protection',
    description: 'Rules related to data privacy, GDPR, CCPA compliance'
  },
  {
    name: 'liability',
    display_name: 'Liability',
    description: 'Rules related to limitation of liability, indemnification'
  },
  {
    name: 'termination',
    display_name: 'Termination',
    description: 'Rules related to contract termination and renewal'
  },
  {
    name: 'insurance',
    display_name: 'Insurance',
    description: 'Rules related to insurance requirements and coverage'
  },
  {
    name: 'governing_law',
    display_name: 'Governing Law',
    description: 'Rules related to governing law and jurisdiction'
  },
  {
    name: 'dispute_resolution',
    display_name: 'Dispute Resolution',
    description: 'Rules related to arbitration, mediation, and dispute resolution'
  },
  {
    name: 'intellectual_property',
    display_name: 'Intellectual Property',
    description: 'Rules related to IP ownership and licensing'
  },
  {
    name: 'compliance',
    display_name: 'Compliance',
    description: 'Rules related to regulatory compliance and audit rights'
  },
  {
    name: 'force_majeure',
    display_name: 'Force Majeure',
    description: 'Rules related to force majeure events'
  },
  {
    name: 'service_level',
    display_name: 'Service Level',
    description: 'Rules related to SLAs and performance guarantees'
  },
  {
    name: 'general_terms',
    display_name: 'General Terms',
    description: 'Rules related to assignment, subcontracting, and general provisions'
  },
  {
    name: 'warranties',
    display_name: 'Warranties',
    description: 'Rules related to warranties and disclaimers'
  },
  {
    name: 'testing',
    display_name: 'Testing',
    description: 'Test rules for development and validation'
  }
];

/**
 * Severity options with display labels
 */
export const SEVERITY_OPTIONS: { value: RuleSeverity; label: string; color: string }[] = [
  { value: 'critical', label: 'Critical', color: 'danger' },
  { value: 'high', label: 'High', color: 'warning' },
  { value: 'medium', label: 'Medium', color: 'info' },
  { value: 'low', label: 'Low', color: 'secondary' }
];

/**
 * Result status options with display labels
 */
export const RESULT_OPTIONS: { value: EvaluationResult; label: string; color: string }[] = [
  { value: 'pass', label: 'Pass', color: 'success' },
  { value: 'fail', label: 'Fail', color: 'danger' },
  { value: 'partial', label: 'Partial', color: 'warning' },
  { value: 'not_applicable', label: 'N/A', color: 'secondary' }
];

/**
 * Helper function to get severity color class
 */
export function getSeverityColor(severity: RuleSeverity): string {
  const option = SEVERITY_OPTIONS.find(s => s.value === severity);
  return option ? option.color : 'secondary';
}

/**
 * Helper function to get result color class
 */
export function getResultColor(result: EvaluationResult): string {
  const option = RESULT_OPTIONS.find(r => r.value === result);
  return option ? option.color : 'secondary';
}

/**
 * Helper function to format date for display in browser's local timezone
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) return 'Never';

  try {
    // Normalize the timestamp to ensure it's treated as UTC
    let utcTimestamp = dateString.trim();

    // Handle various timestamp formats
    if (!utcTimestamp.endsWith('Z') && !utcTimestamp.includes('+') && !utcTimestamp.includes('-', 10)) {
      // Format: "2025-01-15 10:30:00" or "2025-01-15T10:30:00" - add Z to indicate UTC
      if (!utcTimestamp.includes('T')) {
        utcTimestamp = utcTimestamp.replace(' ', 'T');
      }
      utcTimestamp += 'Z';
    }

    // Parse UTC timestamp - the Date constructor will convert to local time
    const date = new Date(utcTimestamp);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.error('Invalid timestamp:', dateString);
      return 'Invalid date';
    }

    // Format in browser's local timezone with explicit timezone display
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZoneName: 'short'
    });
  } catch (error) {
    console.error('Error formatting timestamp:', dateString, error);
    return 'Invalid date';
  }
}

/**
 * Helper function to calculate pass rate percentage
 */
export function calculatePassRate(summary: ResultSummary): number {
  if (summary.total === 0) return 0;
  return Math.round((summary.pass / summary.total) * 100);
}

// ============================================================================
// RULE SET MODELS
// ============================================================================

/**
 * Rule Set model - collection of compliance rules
 */
export interface RuleSet {
  id: string;
  doctype: string;
  name: string;
  description: string | null;
  suggested_contract_types: string[];
  rule_ids: string[];
  is_active: boolean;
  created_date: string;
  modified_date: string;
  created_by: string;
}

/**
 * Request model for creating a new rule set
 */
export interface RuleSetCreate {
  name: string;
  description?: string | null;
  suggested_contract_types?: string[];
  rule_ids?: string[];
  is_active?: boolean;
}

/**
 * Request model for updating a rule set
 */
export interface RuleSetUpdate {
  name?: string;
  description?: string | null;
  suggested_contract_types?: string[];
  rule_ids?: string[];
  is_active?: boolean;
}

/**
 * Rule set with rule count
 */
export interface RuleSetWithRuleCount extends RuleSet {
  rule_count: number;
}

/**
 * Response from listing rule sets
 */
export interface RuleSetListResponse {
  rule_sets: RuleSet[];
  total: number;
}

/**
 * Request to add rules to a rule set
 */
export interface AddRulesToSetRequest {
  rule_ids: string[];
}

/**
 * Request to remove rules from a rule set
 */
export interface RemoveRulesFromSetRequest {
  rule_ids: string[];
}

/**
 * Request to clone a rule set
 */
export interface CloneRuleSetRequest {
  new_name: string;
  clone_rules?: boolean;
}
