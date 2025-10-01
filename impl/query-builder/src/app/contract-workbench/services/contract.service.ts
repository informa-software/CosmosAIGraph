import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { 
  Contract, 
  ContractQuery, 
  ContractQueryResponse, 
  EntityOption,
  ContractComparisonRequest,
  ContractComparisonResponse 
} from '../models/contract.models';

// Mock data for development/fallback
const MOCK_CONTRACTS: Contract[] = [
  {
    id: 'contract_c001',
    title: 'Master Services Agreement – Asterix Health',
    counterparty: 'Asterix Health, Inc.',
    contractingParty: 'The Westervelt Company',
    effective: '2024-11-02',
    law: 'New York',
    type: 'MSA',
    risk: 'Med',
    clauses: {
      Indemnity: 'Each party shall indemnify, defend, and hold harmless the other from third-party claims arising out of gross negligence or willful misconduct.',
      'Limitation of Liability': 'Neither party shall be liable for indirect or consequential damages; aggregate liability shall not exceed 12 months of fees.',
      'Payment Terms': 'Net 45 days from invoice date; 1% monthly late fee.',
      Insurance: 'Commercial general liability $2M, cyber liability $3M, workers\' compensation statutory.',
      'Governing Law': 'This Agreement is governed by the laws of the State of New York, without regard to conflicts principles.',
    },
  },
  {
    id: 'contract_c002',
    title: 'Subscription Agreement – Novalink',
    counterparty: 'Novalink LLC',
    contractingParty: 'Westervelt Ecological Services',
    effective: '2025-03-18',
    law: 'Delaware',
    type: 'Subscription',
    risk: 'Low',
    clauses: {
      Indemnity: 'Vendor will indemnify Customer against third-party IP infringement claims subject to prompt notice and sole control of the defense.',
      'Limitation of Liability': 'EXCEPT FOR FRAUD OR INTENTIONAL MISCONDUCT, LIABILITY IS CAPPED AT FEES PAID IN THE SIX (6) MONTHS PRECEDING THE CLAIM.',
      'Payment Terms': 'Net 30; 0.5% monthly late fee.',
      Insurance: 'CGL $1M, cyber $1M.',
      'Governing Law': 'This Agreement and any dispute shall be governed by the laws of the State of Delaware.',
    },
  },
  {
    id: 'contract_c003',
    title: 'Professional Services SOW – BlueFerry',
    counterparty: 'BlueFerry Corp',
    contractingParty: 'Westervelt Lumber Thomasville',
    effective: '2023-09-01',
    law: 'California',
    type: 'SOW',
    risk: 'High',
    clauses: {
      Indemnity: 'Vendor shall indemnify Customer for claims alleging bodily injury, death, or damage to tangible property caused by Vendor\'s performance.',
      'Limitation of Liability': 'Total cumulative liability shall not exceed the greater of $500,000 or amounts paid in the 3 months preceding the event.',
      'Payment Terms': 'Milestone-based; 40/40/20 with 10-day review windows.',
      Insurance: 'CGL $2M, professional liability $1M.',
      'Governing Law': 'This Statement of Work is governed by the laws of the State of California.',
    },
  },
  {
    id: 'contract_c004',
    title: 'Service Agreement – Sunshine Systems',
    counterparty: 'Sunshine Systems LLC',
    contractingParty: 'The Westervelt Company',
    effective: '2024-06-15',
    law: 'Florida',
    type: 'MSA',
    risk: 'Low',
    clauses: {
      Indemnity: 'Provider shall indemnify Client for third-party claims arising from Provider\'s breach of this Agreement or negligent acts.',
      'Limitation of Liability': 'Total liability shall not exceed the total fees paid under this Agreement in the twelve (12) month period preceding the claim.',
      'Payment Terms': 'Net 30 days; 1.5% monthly interest on overdue amounts.',
      Insurance: 'General liability $2M, professional liability $2M, auto liability $1M.',
      'Governing Law': 'This Agreement shall be governed by and construed in accordance with the laws of the State of Florida.',
    },
  },
  {
    id: 'contract_c005',
    title: 'Software License Agreement – Peachtree Tech',
    counterparty: 'Peachtree Technologies Inc.',
    contractingParty: 'Westervelt Ecological Services',
    effective: '2023-12-01',
    law: 'Georgia',
    type: 'Subscription',
    risk: 'Med',
    clauses: {
      Indemnity: 'Licensor indemnifies Licensee against claims that the Software infringes third-party intellectual property rights.',
      'Limitation of Liability': 'Neither party liable for special, incidental, or consequential damages. Total liability limited to fees paid in prior 6 months.',
      'Payment Terms': 'Annual prepayment; Net 15 for additional services.',
      Insurance: 'Technology E&O $3M, cyber liability $5M.',
      'Governing Law': 'This Agreement is governed by the laws of the State of Georgia without regard to conflict of law principles.',
    },
  },
  {
    id: 'contract_c006',
    title: 'Consulting Agreement – Gulf Coast Advisors',
    counterparty: 'Gulf Coast Advisors',
    contractingParty: 'Westervelt Lumber Thomasville',
    effective: '2024-09-30',
    law: 'Alabama',
    type: 'SOW',
    risk: 'High',
    clauses: {
      Indemnity: 'Consultant shall defend and indemnify Company from all claims resulting from Consultant\'s willful misconduct or gross negligence.',
      'Limitation of Liability': 'Consultant\'s aggregate liability shall not exceed fifty percent (50%) of fees paid under the applicable Statement of Work.',
      'Payment Terms': 'Monthly invoicing; payment due within 45 days of invoice date.',
      Insurance: 'Professional liability $1M, general liability $1M, workers compensation as required by law.',
      'Governing Law': 'This Agreement shall be governed by the laws of the State of Alabama.',
    },
  },
];

@Injectable({
  providedIn: 'root'
})
export class ContractService {
  private apiUrl = 'http://localhost:8000/api'; // Backend API URL

  constructor(private http: HttpClient) {}

  /**
   * Get contracts with optional filtering
   * Now supports multiple values for contracting parties and governing laws
   */
  getContracts(
    contractType?: string,
    contractorParty?: string,
    contractingParties?: string[],  // Changed to array
    governingLaws?: string[],       // Changed to array
    dateFrom?: string,
    dateTo?: string
  ): Observable<Contract[]> {
    let params = new HttpParams();
    
    if (contractType && contractType !== 'Any') {
      params = params.set('contract_type', contractType);
    }
    if (contractorParty) {
      params = params.set('contractor_party', contractorParty);
    }
    // Send multiple contracting parties as comma-separated string
    if (contractingParties && contractingParties.length > 0) {
      params = params.set('contracting_parties', contractingParties.join(','));
    }
    // Send multiple governing laws as comma-separated string
    if (governingLaws && governingLaws.length > 0) {
      params = params.set('governing_laws', governingLaws.join(','));
    }
    if (dateFrom) {
      params = params.set('date_from', dateFrom);
    }
    if (dateTo) {
      params = params.set('date_to', dateTo);
    }

    return this.http.get<{ contracts: Contract[] }>(`${this.apiUrl}/contracts`, { params }).pipe(
      map(response => response.contracts),
      catchError(error => {
        console.log('Using mock contracts data:', error);
        return of(MOCK_CONTRACTS);
      })
    );
  }

  /**
   * Query contracts using natural language
   */
  queryContracts(query: ContractQuery): Observable<ContractQueryResponse> {
    return this.http.post<ContractQueryResponse>(`${this.apiUrl}/contract_query`, query).pipe(
      catchError(error => {
        console.error('Error querying contracts:', error);
        // Return mock response
        const nonDelawareContracts = MOCK_CONTRACTS
          .filter(c => c.law !== 'Delaware')
          .map(c => `${c.title} (${c.law})`)
          .join(', ');
        
        return of({
          answer: `Contracts governed by states other than Delaware: ${nonDelawareContracts}. The most divergent indemnity language appears in the BlueFerry SOW (bodily injury/property focus) vs Novalink Agreement (IP infringement focus).`,
          strategy: {
            useDb: true,
            useVector: false,
            useGraph: false,
            entities: {}
          },
          contextUsed: 0
        });
      })
    );
  }

  /**
   * Get mock contracts for development
   */
  getMockContracts(): Contract[] {
    return MOCK_CONTRACTS;
  }

  /**
   * Get all governing laws from the backend
   */
  getGoverningLaws(): Observable<EntityOption[]> {
    return this.http.get<any>(`${this.apiUrl}/entities/governing_laws`).pipe(
      map(response => {
        console.log('Governing laws API response:', response);
        
        // Handle the response format: { entities: [...], total: n, type: "governing_laws" }
        if (response && response.entities && Array.isArray(response.entities)) {
          // Return EntityOption objects with both display and normalized names
          const laws = response.entities.map((item: any) => ({
            normalizedName: item.normalizedName || item.name,
            displayName: item.displayName || item.normalizedName || item.name,
            contractCount: item.contractCount,
            totalValue: item.totalValue
          }));
          console.log('Extracted governing laws:', laws);
          return laws;
        }
        
        // If response format is unexpected, throw error
        throw new Error('Invalid response format from governing laws API');
      })
    );
  }

  /**
   * Get all contracting parties from the backend
   */
  getContractingParties(): Observable<EntityOption[]> {
    return this.http.get<any>(`${this.apiUrl}/entities/contracting_parties`).pipe(
      map(response => {
        console.log('Contracting parties API response:', response);
        
        // Handle the response format: { entities: [...], total: n, type: "contracting_parties" }
        if (response && response.entities && Array.isArray(response.entities)) {
          // Return EntityOption objects with both display and normalized names
          const parties = response.entities.map((item: any) => ({
            normalizedName: item.normalizedName || item.name,
            displayName: item.displayName || item.normalizedName || item.name,
            contractCount: item.contractCount,
            totalValue: item.totalValue
          }));
          console.log('Extracted contracting parties:', parties);
          return parties;
        }
        
        // If response format is unexpected, throw error
        throw new Error('Invalid response format from contracting parties API');
      })
    );
  }

  /**
   * Get all contract types from the backend
   */
  getContractTypes(): Observable<EntityOption[]> {
    return this.http.get<any>(`${this.apiUrl}/entities/contract_types`).pipe(
      map(response => {
        console.log('Contract types API response:', response);
        
        // Handle the actual response format: { entities: [...], total: n, type: "contract_types" }
        if (response && response.entities && Array.isArray(response.entities)) {
          // Return EntityOption objects with both display and normalized names
          const types = response.entities.map((item: any) => ({
            normalizedName: item.normalizedName || item.type,
            displayName: item.displayName || item.normalizedName || item.type,
            contractCount: item.contractCount,
            totalValue: item.totalValue
          }));
          console.log('Extracted contract types:', types);
          return types;
        }
        
        // If response format is unexpected, throw error
        throw new Error('Invalid response format from contract types API');
      })
    );
  }

  /**
   * Compare contracts against a standard contract
   */
  compareContracts(request: ContractComparisonRequest): Observable<ContractComparisonResponse> {
    return this.http.post<ContractComparisonResponse>(`${this.apiUrl}/compare-contracts`, request).pipe(
      catchError(error => {
        console.error('Error comparing contracts:', error);
        
        // Return error response
        return of({
          success: false,
          standardContractId: request.standardContractId,
          compareContractIds: request.compareContractIds,
          comparisonMode: request.comparisonMode,
          selectedClauses: request.selectedClauses,
          results: { comparisons: [] },
          error: error.message || 'Failed to compare contracts'
        });
      })
    );
  }
}