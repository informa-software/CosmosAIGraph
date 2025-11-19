import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../services/api.service';
import { WordService } from '../services/word.service';
import { TrackChangesService } from '../services/track-changes.service';
import {
  RuleSetWithCount,
  ComplianceRule,
  EvaluationJob,
  ComplianceResultData,
  ContractEvaluationResults,
  EvaluationResult
} from '../models/compliance.models';
import {
  TrackedChangesSummary,
  TrackChangesComparisonResponse,
  ContractComparison
} from '../models/track-changes.models';
import {
  WordAddinEvaluationSession,
  CreateSessionRequest,
  UpdateSessionRequest,
  TrackChangesInfo,
  ComparisonSummary,
  ComplianceSummary
} from './models/session.models';
import {
  Contract,
  ClauseType,
  ComparisonMode,
  ComparisonResponse,
  ComparisonState
} from '../models/comparison.models';

declare const Office: any;

@Component({
  selector: 'app-word-addin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './word-addin.component.html',
  styleUrl: './word-addin.component.scss'
})
export class WordAddinComponent implements OnInit {
  // Tab state
  activeTab: 'compliance' | 'comparison' = 'compliance';

  // Office context
  isOfficeInitialized = false;

  // View state
  currentView: 'rule-set-list' | 'rule-set-detail' = 'rule-set-list';

  // Rule sets
  ruleSets: RuleSetWithCount[] = [];
  selectedRuleSet: RuleSetWithCount | null = null;
  selectedRuleSetId: string = '';
  loadingRuleSets = false;
  ruleSetError: string | null = null;

  // Rules in selected rule set
  ruleSetRules: ComplianceRule[] = [];
  loadingRules = false;
  rulesError: string | null = null;

  // Document info
  documentText: string = '';
  documentStats: { characterCount: number; wordCount: number; paragraphCount: number } | null = null;

  // Evaluation state
  isEvaluating = false;
  evaluationProgress = 0;
  evaluationError: string | null = null;
  currentJob: EvaluationJob | null = null;

  // Results
  evaluationResults: ContractEvaluationResults | null = null;
  showResults = false;
  showRuleResults = false; // Show results in rule detail view
  expandedResultId: string | null = null; // Track which result is expanded
  appliedRecommendations: Set<string> = new Set(); // Track which recommendations have been applied

  // Evidence modal
  showEvidenceModal = false;
  selectedEvidence: string[] = [];
  selectedRuleName = '';

  // Confirmation modal
  showConfirmationModal = false;
  confirmationTitle = '';
  confirmationMessage = '';
  confirmationOriginalText = '';
  confirmationProposedText = '';
  pendingRuleId: string | null = null;
  pendingInsertOperation = false; // Flag to indicate insert-at-cursor operation

  // Notification system
  notification: { message: string; type: 'success' | 'error' | 'info' | 'warning' } | null = null;

  // Settings panel
  showSettingsPanel = false;

  // Track changes state
  trackChangesEnabled = false;
  trackChangesSummary: TrackedChangesSummary | null = null;
  showComplianceChange: boolean = false; // Toggle to compare original vs current compliance
  comparisonSectionExpanded: boolean = false; // Controls if comparison section is expanded

  // Track changes results
  comparisonResults: TrackChangesComparisonResponse | null = null;
  isAnalyzingChanges = false;
  changesAnalysisProgress = 0;
  changesAnalysisError: string | null = null;

  // Compliance results for both versions
  originalComplianceResults: ContractEvaluationResults | null = null;
  revisedComplianceResults: ContractEvaluationResults | null = null;

  // Session tracking
  currentSession: WordAddinEvaluationSession | null = null;

  // ============================================================================
  // Comparison Tab State
  // ============================================================================

  // Contracts for dropdown selection
  contracts: Contract[] = [];
  loadingContracts = false;
  contractsError: string | null = null;

  // Selected standard contract
  selectedStandardContractId: string = '';
  selectedStandardContract: Contract | null = null;

  // Clauses for clause-by-clause comparison
  availableClauses: ClauseType[] = [];
  selectedClauses: string[] | 'all' = 'all';
  loadingClauses = false;
  clausesError: string | null = null;

  // Comparison mode
  comparisonMode: ComparisonMode = 'full';

  // Comparison execution state
  isComparing = false;
  comparisonProgress = 0;
  comparisonError: string | null = null;

  // Comparison results
  comparisonResults_v2: ComparisonResponse | null = null;
  showComparisonResults = false;

  // Expanded clause analysis tracking
  expandedClauseAnalyses: Set<string> = new Set();

  // Document size limit (1MB for POC)
  readonly MAX_DOCUMENT_SIZE = 1 * 1024 * 1024; // 1MB in bytes

  constructor(
    private apiService: ApiService,
    private wordService: WordService,
    private trackChangesService: TrackChangesService
  ) {}

  /**
   * Show notification message
   */
  showNotification(message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info'): void {
    this.notification = { message, type };

    // Auto-dismiss after 5 seconds for success/info, 8 seconds for warnings/errors
    const duration = (type === 'success' || type === 'info') ? 5000 : 8000;
    setTimeout(() => {
      if (this.notification?.message === message) {
        this.notification = null;
      }
    }, duration);
  }

  /**
   * Dismiss notification
   */
  dismissNotification(): void {
    this.notification = null;
  }

  async ngOnInit(): Promise<void> {
    console.log('WordAddinComponent initialized');

    // Check if we're in Office context
    if (typeof Office !== 'undefined' && Office.context) {
      if (Office.context.host === Office.HostType.Word) {
        this.isOfficeInitialized = true;
        console.log('✓ Running in Word Add-in context');

        // Check for track changes
        await this.checkTrackChanges();
      }
    }

    // Load rule sets
    await this.loadRuleSets();
  }

  /**
   * Load available rule sets from backend
   */
  async loadRuleSets(): Promise<void> {
    this.loadingRuleSets = true;
    this.ruleSetError = null;

    try {
      const ruleSetsWithCounts = await this.apiService.getRuleSetsWithCounts();
      this.ruleSets = ruleSetsWithCounts.filter(rs => rs.is_active);

      console.log(`Loaded ${this.ruleSets.length} active rule sets`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.ruleSetError = `Failed to load rule sets: ${errorMessage}`;
      console.error('Error loading rule sets:', error);
    } finally {
      this.loadingRuleSets = false;
    }
  }

  /**
   * Select a rule set and navigate to detail view
   */
  async selectRuleSet(ruleSet: RuleSetWithCount): Promise<void> {
    this.selectedRuleSet = ruleSet;
    this.selectedRuleSetId = ruleSet.id;
    this.currentView = 'rule-set-detail';

    // Load rules for this rule set
    await this.loadRuleSetRules(ruleSet.id);
  }

  /**
   * Go back to rule set list view
   */
  async backToRuleSetList(): Promise<void> {
    console.log('🔙 backToRuleSetList() - Closing results and cleaning up');

    this.currentView = 'rule-set-list';
    this.selectedRuleSet = null;
    this.selectedRuleSetId = '';
    this.ruleSetRules = [];
    this.rulesError = null;

    // Reset results state
    this.showRuleResults = false;
    this.evaluationResults = null;
    this.originalComplianceResults = null;
    this.revisedComplianceResults = null;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.expandedResultId = null;
    this.appliedRecommendations.clear();

    // Clear any content control highlights from the document
    await this.clearHighlights();
    console.log('🔙 backToRuleSetList() - Cleanup complete');
  }

  /**
   * Load rules for a specific rule set
   */
  async loadRuleSetRules(ruleSetId: string): Promise<void> {
    this.loadingRules = true;
    this.rulesError = null;
    this.ruleSetRules = [];

    try {
      // Get rule IDs for this rule set
      const ruleIds = await this.apiService.getRuleSetRules(ruleSetId);
      console.log(`Found ${ruleIds.length} rules in rule set`);

      // Fetch full rule details for each rule ID
      const rulePromises = ruleIds.map(ruleId => this.apiService.getRule(ruleId));
      this.ruleSetRules = await Promise.all(rulePromises);

      console.log(`Loaded ${this.ruleSetRules.length} rules`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.rulesError = `Failed to load rules: ${errorMessage}`;
      console.error('Error loading rules:', error);
    } finally {
      this.loadingRules = false;
    }
  }

  /**
   * Execute analysis from rule set detail view
   */
  async executeRuleSetAnalysis(): Promise<void> {
    if (!this.selectedRuleSetId) {
      this.showNotification('No rule set selected', 'warning');
      return;
    }

    // Reset previous results
    this.evaluationResults = null;
    this.originalComplianceResults = null;
    this.revisedComplianceResults = null;
    this.evaluationError = null;
    this.showRuleResults = false;
    this.expandedResultId = null;
    this.appliedRecommendations.clear();
    this.comparisonSectionExpanded = false; // Reset comparison section to collapsed

    // Clear any previous highlights before starting new analysis
    await this.clearHighlights();

    // Check if track changes is enabled and comparison is requested
    if (this.trackChangesEnabled && this.showComplianceChange) {
      // Analyze both original and current, with current as primary results
      await this.executeTrackChangesAnalysis();
    } else {
      // Analyze current document only
      await this.executeSimpleAnalysis();
    }
  }

  /**
   * Execute simple analysis against current document text
   */
  async executeSimpleAnalysis(): Promise<void> {
    this.isEvaluating = true;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.expandedResultId = null;
    this.appliedRecommendations.clear(); // Clear previously applied recommendations

    // Clear any previous highlights before starting new analysis
    await this.clearHighlights();

    try {
      // Step 1: Extract document text
      // Check if track changes is currently enabled (without updating component state)
      const trackChangesCurrentlyEnabled = await this.trackChangesService.isTrackChangesEnabled();

      if (trackChangesCurrentlyEnabled) {
        // If track changes is enabled, extract the revised text (clean version)
        console.log('Track changes enabled - extracting revised text...');
        this.documentText = await this.trackChangesService.extractRevisedText();
      } else {
        // Normal extraction
        console.log('Extracting document text...');
        this.documentText = await this.wordService.getDocumentText();
      }

      this.documentStats = await this.wordService.getDocumentStats();

      if (!this.documentText || this.documentText.trim().length === 0) {
        throw new Error('Document is empty. Please add some content first.');
      }

      this.evaluationProgress = 20;

      // Step 2: Generate a contract ID from document title or timestamp
      const props = await this.wordService.getDocumentProperties();
      const contractId = `word_${props.title.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}`;

      console.log(`Contract ID: ${contractId}`);
      this.evaluationProgress = 30;

      // Step 3: Submit for evaluation
      console.log('Submitting for evaluation...');
      const evalResponse = await this.apiService.evaluateContract({
        contract_id: contractId,
        contract_text: this.documentText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!evalResponse.job_id) {
        throw new Error('No job ID returned from evaluation request');
      }

      console.log(`Evaluation job started: ${evalResponse.job_id}`);
      this.evaluationProgress = 40;

      // Step 4: Poll for job completion
      console.log('Waiting for evaluation to complete...');
      this.currentJob = await this.apiService.pollJobCompletion(evalResponse.job_id, 2000, 60);

      this.evaluationProgress = 80;

      if (this.currentJob.status === 'failed') {
        throw new Error(`Evaluation failed: ${this.currentJob.error_message || 'Unknown error'}`);
      }

      // Step 5: Fetch results
      console.log('Fetching results...');
      this.evaluationResults = await this.apiService.getContractResults(contractId);

      this.evaluationProgress = 100;
      this.showRuleResults = true;

      console.log(`Evaluation complete: ${this.evaluationResults.results.length} results`);

      // Auto-expand and highlight if there's only one result with a recommendation
      await this.autoExpandSingleResult();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      this.evaluationError = errorMessage;
      console.error('Evaluation error:', error);
    } finally {
      this.isEvaluating = false;
    }
  }

  /**
   * Execute track changes analysis for revised version only
   */
  async executeRevisedOnlyAnalysis(): Promise<void> {
    this.isEvaluating = true;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.appliedRecommendations.clear(); // Clear previously applied recommendations

    try {
      // Extract revised text
      console.log('Extracting revised text...');
      this.evaluationProgress = 10;
      const revisedText = await this.trackChangesService.extractRevisedText();
      this.evaluationProgress = 30;

      // Generate contract ID
      const contractId = `word_revised_${Date.now()}`;

      // Submit for evaluation
      console.log('Submitting for evaluation...');
      const evalResponse = await this.apiService.evaluateContract({
        contract_id: contractId,
        contract_text: revisedText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!evalResponse.job_id) {
        throw new Error('No job ID returned from evaluation request');
      }

      this.evaluationProgress = 50;

      // Poll for completion
      this.currentJob = await this.apiService.pollJobCompletion(evalResponse.job_id, 2000, 60);
      this.evaluationProgress = 80;

      if (this.currentJob.status === 'failed') {
        throw new Error(`Evaluation failed: ${this.currentJob.error_message || 'Unknown error'}`);
      }

      // Fetch results
      this.evaluationResults = await this.apiService.getContractResults(contractId);
      this.evaluationProgress = 100;
      this.showRuleResults = true;

      console.log(`Evaluation complete: ${this.evaluationResults.results.length} results`);

      // Auto-expand and highlight if there's only one result with a recommendation
      await this.autoExpandSingleResult();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      this.evaluationError = errorMessage;
      console.error('Evaluation error:', error);
    } finally {
      this.isEvaluating = false;
    }
  }

  /**
   * Execute track changes analysis comparing both versions
   */
  async executeTrackChangesAnalysis(): Promise<void> {
    this.isEvaluating = true;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.appliedRecommendations.clear(); // Clear previously applied recommendations

    const timestamp = Date.now();
    const originalContractId = `word_original_${timestamp}`;
    const revisedContractId = `word_revised_${timestamp}`;

    try {
      // Step 1: Extract original text
      console.log('Extracting original text...');
      this.evaluationProgress = 10;
      const originalText = await this.trackChangesService.extractOriginalText();

      // Step 2: Extract revised text
      console.log('Extracting revised text...');
      this.evaluationProgress = 20;
      const revisedText = await this.trackChangesService.extractRevisedText();

      // Step 3: Submit both for evaluation
      console.log('Evaluating original version...');
      this.evaluationProgress = 30;
      const originalEvalResponse = await this.apiService.evaluateContract({
        contract_id: originalContractId,
        contract_text: originalText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!originalEvalResponse.job_id) {
        throw new Error('No job ID returned for original version evaluation');
      }

      console.log('Evaluating revised version...');
      this.evaluationProgress = 40;
      const revisedEvalResponse = await this.apiService.evaluateContract({
        contract_id: revisedContractId,
        contract_text: revisedText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!revisedEvalResponse.job_id) {
        throw new Error('No job ID returned for revised version evaluation');
      }

      // Step 4: Wait for both jobs to complete
      console.log('Waiting for evaluations to complete...');
      this.evaluationProgress = 50;
      const [originalJob, revisedJob] = await Promise.all([
        this.apiService.pollJobCompletion(originalEvalResponse.job_id, 2000, 60),
        this.apiService.pollJobCompletion(revisedEvalResponse.job_id, 2000, 60)
      ]);

      this.evaluationProgress = 80;

      // Check for failures
      if (originalJob.status === 'failed') {
        throw new Error(`Original version evaluation failed: ${originalJob.error_message}`);
      }
      if (revisedJob.status === 'failed') {
        throw new Error(`Revised version evaluation failed: ${revisedJob.error_message}`);
      }

      // Step 5: Fetch results for both versions
      console.log('Fetching compliance results...');
      this.evaluationProgress = 90;
      [this.originalComplianceResults, this.revisedComplianceResults] = await Promise.all([
        this.apiService.getContractResults(originalContractId),
        this.apiService.getContractResults(revisedContractId)
      ]);

      // Set the revised/current results as the primary results
      this.evaluationResults = this.revisedComplianceResults;

      this.evaluationProgress = 100;
      this.showRuleResults = true;

      console.log('Compliance evaluation complete for both versions');

      // Auto-expand and highlight if there's only one result with a recommendation
      await this.autoExpandSingleResult();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      this.evaluationError = errorMessage;
      console.error('Error evaluating compliance:', error);
    } finally {
      this.isEvaluating = false;
    }
  }

  /**
   * Start compliance evaluation (legacy method for old flow)
   */
  async startEvaluation(): Promise<void> {
    if (!this.selectedRuleSetId) {
      this.showNotification('Please select a rule set first', 'warning');
      return;
    }

    this.isEvaluating = true;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.showResults = false;

    try {
      // Step 1: Extract document text
      console.log('Extracting document text...');
      this.documentText = await this.wordService.getDocumentText();
      this.documentStats = await this.wordService.getDocumentStats();

      if (!this.documentText || this.documentText.trim().length === 0) {
        throw new Error('Document is empty. Please add some content first.');
      }

      this.evaluationProgress = 20;

      // Step 2: Generate a contract ID from document title or timestamp
      const props = await this.wordService.getDocumentProperties();
      const contractId = `word_${props.title.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}`;

      console.log(`Contract ID: ${contractId}`);
      this.evaluationProgress = 30;

      // Step 3: Submit for evaluation
      console.log('Submitting for evaluation...');
      const evalResponse = await this.apiService.evaluateContract({
        contract_id: contractId,
        contract_text: this.documentText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!evalResponse.job_id) {
        throw new Error('No job ID returned from evaluation request');
      }

      console.log(`Evaluation job started: ${evalResponse.job_id}`);
      this.evaluationProgress = 40;

      // Step 4: Poll for job completion
      console.log('Waiting for evaluation to complete...');
      this.currentJob = await this.apiService.pollJobCompletion(evalResponse.job_id, 2000, 60);

      this.evaluationProgress = 80;

      if (this.currentJob.status === 'failed') {
        throw new Error(`Evaluation failed: ${this.currentJob.error_message || 'Unknown error'}`);
      }

      // Step 5: Fetch results
      console.log('Fetching results...');
      this.evaluationResults = await this.apiService.getContractResults(contractId);

      this.evaluationProgress = 100;
      this.showResults = true;

      console.log(`Evaluation complete: ${this.evaluationResults.results.length} results`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      this.evaluationError = errorMessage;
      console.error('Evaluation error:', error);
    } finally {
      this.isEvaluating = false;
    }
  }

  /**
   * Get results grouped by severity
   */
  getResultsBySeverity() {
    if (!this.evaluationResults) return {};

    const grouped: Record<string, ComplianceResultData[]> = {};

    for (const result of this.evaluationResults.results) {
      // Extract severity from rule metadata (we'll need to enhance this)
      const severity = 'medium'; // Placeholder - would need to fetch rule details
      if (!grouped[severity]) {
        grouped[severity] = [];
      }
      grouped[severity].push(result);
    }

    return grouped;
  }

  /**
   * Get count by evaluation result
   */
  getResultCount(result: EvaluationResult): number {
    if (!this.evaluationResults) return 0;
    return this.evaluationResults.results.filter(r => r.evaluation_result === result).length;
  }

  /**
   * Get CSS class for evaluation result
   */
  getResultClass(result: EvaluationResult): string {
    switch (result) {
      case 'pass': return 'result-pass';
      case 'fail': return 'result-fail';
      case 'partial': return 'result-partial';
      case 'not_applicable': return 'result-na';
      default: return '';
    }
  }

  /**
   * Get icon for evaluation result
   */
  getResultIcon(result: EvaluationResult): string {
    switch (result) {
      case 'pass': return '✓';
      case 'fail': return '✗';
      case 'partial': return '⚠';
      case 'not_applicable': return '—';
      default: return '';
    }
  }

  /**
   * Reset and start new evaluation
   */
  resetEvaluation(): void {
    this.evaluationResults = null;
    this.showResults = false;
    this.evaluationError = null;
    this.evaluationProgress = 0;
    this.currentJob = null;
    this.expandedResultId = null;
  }

  /**
   * Toggle result expansion (accordion-style - only one open at a time)
   */
  toggleResult(resultId: string): void {
    if (this.expandedResultId === resultId) {
      // Collapse if already expanded
      this.expandedResultId = null;
    } else {
      // Expand this one, collapse others
      this.expandedResultId = resultId;
    }
  }

  /**
   * Check if a result is expanded
   */
  isResultExpanded(resultId: string): boolean {
    return this.expandedResultId === resultId;
  }

  /**
   * Get description of selected rule set
   */
  getSelectedRuleSetDescription(): string {
    const selected = this.ruleSets.find(rs => rs.id === this.selectedRuleSetId);
    return selected?.description || 'No description';
  }

  /**
   * Highlight evidence text in the document
   * Clears previous highlights first so only one evidence is highlighted at a time
   */
  async highlightEvidence(evidenceText: string): Promise<void> {
    console.log(`🔦 highlightEvidence() - Component method called with text: "${evidenceText.substring(0, 50)}..."`);

    if (!this.isOfficeInitialized) {
      console.warn('🔦 Cannot highlight - not running in Word');
      return;
    }

    try {
      // Highlight the selected evidence (clearing is done by caller)
      console.log('🔦 Calling wordService.highlightText()...');
      const count = await this.wordService.highlightText(evidenceText, 'yellow');
      console.log(`🔦 Highlighted ${count} occurrence(s) - SUCCESS`);

      if (count === 0) {
        console.warn('🔦 WARNING: No matches found for evidence text');
      }
    } catch (error) {
      console.error('🔦 Error highlighting text:', error);
    }
  }

  /**
   * Clear all highlights in the document
   */
  async clearHighlights(): Promise<void> {
    console.log('🧽 clearHighlights() - Component method called');

    if (!this.isOfficeInitialized) {
      console.warn('🧽 Cannot clear highlights - not running in Word');
      return;
    }

    try {
      console.log('🧽 Calling wordService.clearHighlighting()...');
      await this.wordService.clearHighlighting();
      console.log('🧽 Cleared all highlights - SUCCESS');
    } catch (error) {
      console.error('🧽 Error clearing highlights:', error);
    }
  }

  /**
   * Check if track changes is enabled in the document
   */
  async checkTrackChanges(): Promise<void> {
    try {
      this.trackChangesEnabled = await this.trackChangesService.isTrackChangesEnabled();
      if (this.trackChangesEnabled) {
        this.trackChangesSummary = await this.trackChangesService.getTrackChangesSummary();
        console.log('✓ Track changes enabled:', this.trackChangesSummary.changeTrackingMode);
      } else {
        console.log('Track changes is not enabled');
      }
    } catch (error) {
      console.error('Error checking track changes:', error);
      this.trackChangesEnabled = false;
    }
  }

  /**
   * Analyze track changes using AI-powered comparison
   */
  async analyzeChanges(): Promise<void> {
    if (!this.trackChangesEnabled) {
      this.showNotification('Track changes is not enabled in this document', 'warning');
      return;
    }

    this.isAnalyzingChanges = true;
    this.changesAnalysisProgress = 0;
    this.changesAnalysisError = null;
    this.comparisonResults = null;
    this.originalComplianceResults = null;
    this.revisedComplianceResults = null;
    this.currentSession = null;

    const timestamp = Date.now();
    const originalContractId = `word_original_${timestamp}`;
    const revisedContractId = `word_revised_${timestamp}`;

    try {
      // Step 0: Create evaluation session
      console.log('Creating evaluation session...');
      const sessionRequest: CreateSessionRequest = {
        document_title: this.documentStats ? `Word Document (${this.documentStats.characterCount} chars)` : 'Word Document',
        document_character_count: this.documentStats?.characterCount,
        track_changes_info: {
          is_enabled: this.trackChangesEnabled,
          change_tracking_mode: this.trackChangesSummary?.changeTrackingMode || 'TrackAll',
          changes_count: undefined
        },
        original_contract_id: originalContractId,
        revised_contract_id: revisedContractId,
        rule_set_id: this.selectedRuleSetId,
        rule_set_name: this.ruleSets.find(rs => rs.id === this.selectedRuleSetId)?.name,
        compliance_mode: this.showComplianceChange ? 'both' : 'revised',
        client_version: '1.0.0'
      };
      console.log('Session request:', JSON.stringify(sessionRequest, null, 2));

      try {
        this.currentSession = await this.apiService.createSession(sessionRequest);
        console.log('✅ Session created successfully:', this.currentSession.evaluation_id);
        console.log('Session details:', JSON.stringify(this.currentSession, null, 2));
      } catch (sessionError) {
        console.error('❌ Failed to create session:', sessionError);
        // Continue with analysis even if session creation fails
        this.currentSession = null;
      }

      // Step 1: Extract original text
      console.log('Extracting original text...');
      this.changesAnalysisProgress = 10;
      const originalText = await this.trackChangesService.extractOriginalText();
      console.log(`✓ Original text extracted - Length: ${originalText.length} characters`);
      console.log(`Original text preview (first 500 chars):\n${originalText.substring(0, 500)}`);

      // Step 2: Extract revised text
      console.log('Extracting revised text...');
      this.changesAnalysisProgress = 20;
      const revisedText = await this.trackChangesService.extractRevisedText();
      console.log(`✓ Revised text extracted - Length: ${revisedText.length} characters`);
      console.log(`Revised text preview (first 500 chars):\n${revisedText.substring(0, 500)}`);

      // Log character differences for debugging
      const lengthDiff = revisedText.length - originalText.length;
      console.log(`📊 Text length difference: ${lengthDiff > 0 ? '+' : ''}${lengthDiff} characters`);

      // Step 3: Call comparison API
      console.log('Sending text to comparison API...');
      console.log(`  - Original text: ${originalText.length} chars`);
      console.log(`  - Revised text: ${revisedText.length} chars`);
      this.changesAnalysisProgress = 35;
      this.comparisonResults = await this.apiService.compareTrackChanges(originalText, revisedText);
      console.log('Analysis complete:', this.comparisonResults);
      this.changesAnalysisProgress = 50;

      // Update session with comparison results
      if (this.currentSession && this.comparisonResults) {
        // Get the first comparison (word_revised vs word_original)
        const comparison = this.comparisonResults.results.comparisons[0];
        const comparisonSummary: ComparisonSummary = {
          overall_similarity_score: comparison?.overall_similarity_score || 0,
          risk_level: comparison?.risk_level || 'medium',
          critical_findings_count: comparison?.critical_findings?.length || 0,
          missing_clauses_count: comparison?.missing_clauses?.length || 0,
          additional_clauses_count: comparison?.additional_clauses?.length || 0
        };
        await this.apiService.updateSession(this.currentSession.evaluation_id, {
          comparison_completed: true,
          comparison_summary: comparisonSummary
        });
        console.log('Session updated with comparison results');
      }

      // Step 4: If user enabled compliance change comparison, run compliance evaluation on both versions
      if (this.showComplianceChange) {
        await this.runComplianceOnBothVersions(originalContractId, revisedContractId, originalText, revisedText);
        this.changesAnalysisProgress = 100;
      } else {
        this.changesAnalysisProgress = 100;
      }

      // Update session status to completed
      if (this.currentSession) {
        await this.apiService.updateSession(this.currentSession.evaluation_id, {
          status: 'completed'
        });
        console.log('Session marked as completed');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      this.changesAnalysisError = errorMessage;
      console.error('Error analyzing changes:', error);

      // Update session status to failed
      if (this.currentSession) {
        try {
          await this.apiService.updateSession(this.currentSession.evaluation_id, {
            status: 'failed',
            comparison_error: errorMessage
          });
          console.log('Session marked as failed');
        } catch (updateError) {
          console.error('Failed to update session status:', updateError);
        }
      }
    } finally {
      this.isAnalyzingChanges = false;
    }
  }

  /**
   * Run compliance evaluation on both original and revised versions
   */
  private async runComplianceOnBothVersions(
    originalContractId: string,
    revisedContractId: string,
    originalText: string,
    revisedText: string
  ): Promise<void> {
    if (!this.selectedRuleSetId) {
      console.warn('No rule set selected, skipping compliance evaluation');
      return;
    }

    console.log('Running compliance evaluation on both versions...');

    try {
      // Submit original version for evaluation
      console.log('Evaluating original version...');
      this.changesAnalysisProgress = 55;
      const originalEvalResponse = await this.apiService.evaluateContract({
        contract_id: originalContractId,
        contract_text: originalText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!originalEvalResponse.job_id) {
        throw new Error('No job ID returned for original version evaluation');
      }

      // Submit revised version for evaluation
      console.log('Evaluating revised version...');
      this.changesAnalysisProgress = 60;
      const revisedEvalResponse = await this.apiService.evaluateContract({
        contract_id: revisedContractId,
        contract_text: revisedText,
        rule_set_id: this.selectedRuleSetId,
        async_mode: true
      });

      if (!revisedEvalResponse.job_id) {
        throw new Error('No job ID returned for revised version evaluation');
      }

      // Update session with job IDs
      if (this.currentSession) {
        await this.apiService.updateSession(this.currentSession.evaluation_id, {
          original_evaluation_job_id: originalEvalResponse.job_id,
          revised_evaluation_job_id: revisedEvalResponse.job_id
        });
        console.log('Session updated with job IDs');
      }

      // Wait for both jobs to complete
      console.log('Waiting for evaluations to complete...');
      this.changesAnalysisProgress = 65;
      const [originalJob, revisedJob] = await Promise.all([
        this.apiService.pollJobCompletion(originalEvalResponse.job_id, 2000, 60),
        this.apiService.pollJobCompletion(revisedEvalResponse.job_id, 2000, 60)
      ]);

      this.changesAnalysisProgress = 85;

      // Check for failures
      if (originalJob.status === 'failed') {
        throw new Error(`Original version evaluation failed: ${originalJob.error_message}`);
      }
      if (revisedJob.status === 'failed') {
        throw new Error(`Revised version evaluation failed: ${revisedJob.error_message}`);
      }

      // Fetch results for both versions
      console.log('Fetching compliance results...');
      this.changesAnalysisProgress = 90;
      [this.originalComplianceResults, this.revisedComplianceResults] = await Promise.all([
        this.apiService.getContractResults(originalContractId),
        this.apiService.getContractResults(revisedContractId)
      ]);

      this.changesAnalysisProgress = 95;

      // Update session with compliance results
      if (this.currentSession && this.originalComplianceResults && this.revisedComplianceResults) {
        const complianceSummary: ComplianceSummary = {
          original_pass: this.originalComplianceResults.summary.pass || 0,
          original_fail: this.originalComplianceResults.summary.fail || 0,
          original_partial: this.originalComplianceResults.summary.partial || 0,
          revised_pass: this.revisedComplianceResults.summary.pass || 0,
          revised_fail: this.revisedComplianceResults.summary.fail || 0,
          revised_partial: this.revisedComplianceResults.summary.partial || 0,
          changed_rules_count: this.countChangedRules()
        };
        await this.apiService.updateSession(this.currentSession.evaluation_id, {
          compliance_completed: true,
          compliance_summary: complianceSummary
        });
        console.log('Session updated with compliance summary');
      }

      console.log('Compliance evaluation complete for both versions');
    } catch (error) {
      console.error('Error evaluating compliance on both versions:', error);

      // Update session with compliance error
      if (this.currentSession) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown compliance error';
        await this.apiService.updateSession(this.currentSession.evaluation_id, {
          compliance_error: errorMessage
        });
      }

      throw error; // Re-throw to be caught by analyzeChanges
    }
  }

  /**
   * Count the number of rules with different compliance results between original and revised
   */
  private countChangedRules(): number {
    if (!this.originalComplianceResults || !this.revisedComplianceResults) {
      return 0;
    }

    let changedCount = 0;
    const originalResults = this.originalComplianceResults.results;
    const revisedResults = this.revisedComplianceResults.results;

    for (const ruleId in originalResults) {
      if (revisedResults[ruleId]) {
        const originalStatus = originalResults[ruleId].evaluation_result;
        const revisedStatus = revisedResults[ruleId].evaluation_result;
        if (originalStatus !== revisedStatus) {
          changedCount++;
        }
      }
    }

    return changedCount;
  }

  /**
   * Get compliance delta between original and revised versions for a specific rule
   */
  getComplianceDelta(ruleId: string): { original: EvaluationResult | null; revised: EvaluationResult | null; changed: boolean } {
    if (!this.originalComplianceResults || !this.revisedComplianceResults) {
      return { original: null, revised: null, changed: false };
    }

    const originalResult = this.originalComplianceResults.results.find(r => r.rule_id === ruleId);
    const revisedResult = this.revisedComplianceResults.results.find(r => r.rule_id === ruleId);

    return {
      original: originalResult?.evaluation_result || null,
      revised: revisedResult?.evaluation_result || null,
      changed: originalResult?.evaluation_result !== revisedResult?.evaluation_result
    };
  }

  /**
   * Get count of rules where compliance changed
   */
  getChangedComplianceCount(): number {
    if (!this.originalComplianceResults || !this.revisedComplianceResults) {
      return 0;
    }

    let count = 0;
    for (const result of this.originalComplianceResults.results) {
      const delta = this.getComplianceDelta(result.rule_id);
      if (delta.changed) {
        count++;
      }
    }
    return count;
  }

  /**
   * Switch active tab
   */
  async setActiveTab(tab: 'compliance' | 'comparison'): Promise<void> {
    await this.onTabChange(tab);
  }

  /**
   * Get CSS class for rule severity badge
   */
  getSeverityClass(severity: string): string {
    return `severity-${severity}`;
  }

  /**
   * Check if showing dual version results (original + revised)
   */
  hasDualResults(): boolean {
    return this.originalComplianceResults !== null && this.revisedComplianceResults !== null;
  }

  /**
   * Get result for a specific rule from single version results
   */
  getRuleResult(ruleId: string): ComplianceResultData | null {
    if (!this.evaluationResults) return null;
    return this.evaluationResults.results.find(r => r.rule_id === ruleId) || null;
  }

  /**
   * Get original version result for a specific rule
   */
  getOriginalRuleResult(ruleId: string): ComplianceResultData | null {
    if (!this.originalComplianceResults) return null;
    return this.originalComplianceResults.results.find(r => r.rule_id === ruleId) || null;
  }

  /**
   * Get revised version result for a specific rule
   */
  getRevisedRuleResult(ruleId: string): ComplianceResultData | null {
    if (!this.revisedComplianceResults) return null;
    return this.revisedComplianceResults.results.find(r => r.rule_id === ruleId) || null;
  }

  /**
   * Check if compliance result changed between original and current
   */
  hasComplianceChanged(ruleId: string): boolean {
    const original = this.getOriginalRuleResult(ruleId);
    const revised = this.getRevisedRuleResult(ruleId);

    if (!original || !revised) return false;

    return original.evaluation_result !== revised.evaluation_result;
  }

  /**
   * Check if any compliance results changed
   */
  hasAnyComplianceChanges(): boolean {
    if (!this.hasDualResults()) return false;

    return this.ruleSetRules.some(rule => this.hasComplianceChanged(rule.id));
  }

  /**
   * Get count of rules with changed compliance status
   */
  getChangedComplianceRuleCount(): number {
    if (!this.hasDualResults()) return 0;

    return this.ruleSetRules.filter(rule => this.hasComplianceChanged(rule.id)).length;
  }

  /**
   * Toggle expansion of comparison section
   */
  toggleComparisonSection(): void {
    this.comparisonSectionExpanded = !this.comparisonSectionExpanded;
  }

  /**
   * Toggle expansion of rule result to show/hide recommendation
   */
  async onRuleResultClick(ruleId: string): Promise<void> {
    console.log(`👆 onRuleResultClick() - Rule ID: ${ruleId}`);
    console.log(`👆 Currently expanded rule ID: ${this.expandedResultId}`);

    // Only expand if result is fail or partial (has recommendation)
    const result = this.getRuleResult(ruleId);
    if (result && (result.evaluation_result === 'fail' || result.evaluation_result === 'partial')) {
      console.log(`👆 Result evaluation: ${result.evaluation_result}`);
      console.log(`👆 Has recommendation: ${!!result.recommendation}`);

      // Toggle expansion
      if (this.expandedResultId === ruleId) {
        // Clicking the same rule - collapse it
        console.log('👆 Same rule clicked - collapsing');
        this.expandedResultId = null;
        await this.clearHighlights();
      } else {
        // Clicking a different rule - clear old highlights first, then highlight new text
        console.log('👆 Different rule clicked - switching highlights');
        this.expandedResultId = ruleId;

        // Clear any existing highlights from previous rule
        console.log('👆 Clearing existing highlights...');
        await this.clearHighlights();
        console.log('👆 Existing highlights cleared');

        // Highlight the original text when expanding
        if (result.recommendation?.original_text) {
          console.log(`👆 Highlighting new text: "${result.recommendation.original_text.substring(0, 50)}..."`);
          await this.highlightEvidence(result.recommendation.original_text);
          console.log('👆 New text highlighted');
        }
      }
    } else {
      console.log('👆 No action - result does not have recommendation');
    }
    console.log('👆 onRuleResultClick() - Complete');
  }

  /**
   * Show evidence modal for a rule result
   */
  showEvidence(ruleId: string, event: Event): void {
    event.stopPropagation(); // Prevent card click from toggling expansion
    const result = this.getRuleResult(ruleId);
    if (result && result.evidence && result.evidence.length > 0) {
      this.selectedEvidence = result.evidence;
      this.selectedRuleName = result.rule_name;
      this.showEvidenceModal = true;
    }
  }

  /**
   * Close evidence modal
   */
  closeEvidenceModal(): void {
    this.showEvidenceModal = false;
    this.selectedEvidence = [];
    this.selectedRuleName = '';
  }

  /**
   * Apply recommendation by replacing text in the document
   */
  async applyRecommendation(ruleId: string, event: Event): Promise<void> {
    event.stopPropagation(); // Prevent card click from toggling expansion

    if (!this.isOfficeInitialized) {
      this.showNotification('Cannot apply changes - not running in Word', 'error');
      return;
    }

    // Get the result (works for both single and dual results)
    let result = this.getRuleResult(ruleId);

    // If we're in dual mode and didn't find result, try revised version
    if (!result && this.hasDualResults()) {
      result = this.getRevisedRuleResult(ruleId);
    }

    if (!result?.recommendation) {
      console.error('No recommendation available for rule:', ruleId);
      this.showNotification('No recommendation available', 'warning');
      return;
    }

    const { original_text, proposed_text } = result.recommendation;

    if (!original_text || !proposed_text) {
      console.error('Incomplete recommendation data:', result.recommendation);
      this.showNotification('Incomplete recommendation data', 'error');
      return;
    }

    // Show confirmation modal instead of using window.confirm
    this.confirmationTitle = 'Apply Recommendation?';
    this.confirmationMessage = 'This will replace the following text in your document:';
    this.confirmationOriginalText = original_text;
    this.confirmationProposedText = proposed_text;
    this.pendingRuleId = ruleId;
    this.showConfirmationModal = true;
  }

  /**
   * Confirm and apply the recommendation
   */
  async confirmApplyRecommendation(): Promise<void> {
    if (!this.pendingRuleId) return;

    try {
      console.log('Applying recommendation for rule:', this.pendingRuleId);

      // Try to replace text within content controls first
      const count = await this.wordService.replaceTextInContentControl(
        this.confirmationOriginalText,
        this.confirmationProposedText
      );

      if (count > 0) {
        console.log(`Successfully replaced ${count} occurrence(s) in content control`);

        // Mark recommendation as applied
        this.appliedRecommendations.add(this.pendingRuleId);

        // Don't clear highlights - the content control remains with the new text

        // Close modal
        this.closeConfirmationModal();

        // Show success message
        this.showNotification(
          `Successfully applied fix (${count} occurrence(s) replaced). The content control remains visible with the updated text.`,
          'success'
        );
      } else {
        // Text not found in content controls - offer to insert at cursor
        console.warn('Text not found in content control - offering to insert at cursor');

        // Update the modal to show insert dialog (don't close first - that would clear the text values)
        this.confirmationTitle = 'Text Not Found - Insert at Cursor?';
        this.confirmationMessage = 'The original text was not found in the document. Would you like to insert the recommended text at the current cursor position or replace any selected text?';
        // confirmationOriginalText and confirmationProposedText remain set from the initial modal
        // Modal is already showing, just update to insert mode

        // Set a flag to indicate this is an insert operation
        this.pendingInsertOperation = true;
      }
    } catch (error) {
      console.error('Error applying recommendation:', error);
      this.closeConfirmationModal();
      this.showNotification(
        'Failed to apply recommendation: ' + (error instanceof Error ? error.message : 'Unknown error'),
        'error'
      );
    }
  }

  /**
   * Confirm and insert the recommendation at cursor (when text not found)
   */
  async confirmInsertAtCursor(): Promise<void> {
    if (!this.pendingRuleId) return;

    try {
      console.log('Inserting recommendation at cursor for rule:', this.pendingRuleId);

      // Insert the proposed text at cursor or replace selection
      const result = await this.wordService.insertTextAtSelection(this.confirmationProposedText);

      // Mark recommendation as applied
      this.appliedRecommendations.add(this.pendingRuleId);

      // Close modal
      this.closeConfirmationModal();
      this.pendingInsertOperation = false;

      // Show success message
      if (result.replaced) {
        this.showNotification(
          `Successfully applied fix. Replaced selected text: "${result.selectedText.substring(0, 50)}${result.selectedText.length > 50 ? '...' : ''}"`,
          'success'
        );
      } else {
        this.showNotification(
          'Successfully applied fix. Text inserted at cursor position.',
          'success'
        );
      }
    } catch (error) {
      console.error('Error inserting recommendation:', error);
      this.closeConfirmationModal();
      this.pendingInsertOperation = false;
      this.showNotification(
        'Failed to insert recommendation: ' + (error instanceof Error ? error.message : 'Unknown error'),
        'error'
      );
    }
  }

  /**
   * Close confirmation modal
   */
  closeConfirmationModal(): void {
    this.showConfirmationModal = false;
    this.confirmationTitle = '';
    this.confirmationMessage = '';
    this.confirmationOriginalText = '';
    this.confirmationProposedText = '';
    this.pendingRuleId = null;
    this.pendingInsertOperation = false;
  }

  /**
   * Check if a recommendation has been applied
   */
  isRecommendationApplied(ruleId: string): boolean {
    return this.appliedRecommendations.has(ruleId);
  }

  /**
   * Reset after evaluation error to allow retry
   */
  async resetEvaluationError(): Promise<void> {
    console.log('🔄 resetEvaluationError() - Resetting error state');
    this.evaluationError = null;
    this.showRuleResults = false;
    this.expandedResultId = null;

    // Clear any content control highlights from the document
    await this.clearHighlights();
    console.log('🔄 resetEvaluationError() - Reset complete');
  }

  /**
   * Auto-expand and highlight the first result if there's only one rule with a recommendation
   */
  async autoExpandSingleResult(): Promise<void> {
    if (!this.isOfficeInitialized) {
      console.log('Not in Office context, skipping auto-expand');
      return;
    }

    // Get all results with recommendations (fail or partial)
    const resultsWithRecommendations = this.ruleSetRules.filter(rule => {
      const result = this.getRuleResult(rule.id);
      return result &&
             (result.evaluation_result === 'fail' || result.evaluation_result === 'partial') &&
             result.recommendation?.original_text;
    });

    // If there's exactly one result with a recommendation, auto-expand and highlight it
    if (resultsWithRecommendations.length === 1) {
      const rule = resultsWithRecommendations[0];
      const result = this.getRuleResult(rule.id);

      if (result?.recommendation?.original_text) {
        console.log('Auto-expanding single result with recommendation:', rule.id);
        this.expandedResultId = rule.id;

        // Highlight the text
        try {
          await this.highlightEvidence(result.recommendation.original_text);
        } catch (error) {
          console.error('Error auto-highlighting text:', error);
        }
      }
    }
  }

  /**
   * Toggle settings panel
   */
  toggleSettings(): void {
    this.showSettingsPanel = !this.showSettingsPanel;
  }

  /**
   * Debug method to examine Word object structure
   */
  async debugWordObject(): Promise<void> {
    console.log('🔍 ========== DEBUG: Word Object Examination ==========');

    const isApiSupported = Office.context.requirements.isSetSupported('WordApi', '1.4');
    console.log('WordApi 1.4 supported:', isApiSupported);
    const isDesktopApiSupported = Office.context.requirements.isSetSupported('WordApiDesktop', '1.4');
    console.log('WordApiDesktop 1.4 supported:', isDesktopApiSupported);
// if (isSupported) {
//   await Word.run(async (context) => {
//     const revisionsFilter = context.document.revisionsFilter;
//     console.log('revisionsFilter exists:', revisionsFilter !== undefined);
    
//     if (revisionsFilter) {
//       revisionsFilter.load('view');
//       await context.sync();
//       console.log('Current view:', revisionsFilter.view);
//     }
//   });
// }
    if (!this.wordService.isWordAvailable()) {
      console.error('❌ Word is not available');
      this.showNotification('Word is not available in browser mode', 'error');
      return;
    }

    // Log Office.js version information
    console.log('\n--- Office.js Version Information ---');
    try {
      if (typeof Office !== 'undefined') {
        console.log('✅ Office object available');
        console.log('📋 Office.context.platform:', (Office.context as any).platform);
        console.log('📋 Office.context.host:', (Office.context as any).host);
        console.log('📋 Office.context.diagnostics:', (Office.context as any).diagnostics);
      }
      if (typeof Word !== 'undefined') {
        console.log('✅ Word object available');
        console.log('📋 Word.ApiSet:', (Word as any).ApiSet);
        console.log('📋 Word object keys:', Object.keys(Word).slice(0, 20));
      }
    } catch (error) {
      console.log('❌ Error getting version info:', error);
    }
     
    try {
      await Word.run(async (context: any) => {
        const doc = context.document;

        // Log available properties on document
        console.log('📄 Document object:', doc);
        console.log('📄 Document properties:', Object.keys(doc));

        // Try to load various properties
        console.log('\n--- Loading document properties  ---');
        doc.load('properties');
        //const revisionsFilter = doc.revisionsFilter; 
        //revisionsFilter.load('markup,view');
        //await context.sync();
        //console.log(doc.revisionsFilter);

        // Log document properties
        console.log('✅ Document properties loaded:', doc.properties);
        if (doc.properties) {
          const props = doc.properties;
          props.load('title,subject,author,keywords,comments,lastModified');
          await context.sync();
          console.log('📋 Title:', props.title);
          console.log('📋 Subject:', props.subject);
          console.log('📋 Author:', props.author);
          console.log('📋 Keywords:', props.keywords);
          console.log('📋 Comments:', props.comments);
          console.log('📋 Last Modified:', props.lastModified);
        }

        // Check if revisionsFilter exists
        console.log('\n--- Checking revisionsFilter ---');
        if (doc.revisionsFilter) {
          console.log('✅ doc.revisionsFilter exists:', doc.revisionsFilter);
          console.log('📋 revisionsFilter properties:', Object.keys(doc.revisionsFilter));

          // Try to load revisionsFilter properties
          const revisionsFilter = doc.revisionsFilter;
          revisionsFilter.load();
          await context.sync();

          console.log('✅ Loaded revisionsFilter:', revisionsFilter);
          console.log('📋 markup property:', revisionsFilter.markup);
          console.log('📋 view property:', revisionsFilter.view);
        } else {
          console.log('❌ doc.revisionsFilter does not exist');
        }

        // Check if changeTrackingMode exists
        console.log('\n--- Checking changeTrackingMode ---');
        try {
          doc.load('changeTrackingMode');
          await context.sync();
          console.log('✅ changeTrackingMode:', doc.changeTrackingMode);
        } catch (error) {
          console.log('❌ changeTrackingMode not available:', error);
        }

        // Check other document properties
        console.log('\n--- Checking other document properties ---');
        try {
          doc.load('saved,contentControls');
          await context.sync();
          console.log('✅ Document saved:', doc.saved);
          console.log('✅ Content controls count:', doc.contentControls?.items?.length || 0);
        } catch (error) {
          console.log('❌ Error loading additional properties:', error);
        }

        // Try to access body properties
        console.log('\n--- Checking body properties ---');
        try {
          const body = doc.body;
          body.load('text');
          await context.sync();
          console.log('✅ Body text length:', body.text?.length || 0);
          console.log('✅ Body text preview:', body.text?.substring(0, 100) + '...');
        } catch (error) {
          console.log('❌ Error loading body properties:', error);
        }

        // Check Word enums
        console.log('\n--- Checking Word Enums ---');
        console.log('Word.RevisionsMarkup:', (Word as any).RevisionsMarkup);
        console.log('Word.RevisionsView:', (Word as any).RevisionsView);
        console.log('Word.ChangeTrackingMode:', (Word as any).ChangeTrackingMode);

        this.showNotification('Debug info logged to console. Press F12 to view.', 'info');
      });
    } catch (error) {
      console.error('❌ Error during debug:', error);
      this.showNotification('Debug error: ' + (error instanceof Error ? error.message : 'Unknown error'), 'error');
    }

    console.log('🔍 ========== END DEBUG ==========');
  }

  // ============================================================================
  // Comparison Tab Methods
  // ============================================================================

  /**
   * Load contracts for dropdown selection
   */
  async loadContracts(): Promise<void> {
    this.loadingContracts = true;
    this.contractsError = null;

    try {
      this.contracts = await this.apiService.getContracts();
      console.log(`Loaded ${this.contracts.length} contracts for comparison`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.contractsError = `Failed to load contracts: ${errorMessage}`;
      console.error('Error loading contracts:', error);
      this.showNotification(this.contractsError, 'error');
    } finally {
      this.loadingContracts = false;
    }
  }

  /**
   * Handle standard contract selection
   */
  async onStandardContractSelected(contractId: string): Promise<void> {
    this.selectedStandardContractId = contractId;
    this.selectedStandardContract = this.contracts.find(c => c.id === contractId) || null;

    // Reset clause selection
    this.availableClauses = [];
    this.selectedClauses = 'all';
    this.clausesError = null;

    // Load clauses for this contract if in clause mode
    if (this.comparisonMode === 'clauses' && contractId) {
      await this.loadContractClauses(contractId);
    }
  }

  /**
   * Load available clauses for selected contract
   */
  async loadContractClauses(contractId: string): Promise<void> {
    this.loadingClauses = true;
    this.clausesError = null;

    try {
      this.availableClauses = await this.apiService.getContractClauses(contractId);
      console.log(`Loaded ${this.availableClauses.length} clauses for contract ${contractId}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.clausesError = `Failed to load clauses: ${errorMessage}`;
      console.error('Error loading clauses:', error);
      this.showNotification(this.clausesError, 'warning');
    } finally {
      this.loadingClauses = false;
    }
  }

  /**
   * Handle comparison mode change (full | clauses)
   */
  async onComparisonModeChanged(mode: ComparisonMode): Promise<void> {
    this.comparisonMode = mode;

    // Load clauses if switching to clause mode and contract is selected
    if (mode === 'clauses' && this.selectedStandardContractId && this.availableClauses.length === 0) {
      await this.loadContractClauses(this.selectedStandardContractId);
    }
  }

  /**
   * Toggle clause selection
   * @param clauseDisplayName - The display name of the clause (e.g., "Governing Law")
   */
  toggleClauseSelection(clauseDisplayName: string): void {
    if (this.selectedClauses === 'all') {
      this.selectedClauses = [clauseDisplayName];
    } else {
      const index = this.selectedClauses.indexOf(clauseDisplayName);
      if (index > -1) {
        this.selectedClauses.splice(index, 1);
        // If none selected, revert to 'all'
        if (this.selectedClauses.length === 0) {
          this.selectedClauses = 'all';
        }
      } else {
        this.selectedClauses.push(clauseDisplayName);
      }
    }
  }

  /**
   * Select all clauses
   */
  selectAllClauses(): void {
    this.selectedClauses = 'all';
  }

  /**
   * Deselect all clauses
   */
  deselectAllClauses(): void {
    this.selectedClauses = [];
  }

  /**
   * Check if a clause is selected
   * @param clauseDisplayName - The display name of the clause (e.g., "Governing Law")
   */
  isClauseSelected(clauseDisplayName: string): boolean {
    if (this.selectedClauses === 'all') return true;
    return this.selectedClauses.includes(clauseDisplayName);
  }

  /**
   * Check if document size is within limit
   */
  async checkDocumentSize(): Promise<{ valid: boolean; size: number; error?: string }> {
    try {
      // Get current document text (use revised if track changes enabled)
      const trackChangesCurrentlyEnabled = await this.trackChangesService.isTrackChangesEnabled();
      let documentText: string;

      if (trackChangesCurrentlyEnabled) {
        documentText = await this.trackChangesService.extractRevisedText();
      } else {
        documentText = await this.wordService.getDocumentText();
      }

      const sizeInBytes = new TextEncoder().encode(documentText).length;

      if (sizeInBytes > this.MAX_DOCUMENT_SIZE) {
        return {
          valid: false,
          size: sizeInBytes,
          error: `Document size (${(sizeInBytes / 1024 / 1024).toFixed(2)}MB) exceeds 1MB limit. Coming Soon: support for larger documents.`
        };
      }

      return { valid: true, size: sizeInBytes };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return {
        valid: false,
        size: 0,
        error: `Failed to check document size: ${errorMessage}`
      };
    }
  }

  /**
   * Execute Compare with Original (track changes mode)
   */
  async executeCompareWithOriginal(): Promise<void> {
    console.log('🔄 Starting Compare with Original...');

    // Reset state
    this.isComparing = true;
    this.comparisonProgress = 0;
    this.comparisonError = null;
    this.comparisonResults_v2 = null;
    this.showComparisonResults = false;

    try {
      // Step 1: Check document size
      this.comparisonProgress = 10;
      const sizeCheck = await this.checkDocumentSize();
      if (!sizeCheck.valid) {
        throw new Error(sizeCheck.error || 'Document too large');
      }

      // Step 2: Extract original and revised text
      this.comparisonProgress = 20;
      console.log('Extracting original and revised text...');
      const originalText = await this.trackChangesService.extractOriginalText();
      const revisedText = await this.trackChangesService.extractRevisedText();

      if (!originalText || originalText.trim().length === 0) {
        throw new Error('Original document text is empty');
      }
      if (!revisedText || revisedText.trim().length === 0) {
        throw new Error('Revised document text is empty');
      }

      console.log(`Original text length: ${originalText.length} chars`);
      console.log(`Revised text length: ${revisedText.length} chars`);
      this.comparisonProgress = 40;

      // Step 3: Submit for comparison
      console.log('Submitting for comparison...');
      this.comparisonResults_v2 = await this.apiService.compareWithOriginal({
        originalText,
        revisedText,
        comparisonMode: 'full' // Track changes always uses full mode
      });

      this.comparisonProgress = 90;

      // Step 4: Display results
      console.log('Comparison complete!', this.comparisonResults_v2);
      this.showComparisonResults = true;
      this.comparisonProgress = 100;
      this.showNotification('Document comparison completed successfully', 'success');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.comparisonError = `Comparison failed: ${errorMessage}`;
      console.error('Error during comparison:', error);
      this.showNotification(this.comparisonError, 'error');
    } finally {
      this.isComparing = false;
    }
  }

  /**
   * Execute Compare with Standard contract
   */
  async executeCompareWithStandard(): Promise<void> {
    console.log('🔄 Starting Compare with Standard...');

    // Validation
    if (!this.selectedStandardContractId) {
      this.showNotification('Please select a standard contract', 'warning');
      return;
    }

    if (this.comparisonMode === 'clauses' && this.selectedClauses !== 'all' && this.selectedClauses.length === 0) {
      this.showNotification('Please select at least one clause or use "All Clauses"', 'warning');
      return;
    }

    // Reset state
    this.isComparing = true;
    this.comparisonProgress = 0;
    this.comparisonError = null;
    this.comparisonResults_v2 = null;
    this.showComparisonResults = false;

    try {
      // Step 1: Check document size
      this.comparisonProgress = 10;
      const sizeCheck = await this.checkDocumentSize();
      if (!sizeCheck.valid) {
        throw new Error(sizeCheck.error || 'Document too large');
      }

      // Step 2: Extract current document text
      this.comparisonProgress = 20;
      console.log('Extracting current document text...');
      const trackChangesCurrentlyEnabled = await this.trackChangesService.isTrackChangesEnabled();
      let currentDocumentText: string;

      if (trackChangesCurrentlyEnabled) {
        // Use revised text if track changes is enabled
        currentDocumentText = await this.trackChangesService.extractRevisedText();
      } else {
        currentDocumentText = await this.wordService.getDocumentText();
      }

      if (!currentDocumentText || currentDocumentText.trim().length === 0) {
        throw new Error('Current document text is empty');
      }

      console.log(`Current document text length: ${currentDocumentText.length} chars`);
      this.comparisonProgress = 40;

      // Step 3: Submit for comparison
      console.log('Submitting for comparison...');
      console.log(`Mode: ${this.comparisonMode}`);
      console.log(`Selected clauses:`, this.selectedClauses);

      this.comparisonResults_v2 = await this.apiService.compareWithStandard({
        standardContractId: this.selectedStandardContractId,
        currentDocumentText,
        comparisonMode: this.comparisonMode,
        selectedClauses: this.selectedClauses
      });

      this.comparisonProgress = 90;

      // Step 4: Display results
      console.log('Comparison complete!', this.comparisonResults_v2);
      this.showComparisonResults = true;
      this.comparisonProgress = 100;
      this.showNotification('Document comparison completed successfully', 'success');

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.comparisonError = `Comparison failed: ${errorMessage}`;
      console.error('Error during comparison:', error);
      this.showNotification(this.comparisonError, 'error');
    } finally {
      this.isComparing = false;
    }
  }

  /**
   * Check if Compare with Original is available
   * Only available when track changes is enabled and there are changes
   */
  canCompareWithOriginal(): boolean {
    return this.trackChangesEnabled;
  }

  /**
   * Clear comparison results and reset state
   */
  clearComparisonResults(): void {
    this.comparisonResults_v2 = null;
    this.showComparisonResults = false;
    this.comparisonError = null;
    this.comparisonProgress = 0;
  }

  /**
   * Reset comparison tab to initial state
   */
  resetComparisonTab(): void {
    this.clearComparisonResults();
    this.selectedStandardContractId = '';
    this.selectedStandardContract = null;
    this.availableClauses = [];
    this.selectedClauses = 'all';
    this.comparisonMode = 'full';
  }

  /**
   * Handle tab change - load contracts when switching to comparison tab
   */
  async onTabChange(tab: 'compliance' | 'comparison'): Promise<void> {
    this.activeTab = tab;

    if (tab === 'comparison') {
      // Load contracts if not already loaded
      if (this.contracts.length === 0 && !this.loadingContracts) {
        await this.loadContracts();
      }
      // Check track changes status
      await this.checkTrackChanges();
    }
  }

  // ============================================================================
  // Comparison Results Display Methods
  // ============================================================================

  /**
   * Get CSS class for similarity score
   */
  getSimilarityClass(score: number): string {
    if (score >= 0.8) return 'similarity-high';
    if (score >= 0.5) return 'similarity-medium';
    return 'similarity-low';
  }

  /**
   * Toggle clause analysis expansion
   */
  toggleClauseAnalysis(clauseType: string): void {
    if (this.expandedClauseAnalyses.has(clauseType)) {
      this.expandedClauseAnalyses.delete(clauseType);
    } else {
      this.expandedClauseAnalyses.add(clauseType);
    }
  }

  /**
   * Check if clause analysis is expanded
   */
  isClauseAnalysisExpanded(clauseType: string): boolean {
    return this.expandedClauseAnalyses.has(clauseType);
  }

  /**
   * Insert clause from library (placeholder for future implementation)
   */
  insertClauseFromLibrary(clauseType: string): void {
    this.showNotification(
      `Coming Soon: Insert ${clauseType} clause from library`,
      'info'
    );
    console.log(`Insert clause requested: ${clauseType}`);
  }
}
