import { Injectable } from '@angular/core';
import { Entity, ClauseType, QueryTemplate, QueryResult } from '../models/query.models';

@Injectable({
  providedIn: 'root'
})
export class MockDataService {

  // Mock Templates
  getTemplates(): QueryTemplate[] {
    return [
      {
        id: 'COMPARE_CLAUSES',
        name: 'Compare Clauses',
        icon: 'compare_arrows',
        description: 'Compare specific clauses across multiple contracts',
        operation: 'comparison',
        target: 'clauses',
        requiredFields: ['clauseType', 'contractorParties'],
        optionalFields: ['contractingParty', 'dateRange']
      },
      {
        id: 'ANALYZE_CONTRACT',
        name: 'Analyze Contract',
        icon: 'analytics',
        description: 'Deep analysis of a single contract',
        operation: 'analysis',
        target: 'contracts',
        requiredFields: ['contractId'],
        optionalFields: ['analysisType', 'includeChunks']
      },
      {
        id: 'FIND_CONTRACTS',
        name: 'Find Contracts',
        icon: 'search',
        description: 'Search for contracts by various criteria',
        operation: 'search',
        target: 'contracts',
        requiredFields: [],
        optionalFields: ['contractingParty', 'contractorParty', 'governingLaw', 'contractType', 'dateRange']
      },
      {
        id: 'COMPARE_CONTRACTS',
        name: 'Compare Contracts',
        icon: 'difference',
        description: 'Side-by-side comparison of multiple contracts',
        operation: 'comparison',
        target: 'contracts',
        requiredFields: ['contracts'],
        optionalFields: ['comparisonAspects']
      }
    ];
  }

  // Mock Contractor Parties
  getContractorParties(): Entity[] {
    return [
      {
        normalizedName: 'abc_construction',
        displayName: 'ABC Construction LLC',
        type: 'contractor',
        contractCount: 15,
        totalValue: 5500000
      },
      {
        normalizedName: 'xyz_services',
        displayName: 'XYZ Services Inc.',
        type: 'contractor',
        contractCount: 8,
        totalValue: 3200000
      },
      {
        normalizedName: 'global_tech_solutions',
        displayName: 'Global Tech Solutions Corp',
        type: 'contractor',
        contractCount: 22,
        totalValue: 12500000
      },
      {
        normalizedName: 'premier_contractors',
        displayName: 'Premier Contractors & Associates',
        type: 'contractor',
        contractCount: 10,
        totalValue: 4800000
      },
      {
        normalizedName: 'alpha_engineering',
        displayName: 'Alpha Engineering Group',
        type: 'contractor',
        contractCount: 18,
        totalValue: 8900000
      },
      {
        normalizedName: 'cameron_d_williams_dba_c_y_transportation',
        displayName: 'CAMERON D WILLIAMS DBA C&Y TRANSPORTATION LLC',
        type: 'contractor',
        contractCount: 5,
        totalValue: 750000
      }
    ];
  }

  // Mock Contracting Parties
  getContractingParties(): Entity[] {
    return [
      {
        normalizedName: 'westervelt',
        displayName: 'The Westervelt Company',
        type: 'contracting',
        contractCount: 25,
        totalValue: 45000000
      },
      {
        normalizedName: 'acme',
        displayName: 'ACME Corporation',
        type: 'contracting',
        contractCount: 30,
        totalValue: 62000000
      },
      {
        normalizedName: 'pinnacle_enterprises',
        displayName: 'Pinnacle Enterprises Holdings',
        type: 'contracting',
        contractCount: 18,
        totalValue: 38000000
      },
      {
        normalizedName: 'meridian_group',
        displayName: 'Meridian Group International',
        type: 'contracting',
        contractCount: 12,
        totalValue: 28500000
      },
      {
        normalizedName: 'fortune_500_company',
        displayName: 'Fortune 500 Company LLC',
        type: 'contracting',
        contractCount: 45,
        totalValue: 125000000
      }
    ];
  }

  // Mock Governing Laws
  getGoverningLaws(): Entity[] {
    return [
      {
        normalizedName: 'alabama',
        displayName: 'Alabama',
        type: 'governing_law',
        contractCount: 45
      },
      {
        normalizedName: 'georgia',
        displayName: 'Georgia',
        type: 'governing_law',
        contractCount: 32
      },
      {
        normalizedName: 'florida',
        displayName: 'Florida',
        type: 'governing_law',
        contractCount: 28
      },
      {
        normalizedName: 'texas',
        displayName: 'Texas',
        type: 'governing_law',
        contractCount: 38
      },
      {
        normalizedName: 'new_york',
        displayName: 'New York',
        type: 'governing_law',
        contractCount: 52
      },
      {
        normalizedName: 'california',
        displayName: 'California',
        type: 'governing_law',
        contractCount: 41
      }
    ];
  }

  // Mock Contract Types
  getContractTypes(): Entity[] {
    return [
      {
        normalizedName: 'master_services_agreement',
        displayName: 'Master Services Agreement',
        type: 'contract_type',
        contractCount: 85
      },
      {
        normalizedName: 'non_disclosure_agreement',
        displayName: 'Non-Disclosure Agreement',
        type: 'contract_type',
        contractCount: 120
      },
      {
        normalizedName: 'statement_of_work',
        displayName: 'Statement of Work',
        type: 'contract_type',
        contractCount: 65
      },
      {
        normalizedName: 'purchase_order',
        displayName: 'Purchase Order',
        type: 'contract_type',
        contractCount: 95
      },
      {
        normalizedName: 'service_level_agreement',
        displayName: 'Service Level Agreement',
        type: 'contract_type',
        contractCount: 42
      }
    ];
  }

  // Mock Clause Types
  getClauseTypes(): ClauseType[] {
    return [
      {
        type: 'Indemnification',
        displayName: 'Indemnification',
        icon: 'shield',
        description: 'Protection against losses and damages'
      },
      {
        type: 'IndemnificationObligations',
        displayName: 'Indemnification Obligations',
        icon: 'security',
        description: 'Specific indemnity obligations'
      },
      {
        type: 'PaymentObligations',
        displayName: 'Payment Terms',
        icon: 'payment',
        description: 'Payment schedules and terms'
      },
      {
        type: 'TerminationObligations',
        displayName: 'Termination',
        icon: 'cancel',
        description: 'Contract termination conditions'
      },
      {
        type: 'WarrantyObligations',
        displayName: 'Warranties',
        icon: 'verified',
        description: 'Warranty terms and conditions'
      },
      {
        type: 'ConfidentialityObligations',
        displayName: 'Confidentiality',
        icon: 'lock',
        description: 'Confidentiality and NDA terms'
      },
      {
        type: 'LimitationOfLiabilityObligations',
        displayName: 'Limitation of Liability',
        icon: 'warning',
        description: 'Liability limitations and caps'
      },
      {
        type: 'ComplianceObligations',
        displayName: 'Compliance',
        icon: 'gavel',
        description: 'Regulatory compliance requirements'
      },
      {
        type: 'ServiceLevelAgreement',
        displayName: 'Service Levels',
        icon: 'trending_up',
        description: 'Service level requirements and SLAs'
      }
    ];
  }

  // Mock Query Results
  getMockQueryResults(query: any): QueryResult {
    const mockResults: { [key: string]: QueryResult } = {
      'COMPARE_CLAUSES': {
        success: true,
        results: [
          {
            contractId: 'contract_123',
            parties: 'The Westervelt Company - ABC Construction LLC',
            clauseType: 'Indemnification',
            clauseText: 'ABC Construction LLC shall defend, indemnify, and hold harmless The Westervelt Company from and against any and all claims, damages, losses, and expenses...',
            confidence: 0.92
          },
          {
            contractId: 'contract_456',
            parties: 'The Westervelt Company - XYZ Services Inc.',
            clauseType: 'Indemnification',
            clauseText: 'XYZ Services Inc. agrees to indemnify and hold harmless The Westervelt Company against all losses, damages, and expenses including reasonable attorney fees...',
            confidence: 0.89
          }
        ],
        metadata: {
          executionTime: 1250,
          documentsScanned: 42,
          strategy: 'orchestrated'
        },
        context: 'Retrieved 2 indemnification clauses for comparison from contracts with The Westervelt Company'
      },
      'FIND_CONTRACTS': {
        success: true,
        results: [
          {
            contractId: 'contract_001',
            contractorParty: 'ABC Construction LLC',
            contractingParty: 'The Westervelt Company',
            governingLaw: 'Alabama',
            contractType: 'Master Services Agreement',
            effectiveDate: '2024-01-15',
            value: 2500000
          },
          {
            contractId: 'contract_002',
            contractorParty: 'Global Tech Solutions Corp',
            contractingParty: 'The Westervelt Company',
            governingLaw: 'Alabama',
            contractType: 'Master Services Agreement',
            effectiveDate: '2024-02-20',
            value: 3800000
          },
          {
            contractId: 'contract_003',
            contractorParty: 'Premier Contractors & Associates',
            contractingParty: 'ACME Corporation',
            governingLaw: 'Alabama',
            contractType: 'Master Services Agreement',
            effectiveDate: '2024-03-10',
            value: 1200000
          }
        ],
        metadata: {
          executionTime: 850,
          documentsScanned: 156,
          strategy: 'database'
        },
        context: ''
      },
      'ANALYZE_CONTRACT': {
        success: true,
        results: [
          {
            contractId: 'contract_789',
            analysis: {
              parties: {
                contractor: 'Alpha Engineering Group',
                contracting: 'Pinnacle Enterprises Holdings'
              },
              keyTerms: {
                value: 4500000,
                duration: '3 years',
                governingLaw: 'Georgia'
              },
              risks: [
                'Unlimited liability clause present',
                'No force majeure provision',
                'Ambiguous termination conditions'
              ],
              obligations: [
                'Quarterly progress reports required',
                'Insurance minimum $5M',
                'Performance bond required'
              ]
            }
          }
        ],
        metadata: {
          executionTime: 2100,
          documentsScanned: 8,
          strategy: 'vector'
        },
        context: ''
      }
    };

    // Return appropriate mock based on template
    const template = query.template || 'FIND_CONTRACTS';
    return mockResults[template] || mockResults['FIND_CONTRACTS'];
  }

  // Search entities with simulated fuzzy matching
  searchEntities(searchText: string, entityType: string): Entity[] {
    let entities: Entity[] = [];
    
    switch (entityType) {
      case 'contractor':
        entities = this.getContractorParties();
        break;
      case 'contracting':
        entities = this.getContractingParties();
        break;
      case 'governing_law':
        entities = this.getGoverningLaws();
        break;
      case 'contract_type':
        entities = this.getContractTypes();
        break;
    }

    if (!searchText) {
      return entities;
    }

    const search = searchText.toLowerCase();
    return entities.filter(entity => 
      entity.displayName.toLowerCase().includes(search) ||
      entity.normalizedName.toLowerCase().includes(search)
    );
  }
}