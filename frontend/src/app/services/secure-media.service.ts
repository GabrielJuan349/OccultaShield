/**
 * SecureMediaService - Carga segura de imágenes y videos
 * Usa HttpClient con Authorization header en vez de tokens en URL
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpEventType } from '@angular/common/http';
import { Observable, map, shareReplay, filter, catchError, of } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SecureMediaService {
  private readonly http = inject(HttpClient);
  private readonly cache = new Map<string, Observable<string>>();

  /**
   * Carga imagen con Authorization header y devuelve blob URL
   * El interceptor añade automáticamente el header Authorization
   */
  loadImage(url: string): Observable<string> {
    // Return cached observable if exists
    if (this.cache.has(url)) {
      return this.cache.get(url)!;
    }

    const request$ = this.http.get(url, { responseType: 'blob' }).pipe(
      map(blob => URL.createObjectURL(blob)),
      catchError(err => {
        console.error('[SecureMedia] Error loading image:', url, err);
        return of(''); // Return empty string on error
      }),
      shareReplay(1)
    );

    this.cache.set(url, request$);
    return request$;
  }

  /**
   * Descarga video con Authorization header y devuelve blob URL
   * Incluye progreso de descarga
   */
  downloadVideo(url: string): Observable<{ progress: number; blobUrl?: string }> {
    return this.http.get(url, {
      responseType: 'blob',
      reportProgress: true,
      observe: 'events'
    }).pipe(
      map(event => {
        if (event.type === HttpEventType.DownloadProgress && event.total) {
          return { progress: Math.round((event.loaded / event.total) * 100) };
        }
        if (event.type === HttpEventType.Response) {
          const blobUrl = URL.createObjectURL(event.body as Blob);
          return { progress: 100, blobUrl };
        }
        return { progress: 0 };
      }),
      filter(result => result.progress > 0 || result.blobUrl !== undefined),
      catchError(err => {
        console.error('[SecureMedia] Error downloading video:', url, err);
        return of({ progress: 0, blobUrl: undefined });
      })
    );
  }

  /**
   * Limpia blob URLs para evitar memory leaks
   */
  revokeUrl(blobUrl: string): void {
    if (blobUrl?.startsWith('blob:')) {
      URL.revokeObjectURL(blobUrl);
    }
  }

  /**
   * Limpia una URL específica del caché
   */
  removeFromCache(url: string): void {
    const cached = this.cache.get(url);
    if (cached) {
      // Note: Can't revoke here as we don't have the blob URL
      this.cache.delete(url);
    }
  }

  /**
   * Limpia todo el caché
   */
  clearCache(): void {
    this.cache.clear();
  }
}
