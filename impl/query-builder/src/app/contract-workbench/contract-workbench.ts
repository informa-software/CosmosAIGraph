import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { 
  Contract, 
  ContractFilter, 
  ContractQuery,
  EntityOption,
  ContractComparisonRequest,
  ContractComparisonResponse,
  ContractComparison,
  ClauseAnalysis,
  CLAUSE_KEYS, 
  GOLD_STANDARD 
} from './models/contract.models';
import { ContractService } from './services/contract.service';
import { ToastService } from '../shared/services/toast.service';

@Component({
  selector: 'app-contract-workbench',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './contract-workbench.html',
  styleUrls: ['./contract-workbench.scss']
})
export class ContractWorkbenchComponent implements OnInit {
  // Constants
  readonly CLAUSE_KEYS = CLAUSE_KEYS;
  readonly GOLD_STANDARD = GOLD_STANDARD;

  // Mode state
  workbenchMode: 'comparison' | 'question' = 'comparison'; // Primary mode selector

  // State
  contracts: Contract[] = [];
  filteredContracts: Contract[] = [];
  allContracts: Contract[] = []; // All contracts for Standard Contract dropdown
  selectedContracts: string[] = [];
  standardContractId: string = '';
  standardContract: Contract | null = null;
  availableGoverningLaws: EntityOption[] = [];
  availableContractingParties: EntityOption[] = [];
  availableContractTypes: EntityOption[] = [];
  availableClausesFromStandard: string[] = []; // Clauses from the selected standard contract
  
  filters: ContractFilter = {
    mode: 'realtime',
    comparisonMode: 'clauses',
    type: 'Any',
    dateFrom: '',
    dateTo: '',
    clauses: [],
    risk: 50,
    governingLaws: [],
    contractingParties: []
  };

  searchText = '';
  question = '';
  answer = '';
  isLoadingAnswer = false;
  
  // Chat interface state
  chatHistory: { text: string; timestamp: Date; isProcessing?: boolean }[] = [];
  currentChatInput = '';

  // Comparison state
  comparisonResults: ContractComparisonResponse | null = null;
  isLoadingComparison = false;
  showComparisonModal = false;
  expandedClauses: { [key: string]: boolean } = {}; // Track which clauses are expanded
  showClauseTextModal = false;
  selectedClauseForReview: ClauseAnalysis | null = null;
  selectedContractIdForReview: string = '';

  // UI state
  activeTab: 'answers' | 'contracts' | 'clauses' | 'comparison' = 'comparison';
  showContractSelectionModal = false;
  isLoadingContracts = false;
  showContractDetailsModal = false;
  showRawDiffModal = false;
  selectedContractForDetails: Contract | null = null;
  dateRangeError = '';

  // Computed properties
  get canSelectMoreContracts(): boolean {
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;
    return this.selectedContracts.length < maxContracts;
  }

  get pickedContracts(): Contract[] {
    return this.contracts.filter(c => this.selectedContracts.includes(c.id));
  }

  // Get filtered contracts excluding the standard contract for selection list
  getFilteredContractsForSelection(): Contract[] {
    if (!this.standardContractId) {
      return this.filteredContracts;
    }
    // Filter out the standard contract from the selection list
    return this.filteredContracts.filter(c => c.id !== this.standardContractId);
  }

  get jurisdictionStats(): { [key: string]: number } {
    const stats: { [key: string]: number } = {};
    this.contracts.forEach(contract => {
      stats[contract.governing_law_state] = (stats[contract.governing_law_state] || 0) + 1;
    });
    return stats;
  }

  constructor(
    private contractService: ContractService,
    private toastService: ToastService
  ) {}

  ngOnInit(): void {
    this.loadGoverningLaws();
    this.loadContractingParties();
    this.loadContractTypes();
    this.loadAllContracts(); // Load all contracts for Standard Contract dropdown
    // Don't load filtered contracts on init - wait for user to click Select Contracts
    
    // Set initial tab based on mode
    this.updateTabForMode();
  }

  setWorkbenchMode(mode: 'comparison' | 'question'): void {
    this.workbenchMode = mode;
    this.updateTabForMode();
  }

  updateTabForMode(): void {
    if (this.workbenchMode === 'comparison') {
      // For comparison mode, show comparison results tab
      this.activeTab = 'comparison';
    } else {
      // For question mode, show answers tab
      this.activeTab = 'answers';
    }
  }

  loadGoverningLaws(): void {
    // Call API to get all governing laws
    this.contractService.getGoverningLaws().subscribe({
      next: (laws) => {
        if (laws && laws.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableGoverningLaws = laws.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded governing laws from API:', this.availableGoverningLaws);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Governing Laws Found',
            'The API returned no governing laws. Please check your data.'
          );
          this.availableGoverningLaws = [];
        }
      },
      error: (error) => {
        console.error('Error loading governing laws from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Governing Laws',
          'Unable to retrieve governing laws from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableGoverningLaws = [];
      }
    });
  }

  loadContractingParties(): void {
    // Call API to get all contracting parties
    this.contractService.getContractingParties().subscribe({
      next: (parties) => {
        if (parties && parties.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableContractingParties = parties.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded contracting parties from API:', this.availableContractingParties);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Contracting Parties Found',
            'The API returned no contracting parties. Please check your data.'
          );
          this.availableContractingParties = [];
        }
      },
      error: (error) => {
        console.error('Error loading contracting parties from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Contracting Parties',
          'Unable to retrieve contracting parties from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableContractingParties = [];
      }
    });
  }

  loadContractTypes(): void {
    // Call API to get all contract types
    this.contractService.getContractTypes().subscribe({
      next: (types) => {
        if (types && types.length > 0) {
          // Sort by display name for user-friendly ordering
          this.availableContractTypes = types.sort((a, b) => 
            a.displayName.localeCompare(b.displayName)
          );
          console.log('Loaded contract types from API:', this.availableContractTypes);
        } else {
          // If API returns empty list
          this.toastService.warning(
            'No Contract Types Found',
            'The API returned no contract types. Please check your data.'
          );
          this.availableContractTypes = [];
        }
      },
      error: (error) => {
        console.error('Error loading contract types from API:', error);
        // Show error toast
        this.toastService.error(
          'Failed to Load Contract Types',
          'Unable to retrieve contract types from the server. Please try again later.'
        );
        // Set empty array - no fallback
        this.availableContractTypes = [];
      }
    });
  }

  loadAllContracts(): void {
    // Load all contracts without any filters for the Standard Contract dropdown
    this.contractService.getContracts().subscribe({
      next: (contracts) => {
        this.allContracts = contracts;
        console.log('Loaded all contracts for Standard Contract dropdown:', contracts.length);
        console.log('Sample contract IDs:', contracts.slice(0, 3).map(c => ({ id: c.id, title: c.title })));
      },
      error: (error) => {
        console.error('Error loading all contracts:', error);
        // Silent failure - Standard Contract dropdown is optional
        this.allContracts = [];
      }
    });
  }

  // Date validation is still needed for UI feedback
  validateDateRange(): void {
    if (this.filters.dateFrom && this.filters.dateTo) {
      const fromDate = new Date(this.filters.dateFrom);
      const toDate = new Date(this.filters.dateTo);
      
      if (fromDate > toDate) {
        this.dateRangeError = 'From date must be before or equal to To date';
      } else {
        this.dateRangeError = '';
      }
    } else {
      this.dateRangeError = '';
    }
    
    // Clear selected contracts when date range changes
    if (this.filters.dateFrom || this.filters.dateTo) {
      this.selectedContracts = [];
    }
  }

  onStandardContractChange(): void {
    if (this.standardContractId) {
      console.log('Standard contract ID from select:', this.standardContractId);
      console.log('All contracts:', this.allContracts.map(c => ({ id: c.id, title: c.title })));
      
      // Look in allContracts instead of contracts (which might be filtered)
      this.standardContract = this.allContracts.find(c => c.id === this.standardContractId) || null;
      console.log('Standard contract selected:', this.standardContract);
      
      // Extract available clauses from the standard contract
      if (this.standardContract && this.standardContract.clauses) {
        this.availableClausesFromStandard = Object.keys(this.standardContract.clauses);
        console.log('Available clauses from standard contract:', this.availableClausesFromStandard);
        
        // Default to selecting all clauses
        this.filters.clauses = [...this.availableClausesFromStandard];
      } else {
        this.availableClausesFromStandard = [];
        this.filters.clauses = [];
      }
      
      // Remove standard contract from selected contracts if it was selected
      const index = this.selectedContracts.indexOf(this.standardContractId);
      if (index > -1) {
        this.selectedContracts.splice(index, 1);
      }
    } else {
      this.standardContract = null;
      this.availableClausesFromStandard = [];
      this.filters.clauses = [];
    }
  }

  onModeChange(mode: 'realtime' | 'batch'): void {
    this.filters.mode = mode;
    
    // Clear selected contracts when mode changes
    this.selectedContracts = [];
    
    // Enforce limits for contracts only
    if (mode === 'realtime') {
      if (this.selectedContracts.length > 3) {
        this.selectedContracts = this.selectedContracts.slice(0, 3);
      }
    }
  }

  toggleContractSelection(contractId: string): void {
    const index = this.selectedContracts.indexOf(contractId);
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;

    if (index === -1) {
      if (this.selectedContracts.length < maxContracts) {
        this.selectedContracts.push(contractId);
      }
    } else {
      this.selectedContracts.splice(index, 1);
    }
  }

  isContractSelected(contractId: string): boolean {
    return this.selectedContracts.includes(contractId);
  }

  selectAllContracts(): void {
    const maxContracts = this.filters.mode === 'realtime' ? 3 : 999;
    
    this.filteredContracts.forEach(contract => {
      if (!this.selectedContracts.includes(contract.id) && this.selectedContracts.length < maxContracts) {
        this.selectedContracts.push(contract.id);
      }
    });
  }

  deselectAllContracts(): void {
    const filteredIds = this.filteredContracts.map(c => c.id);
    this.selectedContracts = this.selectedContracts.filter(id => !filteredIds.includes(id));
  }

  toggleClause(clause: string): void {
    const index = this.filters.clauses.indexOf(clause);
    
    if (index === -1) {
      this.filters.clauses.push(clause);
    } else {
      this.filters.clauses.splice(index, 1);
    }
    // Clear selected contracts when clause selection changes
    this.selectedContracts = [];
  }

  isClauseSelected(clause: string): boolean {
    return this.filters.clauses.includes(clause);
  }

  // Handler for contract type changes
  onContractTypeChange(): void {
    // Clear selected contracts when contract type changes
    this.selectedContracts = [];
  }

  // Handler for comparison mode changes
  onComparisonModeChange(mode: 'clauses' | 'full'): void {
    this.filters.comparisonMode = mode;
    // Clear selected contracts when comparison mode changes
    this.selectedContracts = [];
  }


  getAnswer(): void {
    this.isLoadingAnswer = true;
    
    const query: ContractQuery = {
      question: this.question,
      filters: this.filters,
      selectedContracts: this.selectedContracts
    };

    this.contractService.queryContracts(query).subscribe({
      next: (response) => {
        this.answer = response.answer;
        this.isLoadingAnswer = false;
        this.activeTab = 'answers';
        
        // Update chat history to remove processing state
        if (this.chatHistory.length > 0) {
          this.chatHistory[this.chatHistory.length - 1].isProcessing = false;
        }
      },
      error: (error) => {
        console.error('Error getting answer:', error);
        this.answer = 'Error processing query. Please try again.';
        this.isLoadingAnswer = false;
        
        // Update chat history to remove processing state
        if (this.chatHistory.length > 0) {
          this.chatHistory[this.chatHistory.length - 1].isProcessing = false;
        }
      }
    });
  }

  sendChatMessage(): void {
    if (!this.currentChatInput.trim()) {
      return;
    }
    
    // Add question to chat history with processing state
    this.chatHistory.push({
      text: this.currentChatInput,
      timestamp: new Date(),
      isProcessing: true
    });
    
    // Set the question for the query
    this.question = this.currentChatInput;
    
    // Clear input
    this.currentChatInput = '';
    
    // Send the query
    this.getAnswer();
  }

  clearChatHistory(): void {
    this.chatHistory = [];
    this.currentChatInput = '';
    this.question = '';
    this.answer = '';
  }

  onChatKeyPress(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendChatMessage();
    }
  }

  askExampleQuestion(question: string): void {
    this.currentChatInput = question;
    this.sendChatMessage();
  }

  compareSelected(): void {
    // Open the contract selection modal and load filtered contracts
    this.showContractSelectionModal = true;
    this.loadFilteredContracts();
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
  }
  
  closeContractSelectionModal(): void {
    this.showContractSelectionModal = false;
    // Re-enable body scroll
    document.body.style.overflow = '';
  }

  loadFilteredContracts(): void {
    this.isLoadingContracts = true;
    
    // Build filter parameters for API call
    // Only pass non-"Any" values and non-empty arrays
    // Use the stored normalized values (which are now in filters)
    const contractType = this.filters.type !== 'Any' ? this.filters.type : undefined;
    const governingLaws = this.filters.governingLaws && this.filters.governingLaws.length > 0 
      ? this.filters.governingLaws : undefined;
    const contractingParties = this.filters.contractingParties && this.filters.contractingParties.length > 0
      ? this.filters.contractingParties : undefined;
    const dateFrom = this.filters.dateFrom || undefined;
    const dateTo = this.filters.dateTo || undefined;

    // Call the service with arrays for multi-select fields
    this.contractService.getContracts(
      contractType,
      undefined, // contractor_party - not in our filters yet
      contractingParties, // Pass full array - service will convert to comma-separated
      governingLaws,      // Pass full array - service will convert to comma-separated
      dateFrom,
      dateTo
    ).subscribe({
      next: (contracts) => {
        this.contracts = contracts;
        this.filteredContracts = contracts; // All returned contracts are already filtered
        this.isLoadingContracts = false;
        console.log('Loaded filtered contracts:', contracts.length);
      },
      error: (error) => {
        console.error('Error loading contracts:', error);
        this.toastService.error('Failed to Load Contracts', 'Unable to retrieve contracts from the server.');
        this.contracts = [];
        this.filteredContracts = [];
        this.isLoadingContracts = false;
      }
    });
  }

  copyResults(): void {
    const results = {
      query: this.question,
      filters: this.filters,
      selectedContracts: this.pickedContracts,
      timestamp: new Date().toISOString()
    };

    navigator.clipboard.writeText(JSON.stringify(results, null, 2))
      .then(() => {
        alert('Results copied to clipboard!');
      })
      .catch(err => {
        console.error('Failed to copy:', err);
        alert('Failed to copy results to clipboard');
      });
  }

  showContractDetails(contract: Contract): void {
    this.selectedContractForDetails = contract;
    this.showContractDetailsModal = true;
  }

  showRawDiff(): void {
    if (this.pickedContracts.length >= 2) {
      this.showRawDiffModal = true;
    }
  }

  highlightText(text: string): string {
    if (!this.searchText || !text) return text;
    const regex = new RegExp(`(${this.searchText})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  normalizeText(text: string): string {
    return String(text || '').replace(/\s+/g, ' ').trim().toLowerCase();
  }

  isDifferentFromGoldStandard(provision: string, value: string): boolean {
    // First check if we have a standard contract selected
    if (this.standardContract && this.standardContract.clauses[provision]) {
      const standardValue = this.standardContract.clauses[provision];
      return this.normalizeText(value) !== this.normalizeText(standardValue);
    }
    
    // Fall back to predefined gold standard
    const goldStandard = this.GOLD_STANDARD[provision];
    if (!goldStandard) return false;
    return this.normalizeText(value) !== this.normalizeText(goldStandard);
  }

  hasGoldStandard(provision: string): boolean {
    // Check if standard contract has this provision
    if (this.standardContract && this.standardContract.clauses[provision]) {
      return true;
    }
    
    // Fall back to predefined gold standard
    return !!this.GOLD_STANDARD[provision];
  }

  getStandardValue(provision: string): string {
    // Return the standard value for comparison
    if (this.standardContract && this.standardContract.clauses[provision]) {
      return this.standardContract.clauses[provision];
    }
    return this.GOLD_STANDARD[provision] || '';
  }

  diffStrings(a: string, b: string): string[] {
    const aWords = a.split(/\s+/);
    const bWords = new Set(b.split(/\s+/));
    
    return aWords.map(word => {
      if (bWords.has(word)) {
        return word;
      } else {
        return `<span class="diff-highlight">${word}</span>`;
      }
    });
  }

  getClauseIcon(clauseName: string): string {
    const icons: { [key: string]: string } = {
      'Indemnity': '🛡️',
      'Payment Terms': '💰',
      'Governing Law': '⚖️',
      'Insurance': '☂️',
      'Limitation of Liability': '⚠️'
    };
    return icons[clauseName] || '📄';
  }

  runSavedQuery(queryName: string): void {
    let queryText = '';
    if (queryName === 'non-delaware') {
      queryText = 'Which contracts are governed by states other than Delaware?';
    } else if (queryName === 'indemnity-by-type') {
      queryText = 'Show indemnity clause variations grouped by contract type';
    }
    
    if (queryText) {
      // Add to chat history
      this.chatHistory.push({
        text: queryText,
        timestamp: new Date(),
        isProcessing: true
      });
      
      this.question = queryText;
      this.getAnswer();
    }
  }

  toggleGoverningLaw(law: string): void {
    if (law === 'Any') {
      // Clear all selections
      this.filters.governingLaws = [];
    } else {
      if (!this.filters.governingLaws) {
        this.filters.governingLaws = [];
      }
      
      const index = this.filters.governingLaws.indexOf(law);
      if (index === -1) {
        this.filters.governingLaws.push(law);
      } else {
        this.filters.governingLaws.splice(index, 1);
      }
    }
    
    // Clear selected contracts when filter changes
    this.selectedContracts = [];
  }

  isGoverningLawSelected(law: string): boolean {
    return this.filters.governingLaws ? this.filters.governingLaws.includes(law) : false;
  }

  toggleContractingParty(party: string): void {
    if (party === 'Any') {
      // Clear all selections
      this.filters.contractingParties = [];
    } else {
      if (!this.filters.contractingParties) {
        this.filters.contractingParties = [];
      }
      
      const index = this.filters.contractingParties.indexOf(party);
      if (index === -1) {
        this.filters.contractingParties.push(party);
      } else {
        this.filters.contractingParties.splice(index, 1);
      }
    }
    
    // Clear selected contracts when filter changes
    this.selectedContracts = [];
  }

  isContractingPartySelected(party: string): boolean {
    return this.filters.contractingParties ? this.filters.contractingParties.includes(party) : false;
  }
  
  getContractingPartyDisplayName(normalizedName: string): string {
    const party = this.availableContractingParties.find(p => p.normalizedName === normalizedName);
    return party ? party.displayName : normalizedName;
  }
  
  getGoverningLawDisplayName(normalizedName: string): string {
    const law = this.availableGoverningLaws.find(l => l.normalizedName === normalizedName);
    return law ? law.displayName : normalizedName;
  }
  
  // Helper methods for Clauses dropdown
  areAllClausesSelected(): boolean {
    return this.availableClausesFromStandard.length > 0 && 
           this.filters.clauses.length === this.availableClausesFromStandard.length;
  }
  
  toggleAllClauses(): void {
    if (this.areAllClausesSelected()) {
      // Deselect all
      this.filters.clauses = [];
    } else {
      // Select all
      this.filters.clauses = [...this.availableClausesFromStandard];
    }
    // Clear selected contracts when clause selection changes
    this.selectedContracts = [];
  }
  
  getClausesButtonText(): string {
    if (this.filters.clauses.length === 0) {
      return 'Select clauses to compare';
    } else if (this.areAllClausesSelected()) {
      return 'All clauses selected';
    } else {
      return `${this.filters.clauses.length} of ${this.availableClausesFromStandard.length} clauses selected`;
    }
  }

  // Comparison methods
  runComparison(): void {
    // Validate that we have required data
    if (!this.standardContractId) {
      this.toastService.warning('No Standard Contract', 'Please select a standard contract for comparison.');
      return;
    }

    if (this.selectedContracts.length === 0) {
      this.toastService.warning('No Contracts Selected', 'Please select contracts to compare against the standard.');
      return;
    }

    console.log('Running comparison with standardContractId:', this.standardContractId);
    console.log('Selected contracts:', this.selectedContracts);

    // Ensure the standard contract ID has the correct format
    // The backend expects IDs with "contract_" prefix
    let normalizedStandardId = this.standardContractId;
    if (!normalizedStandardId.startsWith('contract_')) {
      console.warn(`Standard contract ID missing prefix: ${normalizedStandardId}, adding "contract_" prefix`);
      normalizedStandardId = `contract_${normalizedStandardId}`;
    }

    // Filter out the standard contract from the comparison list
    const compareContractIds = this.selectedContracts.filter(id => 
      id !== this.standardContractId && id !== normalizedStandardId
    );
    
    if (compareContractIds.length === 0) {
      this.toastService.warning('Insufficient Contracts', 'Please select contracts other than the standard contract to compare.');
      return;
    }

    // Ensure all comparison contract IDs have the correct format
    const normalizedCompareIds = compareContractIds.map(id => {
      if (!id.startsWith('contract_')) {
        console.warn(`Compare contract ID missing prefix: ${id}, adding "contract_" prefix`);
        return `contract_${id}`;
      }
      return id;
    });

    // Determine selected clauses
    const selectedClauses = this.filters.comparisonMode === 'full' 
      ? 'all' 
      : (this.areAllClausesSelected() ? 'all' : this.filters.clauses);

    // Create the comparison request
    const request: ContractComparisonRequest = {
      standardContractId: normalizedStandardId,
      compareContractIds: normalizedCompareIds,
      comparisonMode: this.filters.comparisonMode || 'clauses',  // Default to 'clauses' if undefined
      selectedClauses: selectedClauses as string[] | 'all'  // Type assertion since we know it's valid
    };

    console.log('Comparison request:', request);

    // Start the comparison
    this.isLoadingComparison = true;
    this.showComparisonModal = true;
    
    this.contractService.compareContracts(request).subscribe({
      next: (response) => {
        this.comparisonResults = response;
        this.isLoadingComparison = false;
        
        if (response.success) {
          this.activeTab = 'comparison';
          this.toastService.success('Comparison Complete', 'Contract comparison has been completed successfully.');
        } else {
          this.toastService.error('Comparison Failed', response.error || 'An error occurred during comparison.');
        }
      },
      error: (error) => {
        console.error('Error comparing contracts:', error);
        this.isLoadingComparison = false;
        this.toastService.error('Comparison Error', 'Failed to complete contract comparison. Please try again.');
      }
    });
  }

  generateComparison(): void {
    // This is triggered by the "Generate" button in the sidebar
    if (this.filters.mode === 'realtime') {
      // For real-time mode, run the comparison immediately
      this.runComparison();
    } else {
      // For batch mode, show a confirmation dialog first
      if (confirm('This will start a batch comparison process. You will be notified when complete. Continue?')) {
        this.runComparison();
      }
    }
  }

  getRiskBadgeClass(riskLevel: string): string {
    switch (riskLevel) {
      case 'high': return 'badge-danger';
      case 'medium': return 'badge-warning';
      case 'low': return 'badge-success';
      default: return 'badge-secondary';
    }
  }

  getSimilarityBadgeClass(score: number): string {
    if (score >= 90) return 'badge-success';
    if (score >= 70) return 'badge-info';
    if (score >= 50) return 'badge-warning';
    return 'badge-danger';
  }

  getContractTitle(contractId: string): string {
    const contract = this.allContracts.find(c => c.id === contractId);
    return contract ? contract.title : contractId;
  }

  exportComparisonResults(): void {
    if (!this.comparisonResults) return;

    const exportData = {
      timestamp: new Date().toISOString(),
      standardContract: this.standardContractId,
      comparedContracts: this.comparisonResults.compareContractIds,
      mode: this.comparisonResults.comparisonMode,
      results: this.comparisonResults.results
    };

    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `contract-comparison-${new Date().getTime()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  }

  // Sort clause analyses by similarity score (ascending - least similar first)
  getSortedClauseAnalyses(analyses: ClauseAnalysis[]): ClauseAnalysis[] {
    if (!analyses) return [];
    return [...analyses].sort((a, b) => a.similarity_score - b.similarity_score);
  }

  // Toggle clause expansion
  toggleClauseExpansion(contractId: string, clauseType: string): void {
    const key = `${contractId}_${clauseType}`;
    this.expandedClauses[key] = !this.expandedClauses[key];
  }

  // Check if clause is expanded
  isClauseExpanded(contractId: string, clauseType: string): boolean {
    const key = `${contractId}_${clauseType}`;
    return this.expandedClauses[key] || false;
  }

  // Get a unique key for the clause
  getClauseKey(contractId: string, clauseType: string): string {
    return `${contractId}_${clauseType}`;
  }

  // Show clause text comparison modal
  showClauseText(clauseAnalysis: ClauseAnalysis, contractId: string): void {
    this.selectedClauseForReview = clauseAnalysis;
    this.selectedContractIdForReview = contractId;
    this.showClauseTextModal = true;
  }

  // Close clause text modal
  closeClauseTextModal(): void {
    this.showClauseTextModal = false;
    this.selectedClauseForReview = null;
    this.selectedContractIdForReview = '';
  }
}