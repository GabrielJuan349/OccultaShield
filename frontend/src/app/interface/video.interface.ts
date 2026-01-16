/**
 * Video-related interfaces and types for OccultaShield.
 *
 * This module defines the core data structures for video processing,
 * including status tracking, metadata, and API response types.
 *
 * @module video.interface
 * @see VideoService - Primary consumer of these types
 * @see UploadPage - Video upload workflow
 * @see ProcessingPage - Status monitoring
 * @see DownloadPage - Processed video retrieval
 */

// === Enums ===

/**
 * Video processing status values.
 *
 * Tracks the lifecycle of a video through the OccultaShield pipeline:
 * PENDING → UPLOADED → PROCESSING → DETECTED → VERIFIED → WAITING_FOR_REVIEW → ANONYMIZING → COMPLETED
 */
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

/**
 * Technical metadata extracted from an uploaded video.
 *
 * @property duration - Video duration in seconds.
 * @property fps - Frames per second.
 * @property width - Video width in pixels.
 * @property height - Video height in pixels.
 * @property createdAt - ISO timestamp of upload.
 * @property updatedAt - ISO timestamp of last status change.
 */
export interface VideoMetadata {
  duration?: number;
  fps?: number;
  width?: number;
  height?: number;
  createdAt: string;
  updatedAt?: string;
}

// === API Response Types ===

/**
 * Response from video status endpoint.
 *
 * @property id - Unique video identifier (e.g., "vid_abc123").
 * @property status - Current processing status.
 * @property metadata - Optional technical video metadata.
 */
export interface VideoResponse {
  id: string;
  status: VideoStatus;
  metadata?: VideoMetadata;
}

/**
 * Response from video upload endpoint.
 *
 * @property video_id - Assigned video identifier for tracking.
 * @property status - Initial status (typically PENDING).
 * @property message - Human-readable status message.
 */
export interface VideoUploadResponse {
  video_id: string;
  status: VideoStatus;
  message: string;
}

// === Pagination ===

/**
 * Generic paginated response wrapper.
 *
 * @template T - Type of items in the response.
 * @property items - Array of items for current page.
 * @property total - Total number of items across all pages.
 * @property page - Current page number (1-indexed).
 * @property page_size - Number of items per page.
 * @property total_pages - Total number of pages.
 * @property has_next - Whether more pages exist after current.
 * @property has_prev - Whether pages exist before current.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
  has_next?: boolean;
  has_prev?: boolean;
}
