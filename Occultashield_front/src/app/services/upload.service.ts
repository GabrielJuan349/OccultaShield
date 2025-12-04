import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class UploadService {
  private http = inject(HttpClient);

  logActivity(fileName: string, fileSize: number, action: 'upload' | 'clean' | 'download' = 'upload') {
    return this.http.post('/api/upload/log', {
      fileName,
      fileSize,
      action,
      status: 'success'
    });
  }
}
