import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '#environments/environment';

export interface VideoResponse {
    id: string;
    status: string;
    metadata?: any;
}

export interface VideoUploadResponse {
    video_id: string;
    status: string;
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

    uploadVideo(file: File): Observable<any> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post(`${this.apiUrl}/upload`, formData, {
            reportProgress: true,
            observe: 'events'
        });
    }

    getVideoStatus(videoId: string): Observable<VideoResponse> {
        return this.http.get<VideoResponse>(`${this.apiUrl}/${videoId}/status`);
    }

    getViolations(videoId: string, page: number = 1): Observable<PaginatedResponse<ViolationCard>> {
        return this.http.get<PaginatedResponse<ViolationCard>>(`${this.apiUrl}/${videoId}/violations?page=${page}`);
    }

    submitDecisions(videoId: string, decisions: UserDecision[]): Observable<any> {
        const payload: UserDecisionBatch = { decisions };
        return this.http.post(`${this.apiUrl}/${videoId}/decisions`, payload);
    }

    downloadVideo(videoId: string): Observable<Blob> {
        return this.http.get(`${this.apiUrl}/${videoId}/download`, {
            responseType: 'blob'
        });
    }

    deleteVideo(videoId: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/${videoId}`);
    }
}
