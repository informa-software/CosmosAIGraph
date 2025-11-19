/**
 * Models for Word Add-in evaluation session tracking
 */

export interface TrackChangesInfo {
  is_enabled: boolean;
  change_tracking_mode: 'Off' | 'TrackAll' | 'TrackMineOnly';
  changes_count?: number;
}

export interface ComparisonSummary {
  overall_similarity_score: number;
  risk_level: 'low' | 'medium' | 'high';
  critical_findings_count: number;
  missing_clauses_count: number;
  additional_clauses_count: number;
}

export interface ComplianceSummary {
  original_pass: number;
  original_fail: number;
  original_partial: number;
  revised_pass: number;
  revised_fail: number;
  revised_partial: number;
  changed_rules_count: number;
}

export interface WordAddinEvaluationSession {
  evaluation_id: string;
  session_timestamp: string;

  // Document information
  document_title?: string;
  document_character_count?: number;

  // Track changes information
  track_changes_info: TrackChangesInfo;

  // Contract identifiers
  original_contract_id: string;
  revised_contract_id: string;

  // Rule set used
  rule_set_id: string;
  rule_set_name?: string;

  // Analysis mode
  compliance_mode: 'both' | 'revised';

  // Comparison results
  comparison_completed: boolean;
  comparison_summary?: ComparisonSummary;
  comparison_error?: string;

  // Compliance evaluation results
  compliance_completed: boolean;
  original_evaluation_job_id?: string;
  revised_evaluation_job_id?: string;
  compliance_summary?: ComplianceSummary;
  compliance_error?: string;

  // Timing
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;

  // Status
  status: 'in_progress' | 'completed' | 'failed';

  // Metadata
  user_id?: string;
  client_version?: string;
}

export interface CreateSessionRequest {
  document_title?: string;
  document_character_count?: number;
  track_changes_info: TrackChangesInfo;
  original_contract_id: string;
  revised_contract_id: string;
  rule_set_id: string;
  rule_set_name?: string;
  compliance_mode: 'both' | 'revised';
  user_id?: string;
  client_version?: string;
}

export interface UpdateSessionRequest {
  comparison_completed?: boolean;
  comparison_summary?: ComparisonSummary;
  comparison_error?: string;

  compliance_completed?: boolean;
  original_evaluation_job_id?: string;
  revised_evaluation_job_id?: string;
  compliance_summary?: ComplianceSummary;
  compliance_error?: string;

  status?: 'in_progress' | 'completed' | 'failed';
}
