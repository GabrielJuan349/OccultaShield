/**
 * Video Service for OccultaShield Frontend.
 *
 * Provides HTTP client methods for video upload, status polling,
 * violation retrieval, decision submission, and download operations.
 *
 * @example
 * ```typescript
 * const videoService = inject(VideoService);
 * videoService.uploadVideo(file).subscribe(event => {
 *   if (event.type === HttpEventType.Response) {
 *     console.log('Uploaded:', event.body?.video_id);
 *   }
 * });
 * ```
 */

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '#environments/environment';
import {
  VideoStatus,
  VideoResponse,
  VideoUploadResponse,
  PaginatedResponse
} from '#interface/video.interface';
import {
  ViolationCard,
  UserDecision,
  UserDecisionBatch
} from '#interface/violation.interface';

// Re-export for backwards compatibility
export { VideoStatus };
export type {
  VideoResponse,
  VideoUploadResponse,
  PaginatedResponse,
  ViolationCard,
  UserDecision,
  UserDecisionBatch
};

/**
 * Service for video-related API operations.
 *
 * Handles all HTTP communication with the backend video API including
 * upload with progress tracking, status polling, violations retrieval,
 * user decision submission, and processed video download.
 */
@Injectable({
  providedIn: 'root'
})
export class VideoService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/video`;

  /**
   * Upload a video file for GDPR compliance analysis.
   *
   * Sends the video file to the backend with progress reporting enabled.
   * Subscribe to the observable to receive upload progress events.
   *
   * @param file - The video file to upload.
   * @returns Observable emitting HttpEvents including progress and response.
   */
  uploadVideo(file: File): Observable<HttpEvent<VideoUploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<VideoUploadResponse>(
      `${this.apiUrl}/upload`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    ).pipe(
      catchError(this.handleError('uploadVideo'))
    );
  }

  /**
   * Get the current processing status of a video.
   *
   * @param videoId - Unique identifier of the video.
   * @returns Observable emitting the video status response.
   */
  getVideoStatus(videoId: string): Observable<VideoResponse> {
    return this.http.get<VideoResponse>(`${this.apiUrl}/${videoId}/status`).pipe(
      catchError(this.handleError('getVideoStatus'))
    );
  }

  /**
   * Retrieve all GDPR violations detected in a video.
   *
   * Returns a paginated list of ViolationCard objects containing
   * detection details, AI verification results, and capture images.
   *
   * @param videoId - Unique identifier of the video.
   * @returns Observable emitting paginated violation cards.
   */
  getViolations(videoId: string): Observable<PaginatedResponse<ViolationCard>> {
    return this.http.get<PaginatedResponse<ViolationCard>>(
      `${this.apiUrl}/${videoId}/violations`
    ).pipe(
      catchError(this.handleError('getViolations'))
    );
  }

  /**
   * Submit user decisions for detected violations.
   *
   * Sends the user's anonymization choices (blur, pixelate, no_modify)
   * for each violation. Triggers the anonymization process on the backend.
   *
   * @param videoId - Unique identifier of the video.
   * @param decisions - Array of UserDecision objects with verification_id and action.
   * @returns Observable that completes when decisions are submitted.
   */
  submitDecisions(videoId: string, decisions: UserDecision[]): Observable<void> {
    const payload: UserDecisionBatch = { decisions };
    return this.http.post<void>(
      `${this.apiUrl}/${videoId}/decisions`,
      payload
    ).pipe(
      catchError(this.handleError('submitDecisions'))
    );
  }

  /**
   * Download the processed (anonymized) video.
   *
   * Returns the video file as a Blob for client-side download.
   *
   * @param videoId - Unique identifier of the video.
   * @returns Observable emitting the video file as a Blob.
   */
  downloadVideo(videoId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${videoId}/download`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError('downloadVideo'))
    );
  }

  /**
   * Delete a video and all associated data.
   *
   * Removes the video from the database and cleans up storage files.
   *
   * @param videoId - Unique identifier of the video to delete.
   * @returns Observable that completes when deletion is successful.
   */
  deleteVideo(videoId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${videoId}`).pipe(
      catchError(this.handleError('deleteVideo'))
    );
  }

  /**
   * Manejo centralizado de errores HTTP
   */
  private handleError(operation: string) {
    return (error: HttpErrorResponse): Observable<never> => {
      console.error(`${operation} failed:`, {
        status: error.status,
        message: error.message,
        error: error.error
      });

      let userMessage = 'Ocurrió un error inesperado.';

      if (error.status === 0) {
        userMessage = 'No se pudo conectar al servidor. Verifica tu conexión.';
      } else if (error.status === 401) {
        userMessage = 'No estás autorizado. Por favor, inicia sesión nuevamente.';
      } else if (error.status === 404) {
        userMessage = 'Recurso no encontrado.';
      } else if (error.status === 413) {
        userMessage = 'El archivo es demasiado grande.';
      } else if (error.status === 500) {
        userMessage = 'Error del servidor. Por favor, intenta más tarde.';
      } else if (error.error?.message) {
        userMessage = error.error.message;
      }

      return throwError(() => ({
        ...error,
        userMessage
      }));
    };
  }
}
