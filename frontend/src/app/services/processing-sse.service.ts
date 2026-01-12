// services/processing-sse.service.ts
import { Injectable, signal, computed, inject, PLATFORM_ID, OnDestroy } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { environment } from '#environments/environment';
import {
  ProcessingPhase,
  ProcessingState,
  SSEEvent,
  DetectionCount,
  PhaseChangeEvent,
  ProgressEvent,
  DetectionEvent,
  VerificationEvent,
  CompleteEvent,
  ErrorEvent
} from '#interface/processing-events';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class ProcessingSSEService implements OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);

  private eventSource: EventSource | null = null;
  private startTime: number = 0;
  private elapsedInterval: ReturnType<typeof setInterval> | null = null;

  // ===== SIGNALS (Estado Reactivo) =====

  private readonly _phase = signal<ProcessingPhase>('idle');
  private readonly _progress = signal<number>(0);
  private readonly _message = signal<string>('');
  private readonly _currentItem = signal<number>(0);
  private readonly _totalItems = signal<number>(0);
  private readonly _detections = signal<Map<string, DetectionCount>>(new Map());
  private readonly _estimatedTime = signal<number | null>(null);
  private readonly _elapsedTime = signal<number>(0);
  private readonly _isComplete = signal<boolean>(false);
  private readonly _isError = signal<boolean>(false);
  private readonly _errorMessage = signal<string | null>(null);
  private readonly _redirectUrl = signal<string | null>(null);
  private readonly _isConnected = signal<boolean>(false);

  // ===== SIGNALS PÚBLICOS (ReadOnly) =====

  readonly phase = this._phase.asReadonly();
  readonly progress = this._progress.asReadonly();
  readonly message = this._message.asReadonly();
  readonly currentItem = this._currentItem.asReadonly();
  readonly totalItems = this._totalItems.asReadonly();
  readonly isComplete = this._isComplete.asReadonly();
  readonly isError = this._isError.asReadonly();
  readonly errorMessage = this._errorMessage.asReadonly();
  readonly redirectUrl = this._redirectUrl.asReadonly();
  readonly isConnected = this._isConnected.asReadonly();

  // ===== COMPUTED SIGNALS =====

  readonly detectionsList = computed(() => {
    return Array.from(this._detections().values());
  });

  readonly totalDetections = computed(() => {
    return this.detectionsList().reduce((sum, d) => sum + d.count, 0);
  });

  readonly estimatedTimeRemaining = computed(() => {
    const estimated = this._estimatedTime();
    const elapsed = this._elapsedTime();

    if (!estimated || this._isComplete()) return 'Calculating...';

    const remaining = Math.max(0, estimated - elapsed);

    if (remaining < 60) {
      return `${Math.ceil(remaining)} seconds`;
    } else {
      const minutes = Math.floor(remaining / 60);
      const seconds = Math.ceil(remaining % 60);
      return `${minutes}m ${seconds}s`;
    }
  });

  readonly elapsedTimeFormatted = computed(() => {
    const elapsed = this._elapsedTime();
    const minutes = Math.floor(elapsed / 60);
    const seconds = Math.floor(elapsed % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });

  readonly phaseLabel = computed(() => {
    const labels: Record<ProcessingPhase, string> = {
      'idle': 'Waiting...',
      'uploading': 'Uploading Video',
      'detecting': 'Detecting Objects',
      'tracking': 'Tracking Objects',
      'verifying': 'AI Verification',
      'saving': 'Saving Results',
      'waiting_for_review': 'Waiting for Review',
      'anonymizing': 'Anonymizing Video',
      'completed': 'Complete!',
      'error': 'Error'
    };
    return labels[this._phase()];
  });

  readonly phaseIcon = computed(() => {
    const icons: Record<ProcessingPhase, string> = {
      'idle': 'hourglass_empty',
      'uploading': 'cloud_upload',
      'detecting': 'search',
      'tracking': 'timeline',
      'verifying': 'psychology',
      'saving': 'save',
      'waiting_for_review': 'rate_review',
      'anonymizing': 'edit',
      'completed': 'check_circle',
      'error': 'error'
    };
    return icons[this._phase()];
  });

  // ===== MÉTODOS PÚBLICOS =====

  connect(videoId: string): void {
    if (!isPlatformBrowser(this.platformId)) return;

    this.disconnect();
    this.reset();

    const baseUrl = `${environment.apiUrl}/process`;
    const token = this.authService.getToken();
    const url = `${baseUrl}/${videoId}/progress${token ? `?token=${token}` : ''}`;

    this.startTime = Date.now();
    this.startElapsedTimer();

    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      console.log('SSE Connected');
      this._isConnected.set(true);
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      this._isConnected.set(false);

      // Intentar reconectar después de 3 segundos
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        setTimeout(() => this.connect(videoId), 3000);
      }
    };

    // Registrar handlers para cada tipo de evento
    this.registerEventHandlers();
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this._isConnected.set(false);
    this.stopElapsedTimer();
  }

  reset(): void {
    this._phase.set('idle');
    this._progress.set(0);
    this._message.set('');
    this._currentItem.set(0);
    this._totalItems.set(0);
    this._detections.set(new Map());
    this._estimatedTime.set(null);
    this._elapsedTime.set(0);
    this._isComplete.set(false);
    this._isError.set(false);
    this._errorMessage.set(null);
    this._redirectUrl.set(null);
  }

  ngOnDestroy(): void {
    this.disconnect();
  }

  // ===== MÉTODOS PRIVADOS =====

  private registerEventHandlers(): void {
    if (!this.eventSource) return;

    // Estado inicial
    this.eventSource.addEventListener('initial_state', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      this._phase.set(data.phase);
      this._progress.set(data.progress || 0);
      this._message.set(data.message || '');
      this._currentItem.set(data.current || 0);
      this._totalItems.set(data.total || 0);
    });

    // Cambio de fase
    this.eventSource.addEventListener('phase_change', (event: MessageEvent) => {
      const data: PhaseChangeEvent = JSON.parse(event.data);
      this._phase.set(data.phase);
      this._message.set(data.message);
      this._progress.set(0);  // Reset en cambio de fase

      if (data.estimated_time_seconds) {
        this._estimatedTime.set(data.estimated_time_seconds);
      }

      // Auto-redirect to review if waiting
      // Note: Components can also react to this, but this is a global rule
      // However, we can't easily get videoId here from event data if it's not present.
      // But we passed videoId to connect(), so we could store it.
    });

    // Progreso
    this.eventSource.addEventListener('progress', (event: MessageEvent) => {
      const data: ProgressEvent = JSON.parse(event.data);
      this._progress.set(data.progress);
      this._message.set(data.message);

      if (data.current !== null) this._currentItem.set(data.current);
      if (data.total !== null) this._totalItems.set(data.total);
    });

    // Detección
    this.eventSource.addEventListener('detection', (event: MessageEvent) => {
      const data: DetectionEvent = JSON.parse(event.data);

      this._detections.update(map => {
        const newMap = new Map(map);
        newMap.set(data.detection_type, {
          type: data.detection_type,
          count: data.count,
          icon: this.getDetectionIcon(data.detection_type)
        });
        return newMap;
      });

      this._message.set(data.message);
    });

    // Verificación
    this.eventSource.addEventListener('verification', (event: MessageEvent) => {
      const data: VerificationEvent = JSON.parse(event.data);
      this._message.set(data.message);

      // Calcular progreso de verificación
      if (data.total_agents > 0) {
        const verificationProgress = (data.agents_completed / data.total_agents) * 100;
        this._progress.set(Math.round(verificationProgress));
      }
    });

    // Completado
    this.eventSource.addEventListener('complete', (event: MessageEvent) => {
      const data: CompleteEvent = JSON.parse(event.data);

      this._phase.set('completed');
      this._progress.set(100);
      this._message.set(data.message);
      this._isComplete.set(true);
      this._redirectUrl.set(data.redirect_url);

      this.stopElapsedTimer();

      // Auto-redirect después de 2 segundos
      setTimeout(() => {
        if (data.redirect_url) {
          this.router.navigateByUrl(data.redirect_url);
        }
      }, 2000);
    });

    // Error
    this.eventSource.addEventListener('error', (event: MessageEvent) => {
      const data: ErrorEvent = JSON.parse(event.data);

      this._phase.set('error');
      this._isError.set(true);
      this._errorMessage.set(data.message);
      this._message.set(data.message);

      this.stopElapsedTimer();
      this.disconnect();
    });

    // Heartbeat
    this.eventSource.addEventListener('heartbeat', () => {
      console.debug('SSE Heartbeat received');
    });
  }

  private startElapsedTimer(): void {
    this.stopElapsedTimer();

    this.elapsedInterval = setInterval(() => {
      const elapsed = (Date.now() - this.startTime) / 1000;
      this._elapsedTime.set(elapsed);
    }, 1000);
  }

  private stopElapsedTimer(): void {
    if (this.elapsedInterval) {
      clearInterval(this.elapsedInterval);
      this.elapsedInterval = null;
    }
  }

  private getDetectionIcon(type: string): string {
    const icons: Record<string, string> = {
      'face': 'face',
      'license_plate': 'directions_car',
      'person': 'person',
      'body_exposed': 'accessibility',
      'minor': 'child_care'
    };
    return icons[type] || 'help_outline';
  }
}
