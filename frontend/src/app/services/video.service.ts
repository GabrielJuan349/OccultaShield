import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '#environments/environment';

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

export interface VideoResponse {
    id: string;
    status: VideoStatus;
    metadata?: VideoMetadata;
}

export interface VideoMetadata {
    duration?: number;
    fps?: number;
    width?: number;
    height?: number;
    createdAt: string;
    updatedAt?: string;
}

export interface VideoUploadResponse {
    video_id: string;
    status: VideoStatus;
    message: string;
}

export interface ViolationCard {
    verification_id: string; // "id" in backend response
    detection_id: string; // Link to detection
    is_violation: boolean;
    severity: 'none' | 'low' | 'medium' | 'high' | 'critical';
    violated_articles: string[];
    description: string;
    recommended_action: string;
    confidence: number;
    capture_image_url: string; // URL to image
    thumbnail_url?: string;
    detection_type: string;
    timestamp?: string; // Optional if not provided or different format
    track_id?: number | string;
    frames_analyzed?: number;       // Temporal Consensus: number of frames analyzed
    frames_with_violation?: number; // Temporal Consensus: frames with positive violation
}

export interface UserDecision {
    verification_id: string;
    action: 'blur' | 'pixelate' | 'mask' | 'no_modify';
    confirmed_violation: boolean;
}

export interface UserDecisionBatch {
    decisions: UserDecision[];
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
}

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

    getViolations(videoId: string, page: number = 1): Observable<PaginatedResponse<ViolationCard>> {
        return this.http.get<PaginatedResponse<ViolationCard>>(
            `${this.apiUrl}/${videoId}/violations?page=${page}`
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
