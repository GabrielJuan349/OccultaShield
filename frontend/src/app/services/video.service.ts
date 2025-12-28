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
    id: string;
    timestamp: string;
    threat_level: 'High' | 'Medium' | 'Low';
    description: string;
    bbox?: number[];
    detection_type: string;
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

    uploadVideo(file: File): Observable<VideoUploadResponse> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post<VideoUploadResponse>(`${this.apiUrl}/upload`, formData);
    }

    getVideoStatus(videoId: string): Observable<VideoResponse> {
        return this.http.get<VideoResponse>(`${this.apiUrl}/${videoId}/status`);
    }

    getViolations(videoId: string, page: number = 1): Observable<PaginatedResponse<ViolationCard>> {
        return this.http.get<PaginatedResponse<ViolationCard>>(`${this.apiUrl}/${videoId}/violations?page=${page}`);
    }

    submitDecisions(videoId: string, decisions: Record<string, 'anonymize' | 'keep'>): Observable<any> {
        return this.http.post(`${this.apiUrl}/${videoId}/decisions`, { decisions });
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
