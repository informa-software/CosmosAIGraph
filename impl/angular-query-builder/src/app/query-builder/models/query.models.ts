// Query Models and Interfaces

export interface Entity {
  normalizedName: string;
  displayName: string;
  type: 'contractor' | 'contracting' | 'governing_law' | 'contract_type';
  contractCount: number;
  totalValue?: number;
}

export interface ClauseType {
  type: string;
  displayName: string;
  icon: string;
  description?: string;
}

export interface QueryTemplate {
  id: string;
  name: string;
  icon: string;
  description: string;
  operation: 'comparison' | 'analysis' | 'search';
  target: 'contracts' | 'clauses' | 'chunks';
  requiredFields: string[];
  optionalFields?: string[];
}

export interface StructuredQuery {
  template: string;
  operation: string;
  target: string;
  filters: { [key: string]: any };
  displayNames: { [normalizedName: string]: string };
  options: QueryOptions;
}

export interface QueryOptions {
  limit?: number;
  includeChunks?: boolean;
  includeContext?: boolean;
  dateRange?: { start: Date; end: Date };
  valueRange?: { min: number; max: number };
}

export interface QueryResult {
  success: boolean;
  results: any[];
  metadata: {
    executionTime: number;
    documentsScanned: number;
    strategy: string;
  };
  context?: string;
}

export interface EntityGroup {
  type: string;
  entities: Entity[];
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}