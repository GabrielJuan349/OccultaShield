/**
 * Video-related interfaces and types
 * Used by: VideoService, UploadPage, ProcessingPage, DownloadPage
 */

// === Enums ===

export enum VideoStatus {
  PENDING = 'pending',
  UPLOADED = 'uploaded',
  PROCESSING = 'processing',
  DETECTED = 'detected',
  VERIFIED = 'verified',
  WAITING_FOR_REVIEW = 'waiting_for_review',
  ANONYMIZING = 'anonymizing',
  COMPLETED = 'completed',
  ERROR = 'error'
}

// === Video Metadata ===

export interface VideoMetadata {
  duration?: number;
  fps?: number;
  width?: number;
  height?: number;
  createdAt: string;
  updatedAt?: string;
}

// === API Response Types ===

export interface VideoResponse {
  id: string;
  status: VideoStatus;
  metadata?: VideoMetadata;
}

export interface VideoUploadResponse {
  video_id: string;
  status: VideoStatus;
  message: string;
}

// === Pagination ===

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  has_next?: boolean;
  has_prev?: boolean;
}
