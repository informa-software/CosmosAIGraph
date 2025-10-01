// Contract Models

// Entity interfaces for display/normalized value pairs
export interface EntityOption {
  normalizedName: string;
  displayName: string;
  contractCount?: number;
  totalValue?: number;
}

export interface Contract {
  id: string;
  title: string;
  counterparty: string;
  contractingParty?: string;
  effective: string;
  expiration?: string;
  law: string;
  type: string;
  risk?: string;
  value?: string;
  clauses: { [key: string]: string };
  hasFullText?: boolean;
  textTokens?: number;
}

export interface ContractFilter {
  mode: 'realtime' | 'batch';
  comparisonMode?: 'clauses' | 'full';
  type: string;
  dateFrom: string;
  dateTo: string;
  clauses: string[];
  risk: number;
  governingLaws?: string[];
  contractingParties?: string[];
}

export interface ContractQuery {
  question: string;
  filters: ContractFilter;
  selectedContracts: string[];
}

export interface ContractQueryResponse {
  answer: string;
  strategy: QueryStrategy;
  contextUsed: number;
}

export interface QueryStrategy {
  useDb: boolean;
  useVector: boolean;
  useGraph: boolean;
  entities: {
    contractorParties?: string[];
    contractingParties?: string[];
    governingLaws?: string[];
    contractTypes?: string[];
  };
}

// Contract Comparison Models
export interface ContractComparisonRequest {
  standardContractId: string;
  compareContractIds: string[];
  comparisonMode: 'clauses' | 'full';
  selectedClauses?: string[] | 'all';
}

export interface ContractComparisonResponse {
  success: boolean;
  standardContractId: string;
  compareContractIds: string[];
  comparisonMode: 'clauses' | 'full';
  selectedClauses?: string[] | 'all';
  results: ComparisonResults;
  error?: string;
}

export interface ComparisonResults {
  comparisons: ContractComparison[];
}

export interface ContractComparison {
  contract_id: string;
  overall_similarity_score: number;
  risk_level: 'low' | 'medium' | 'high';
  clause_analyses: ClauseAnalysis[];
  missing_clauses: string[];
  additional_clauses: string[];
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
  key_differences: string[];
  risks: string[];
  summary: string;
  standard_clause_text?: string;
  compared_clause_text?: string;
}

export interface GoldStandard {
  [provision: string]: string;
}

export const CLAUSE_KEYS = [
  'Indemnity',
  'Limitation of Liability',
  'Payment Terms',
  'Insurance',
  'Governing Law'
];

// Gold standard baseline (from C-002 in mock data)
export const GOLD_STANDARD: GoldStandard = {
  'Payment Terms': 'Net 30; 0.5% monthly late fee.',
  'Insurance': 'CGL $1M, cyber $1M.',
  'Limitation of Liability': 'EXCEPT FOR FRAUD OR INTENTIONAL MISCONDUCT, LIABILITY IS CAPPED AT FEES PAID IN THE SIX (6) MONTHS PRECEDING THE CLAIM.'
};