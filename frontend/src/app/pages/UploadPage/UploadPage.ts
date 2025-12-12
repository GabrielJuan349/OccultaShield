import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { Router } from '@angular/router';
import { FileDropDirective } from '../../directives/file-drop';
import { UploadService } from '../../services/upload.service';
import { AuthService } from '../../services/auth.service';

@Component({
  imports: [FileDropDirective],
  templateUrl: './UploadPage.html',
  styleUrl: './UploadPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadPage {
  private readonly router = inject(Router);
  private readonly uploadService = inject(UploadService);
  protected readonly authService = inject(AuthService);
  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInputRef');

  // Estado reactivo
  protected uploadStatus = signal<'idle' | 'uploading' | 'complete'>('idle');
  protected uploadProgress = signal(0);
  protected fileName = signal<string>('');

  logout() {
    this.authService.logout();
  }

  // Selección manual (Click)
  triggerFileSelect() {
    this.fileInput().nativeElement.click();
  }

  // Manejador unificado (viene de la Directiva o del Input)
  handleFile(fileOrEvent: File | Event) {
    let file: File | null = null;

    if (fileOrEvent instanceof File) {
      file = fileOrEvent; // Viene del Drag & Drop (Directiva)
    } else {
      const target = fileOrEvent.target as HTMLInputElement;
      file = target.files ? target.files[0] : null; // Viene del Input manual
    }

    if (file) this.validateAndUpload(file);
  }

  private validateAndUpload(file: File) {
    if (!file.type.startsWith('video/')) {
      alert('Formato no válido. Solo se admiten videos.');
      return;
    }

    this.fileName.set(file.name);
    this.uploadStatus.set('uploading');
    this.uploadProgress.set(0);

    // Simulación de carga
    const interval = setInterval(() => {
      this.uploadProgress.update(v => Math.min(v + 10, 100));
      if (this.uploadProgress() === 100) {
        clearInterval(interval);

        // Registrar actividad en el backend
        this.uploadService.logActivity(file.name, file.size).subscribe({
          next: () => console.log('Upload logged successfully'),
          error: (err) => console.error('Failed to log upload', err)
        });

        setTimeout(() => {
          this.uploadStatus.set('complete');
          // Ya no navegamos automáticamente - el usuario usará el botón de confirmación
        }, 500);
      }
    }, 200);
  }

  // Navegar a la pantalla de procesamiento
  continueToProcessing(): void {
    this.router.navigate(['/processing'], { queryParams: { from: 'upload' } });
  }
}
