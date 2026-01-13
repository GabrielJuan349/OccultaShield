import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild, computed, effect } from '@angular/core';
import { toSignal, toObservable } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { of, tap, switchMap, map, catchError, filter, concat } from 'rxjs';
import { HttpEventType } from '@angular/common/http';
import { FileDropDirective } from '../../directives/file-drop';
import { VideoService } from '#services/video.service';
import { AuthService } from '#services/auth.service';

/**
 * Validador de archivos de video
 */
class FileValidator {
  private readonly MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2GB
  private readonly MIN_FILE_SIZE = 1024; // 1KB
  private readonly VALID_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv'] as const;
  private readonly VALID_MIME_TYPES = [
    'video/mp4',
    'video/x-msvideo',
    'video/quicktime',
    'video/x-matroska'
  ] as const;

  validate(file: File): ValidationResult {
    // Validar extensión
    const extension = this.getFileExtension(file.name);
    if (!this.VALID_EXTENSIONS.includes(extension as any)) {
      return {
        valid: false,
        error: `Extensión no válida. Use: ${this.VALID_EXTENSIONS.join(', ')}`
      };
    }

    // Validar MIME type
    if (!this.isValidMimeType(file.type)) {
      return {
        valid: false,
        error: 'Tipo de archivo no válido. Solo se aceptan videos.'
      };
    }

    // Validar tamaño mínimo
    if (file.size < this.MIN_FILE_SIZE) {
      return {
        valid: false,
        error: 'El archivo es demasiado pequeño.'
      };
    }

    // Validar tamaño máximo
    if (file.size > this.MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `Archivo demasiado grande (${sizeMB} MB). Máximo: 2GB`
      };
    }

    return { valid: true };
  }

  private getFileExtension(filename: string): string {
    return filename.substring(filename.lastIndexOf('.')).toLowerCase();
  }

  private isValidMimeType(mimeType: string): boolean {
    return this.VALID_MIME_TYPES.includes(mimeType as any) || mimeType.startsWith('video/');
  }
}

interface ValidationResult {
  valid: boolean;
  error?: string;
}

@Component({
  imports: [FileDropDirective],
  templateUrl: './UploadPage.html',
  styleUrl: './UploadPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadPage {
  private readonly router = inject(Router);
  private readonly videoService = inject(VideoService);
  protected readonly authService = inject(AuthService);
  private readonly fileInput = viewChild.required<ElementRef<HTMLInputElement>>('fileInputRef');
  private readonly fileValidator = new FileValidator();

  // Signal Trigger for Resource
  protected readonly fileToUpload = signal<File | undefined>(undefined);

  // Progress Signal
  protected readonly uploadProgress = signal(0);

  // RESOURCE API implementation
  // Manual Resource Implementation using toSignal
  private readonly uploadState = toSignal(
    toObservable(this.fileToUpload).pipe(
      switchMap(file => {
        if (!file) return of({ status: 'idle' } as const);

        // Reset progress at start
        this.uploadProgress.set(0);

        return concat(
          of({ status: 'loading' as const }), // Emit loading state first
          this.videoService.uploadVideo(file).pipe(
            tap((event: any) => {
              // Update progress for upload events
              if (event.type === HttpEventType.UploadProgress && event.total) {
                const percent = Math.round(100 * event.loaded / event.total);
                this.uploadProgress.set(percent);
                console.log(`Upload progress: ${percent}%`);
              } else if (event.type === HttpEventType.Response) {
                this.uploadProgress.set(100);
                console.log('Upload complete: 100%');
              }
            }),
            filter((event: any) => event.type === HttpEventType.Response), // Wait for completion
            map((event: any) => {
              const response = event.body;

              // Validar que la respuesta tiene los campos requeridos
              if (!response || !response.video_id) {
                throw new Error('Invalid response from server: missing video_id');
              }

              return { status: 'success' as const, value: response };
            })
          )
        ).pipe(
          catchError(error => {
            console.error('Upload error detail:', error);
            this.uploadProgress.set(0);
            return of({ status: 'error' as const, error });
          })
        );
      })
    ),
    { initialValue: { status: 'idle' } as const }
  );

  protected readonly uploadResource = {
    value: computed(() => {
      const s = this.uploadState();
      return s.status === 'success' ? (s as any).value : undefined;
    }),
    error: computed(() => {
      const s = this.uploadState();
      return s.status === 'error' ? (s as any).error : undefined;
    }),
    isLoading: computed(() => {
      const s = this.uploadState();
      return s.status === 'loading';
    })
  };

  // Derived state from Resource
  protected readonly uploadStatus = computed(() => {
    if (this.uploadResource.isLoading()) return 'uploading';
    if (this.uploadResource.error()) return 'error';
    if (this.uploadResource.value()) return 'complete'; // Only complete if we have a value
    return 'idle';
  });

  protected readonly fileName = computed(() => this.fileToUpload()?.name || '');
  protected readonly errorMessage = computed(() => {
    const err = this.uploadResource.error();
    return err ? 'Error durante la subida. Verifica tu conexión.' : '';
  });

  private lastNavigatedVideoId: string | null = null;

  constructor() {
    // Auto-navigate to processing page when upload completes
    // Backend already starts processing automatically on upload
    effect(() => {
      const response = this.uploadResource.value();
      console.log('UploadPage effect - response:', response);

      // Only navigate if we have a new video_id and haven't navigated to it yet
      if (response?.video_id && response.video_id !== this.lastNavigatedVideoId) {
        console.log('Upload complete! Video ID:', response.video_id);
        console.log('Navigating to /processing/' + response.video_id);
        this.lastNavigatedVideoId = response.video_id;

        this.router.navigate(['/processing', response.video_id]).then(
          success => console.log('Navigation result:', success),
          error => console.error('Navigation error:', error)
        );
      }
    });
  }

  logout() {
    this.authService.logout();
  }

  triggerFileSelect() {
    this.fileInput().nativeElement.click();
  }

  handleFile(fileOrEvent: File | Event) {
    console.log('📂 handleFile called with:', fileOrEvent);
    let file: File | null = null;
    if (fileOrEvent instanceof File) file = fileOrEvent;
    else {
      const target = fileOrEvent.target as HTMLInputElement;
      file = target.files ? target.files[0] : null;
    }

    console.log('📄 Extracted file:', file);

    if (file) this.validateAndTrigger(file);
    else console.warn('⚠️ No file extracted');
  }

  private validateAndTrigger(file: File) {
    console.log('🔍 Validating file:', {
      name: file.name,
      type: file.type,
      size: file.size
    });

    const validation = this.fileValidator.validate(file);
    if (!validation.valid) {
      console.error('❌ Validation failed:', validation.error);
      alert(validation.error);

      // Limpiar input para permitir seleccionar el mismo archivo de nuevo
      const input = this.fileInput().nativeElement;
      if (input) {
        input.value = '';
      }
      return;
    }

    console.log('✅ File validation passed');
    this.fileToUpload.set(file);
  }
}
