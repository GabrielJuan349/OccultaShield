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

@Injectable({
  providedIn: 'root'
})
export class VideoService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/video`;

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

  getVideoStatus(videoId: string): Observable<VideoResponse> {
    return this.http.get<VideoResponse>(`${this.apiUrl}/${videoId}/status`).pipe(
      catchError(this.handleError('getVideoStatus'))
    );
  }

  getViolations(videoId: string): Observable<PaginatedResponse<ViolationCard>> {
    return this.http.get<PaginatedResponse<ViolationCard>>(
      `${this.apiUrl}/${videoId}/violations`
    ).pipe(
      catchError(this.handleError('getViolations'))
    );
  }

  submitDecisions(videoId: string, decisions: UserDecision[]): Observable<void> {
    const payload: UserDecisionBatch = { decisions };
    return this.http.post<void>(
      `${this.apiUrl}/${videoId}/decisions`,
      payload
    ).pipe(
      catchError(this.handleError('submitDecisions'))
    );
  }

  downloadVideo(videoId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${videoId}/download`, {
      responseType: 'blob'
    }).pipe(
      catchError(this.handleError('downloadVideo'))
    );
  }

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
