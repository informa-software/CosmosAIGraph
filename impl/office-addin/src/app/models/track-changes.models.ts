/**
 * Models for Track Changes functionality
 * Used for comparing original vs. revised contract versions
 */

export interface TrackedChangesSummary {
  isEnabled: boolean;
  changeTrackingMode: 'Off' | 'TrackAll' | 'TrackMineOnly';
}

export interface ComplianceVersionOption {
  value: 'both' | 'revised';
  label: string;
  description: string;
}

export const COMPLIANCE_VERSION_OPTIONS: ComplianceVersionOption[] = [
  {
    value: 'both',
    label: 'Both Versions (Recommended)',
    description: 'Compare compliance of original and revised versions to identify impact of changes'
  },
  {
    value: 'revised',
    label: 'Revised Only',
    description: 'Evaluate only the revised version with tracked changes'
  }
];

export interface TrackChangesComparisonRequest {
  originalText: string;
  revisedText: string;
  comparisonMode: 'full';
}

export interface TrackChangesComparisonResponse {
  success: boolean;
  standardContractId: string; // Will be 'word_original'
  compareContractIds: string[]; // Will be ['word_revised']
  comparisonMode: string;
  results: {
    comparisons: ContractComparison[];
  };
}

export interface ContractComparison {
  contract_id: string;
  overall_similarity_score: number;
  risk_level: 'low' | 'medium' | 'high';
  clause_analyses?: ClauseAnalysis[];
  missing_clauses?: string[];
  additional_clauses?: string[];
  critical_findings: string[];
  error?: string;
}

export interface ClauseAnalysis {
  clause_type: string;
  standard_clause_id: string;
  compared_clause_id: string;
  exists_in_standard: boolean;
  exists_in_compared: boolean;
  similarity_score: number;
  risk_level: 'low' | 'medium' | 'high';
  key_differences: string[];
  recommendations: string[];
}
