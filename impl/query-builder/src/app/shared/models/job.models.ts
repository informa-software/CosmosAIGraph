/**
 * Job Models
 *
 * TypeScript interfaces for batch processing job queue system.
 * Mirrors the backend models in web_app/src/models/job_models.py
 */

export enum JobStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export enum JobType {
  CONTRACT_COMPARISON = 'contract_comparison',
  CONTRACT_QUERY = 'contract_query',
  CONTRACT_UPLOAD = 'contract_upload'
}

export enum ProcessingStep {
  QUEUED = 'queued',
  RETRIEVING_DATA = 'retrieving_data',
  GENERATING_PROMPT = 'generating_prompt',
  CALLING_LLM = 'calling_llm',
  PROCESSING_RESULTS = 'processing_results',
  SAVING_RESULTS = 'saving_results',
  COMPLETED = 'completed'
}

export interface JobProgress {
  current_step: ProcessingStep;
  percentage: number;
  message: string;
  current_item?: number;
  total_items?: number;
  error?: string;  // Error message if job failed
}

export interface BatchJob {
  id: string;
  job_id: string;
  job_type: JobType;
  user_id: string;
  status: JobStatus;
  priority: number;
  request: Record<string, any>;
  progress: JobProgress;
  result_id?: string;
  error_message?: string;
  error_details?: Record<string, any>;
  created_date: string;
  started_date?: string;
  completed_date?: string;
  elapsed_time?: number;
  ttl: number;
}

// API Request/Response Models

export interface SubmitJobRequest {
  request: Record<string, any>;
  priority?: number;
}

export interface SubmitJobResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobStatusResponse {
  job: BatchJob;
}

export interface UserJobsResponse {
  jobs: BatchJob[];
  total: number;
}

export interface CancelJobResponse {
  job_id: string;
  success: boolean;
  message: string;
}

export interface RetryJobResponse {
  new_job_id: string;
  original_job_id: string;
  message: string;
}

export interface DeleteJobResponse {
  job_id: string;
  success: boolean;
  message: string;
}

// SSE Event Models

export interface JobUpdateEvent {
  job_id: string;
  status: JobStatus;
  progress: JobProgress;
  result_id?: string;
  error_message?: string;
}

export interface JobsUpdateEvent {
  jobs: JobSummary[];
  counts: JobCounts;
}

export interface JobSummary {
  job_id: string;
  job_type: JobType;
  status: JobStatus;
  progress: {
    percentage: number;
    message: string;
  };
  created_date: string;
  completed_date?: string;
  elapsed_time?: number;
  result_id?: string;
  error_message?: string;
}

export interface JobCounts {
  queued: number;
  processing: number;
  completed: number;
  failed: number;
  cancelled: number;
}

export interface HeartbeatEvent {
  timestamp: string;
}

export interface ErrorEvent {
  error: string;
}

// UI Helper Models

export interface JobDisplayInfo {
  job: BatchJob;
  statusColor: 'primary' | 'accent' | 'warn' | 'success' | 'default';
  statusIcon: string;
  canCancel: boolean;
  canRetry: boolean;
  canViewResults: boolean;
  displayTitle: string;
  displayDescription: string;
}
