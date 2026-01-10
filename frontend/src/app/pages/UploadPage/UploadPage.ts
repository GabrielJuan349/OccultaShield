import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild, computed, effect } from '@angular/core';
import { toSignal, toObservable } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { of, tap, switchMap, map, startWith, catchError, filter } from 'rxjs';
import { HttpEventType } from '@angular/common/http';
import { FileDropDirective } from '../../directives/file-drop';
import { VideoService } from '#services/video.service';
import { AuthService } from '#services/auth.service';

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
        this.uploadProgress.set(10);
        return this.videoService.uploadVideo(file).pipe(
          tap((event: any) => {
            if (event.type === HttpEventType.UploadProgress && event.total) {
              const percent = Math.round(100 * event.loaded / event.total);
              this.uploadProgress.set(percent);
            }
          }),
          filter((event: any) => event.type === HttpEventType.Response), // Wait for completion
          map((event: any) => ({ status: 'success' as const, value: event.body })),
          startWith({ status: 'loading' as const }),
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

  constructor() {
    // Effect removed or kept? The user code had an effect to navigate automatically.
    // The template suggests a "Continue to Processing" button appears on completion.
    // If I keep the effect, the button might be redundant or the user might want manual transition.
    // I will comment out the auto-navigation effect for now to let the button work, 
    // OR keep it if the template allows both. 
    // Actually, the template shows: @if (uploadStatus() === 'complete') { button... }
    // If the effect automatically navigates, the button will barely be seen.
    // I will disable the auto-navigation effect to let the button logic take over.
    /*
    effect(() => {
      const response = this.uploadResource.value() as any;
      if (response && response.video_id) {
        // this.router.navigate(['/processing', response.video_id]);
      }
    });
    */
  }

  continueToProcessing() {
    const response = this.uploadResource.value();
    if (response && response.video_id) {
      this.router.navigate(['/processing', response.video_id]);
    }
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
    console.log('🔍 Validating file type:', file.type);
    if (!file.type.startsWith('video/')) {
      console.error('❌ Invalid file type');
      alert('Formato no válido. Solo se admiten videos.');
      return;
    }
    // Set signal -> Triggers Resource
    console.log('✅ File valid, setting signal');
    this.fileToUpload.set(file);
  }
}
