/**
 * Upload Activity Logging Service.
 *
 * Provides activity logging for video upload, processing, and download
 * operations. Used for analytics and audit trail purposes.
 *
 * @example
 * ```typescript
 * uploadService.logActivity('video.mp4', 1024000, 'upload').subscribe();
 * ```
 */

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

/**
 * Service for logging upload-related activities.
 *
 * Records file operations for audit and analytics tracking.
 */
@Injectable({ providedIn: 'root' })
export class UploadService {
  private http = inject(HttpClient);

  /**
   * Log a file activity event.
   *
   * @param fileName - Name of the file being operated on.
   * @param fileSize - Size of the file in bytes.
   * @param action - Type of action: upload, clean, or download.
   * @returns Observable that completes when log is recorded.
   */
  logActivity(fileName: string, fileSize: number, action: 'upload' | 'clean' | 'download' = 'upload') {
    return this.http.post('/api/upload/log', {
      fileName,
      fileSize,
      action,
      status: 'success'
    });
  }
}
