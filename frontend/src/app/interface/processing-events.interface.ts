/**
 * SSE Processing Events interfaces and types
 * Used by: ProcessingSSEService, ProcessingPage
 */

// === Processing Phases ===

export type ProcessingPhase =
  | 'idle'
  | 'uploading'
  | 'detecting'
  | 'tracking'
  | 'verifying'
  | 'saving'
  | 'waiting_for_review'
  | 'anonymizing'
  | 'completed'
  | 'error';

// === SSE Event Types ===

export interface ProgressEvent {
  event_type: 'progress';
  phase: ProcessingPhase;
  progress: number;
  current: number | null;
  total: number | null;
  message: string;
  timestamp: string;
}

export interface PhaseChangeEvent {
  event_type: 'phase_change';
  phase: ProcessingPhase;
  previous_phase: ProcessingPhase | null;
  message: string;
  estimated_time_seconds: number | null;
  timestamp: string;
}

export interface DetectionEvent {
  event_type: 'detection';
  detection_type: string;
  count: number;
  frame_number: number;
  confidence: number;
  message: string;
  timestamp: string;
}

export interface VerificationEvent {
  event_type: 'verification';
  vulnerability_id: string;
  status: string;
  agents_completed: number;
  total_agents: number;
  message: string;
  timestamp: string;
}

export interface CompleteEvent {
  event_type: 'complete';
  video_id: string;
  total_vulnerabilities: number;
  total_violations: number;
  processing_time_seconds: number;
  redirect_url: string;
  message: string;
  timestamp: string;
}

export interface ErrorEvent {
  event_type: 'error';
  code: string;
  message: string;
  details: string | null;
  recoverable: boolean;
  timestamp: string;
}

// === Union Type for all SSE Events ===

export type SSEEvent =
  | ProgressEvent
  | PhaseChangeEvent
  | DetectionEvent
  | VerificationEvent
  | CompleteEvent
  | ErrorEvent;

// === Internal Service Types ===

export interface DetectionCount {
  type: string;
  count: number;
  icon: string;
}

export interface ProcessingState {
  phase: ProcessingPhase;
  progress: number;
  message: string;
  currentItem: number;
  totalItems: number;
  detections: DetectionCount[];
  estimatedTimeRemaining: string;
  elapsedTime: number;
  isComplete: boolean;
  isError: boolean;
  errorMessage: string | null;
  redirectUrl: string | null;
}

// === Initial State Event (from SSE connection) ===

export interface InitialStateEvent {
  video_id: string;
  phase: ProcessingPhase;
  progress: number;
  current: number;
  total: number;
  message: string;
  detections: Record<string, number>;
  elapsed_seconds: number;
}

// === Internal Processing State ===

export interface ProcessingInternalState {
  phase: ProcessingPhase;
  progress: number;
  message: string;
  current: number;
  total: number;
  detections: Map<string, DetectionCount>;
  isComplete: boolean;
  isError: boolean;
  errorMessage: string | null;
  redirectUrl: string | null;
  isConnected: boolean;
}

// === SSE Event Union (for internal handling) ===

export type SSEEventUnion =
  | { type: 'initial_state'; data: InitialStateEvent }
  | { type: 'phase_change'; data: PhaseChangeEvent }
  | { type: 'progress'; data: ProgressEvent }
  | { type: 'detection'; data: DetectionEvent }
  | { type: 'verification'; data: VerificationEvent }
  | { type: 'complete'; data: CompleteEvent }
  | { type: 'error'; data: ErrorEvent }
  | { type: 'heartbeat'; data: Record<string, never> }
  | { type: 'connected' }
  | { type: 'disconnected' };

// === Live Update Entry ===

export interface LiveUpdateEntry {
  timestamp: string;
  message: string;
  type: string;
}
