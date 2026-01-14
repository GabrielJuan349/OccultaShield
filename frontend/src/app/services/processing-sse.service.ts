/**
 * ProcessingSSEService - SSE connection for video processing progress
 * Refactored for Angular 21 zoneless using signals
 */
import { Injectable, signal, computed, inject, PLATFORM_ID, DestroyRef } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Observable, Subject } from 'rxjs';
import { takeUntil, tap, share, finalize } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import type {
  ProcessingPhase,
  DetectionCount,
  PhaseChangeEvent,
  ProgressEvent,
  DetectionEvent,
  VerificationEvent,
  CompleteEvent,
  ErrorEvent,
  InitialStateEvent,
  ProcessingInternalState,
  SSEEventUnion
} from '#interface/processing-events.interface';
import type { ViolationCard } from '#interface/violation.interface';
import { AuthService } from './auth.service';
import { VideoService } from './video.service';
import { environment } from '#environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProcessingSSEService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly videoService = inject(VideoService);
  private readonly destroyRef = inject(DestroyRef);

  // === Control del stream SSE ===
  private readonly disconnect$ = new Subject<void>();
  private currentVideoId: string | null = null;
  private sseSubscription: { unsubscribe: () => void } | null = null;

  // === Estado interno como signal ===
  private readonly _state = signal<ProcessingInternalState>({
    phase: 'idle',
    progress: 0,
    message: '',
    current: 0,
    total: 0,
    detections: new Map(),
    isComplete: false,
    isError: false,
    errorMessage: null,
    redirectUrl: null,
    isConnected: false
  });

  // Timer signals
  private readonly _elapsedTime = signal<number>(0);
  private readonly _redirectCountdown = signal<number | null>(null);
  private startTime: number = 0;
  private elapsedInterval: ReturnType<typeof setInterval> | null = null;
  private countdownInterval: ReturnType<typeof setInterval> | null = null;

  // Violations (se cargan cuando llega waiting_for_review)
  private readonly _violations = signal<ViolationCard[]>([]);
  private readonly _violationsLoading = signal<boolean>(false);
  private readonly _violationsError = signal<string | null>(null);
  private violationsFetched = false;

  // Live updates
  private readonly _liveUpdates = signal<Array<{ timestamp: string; message: string; type: string }>>([]);

  // === Signals públicos (derivados del estado) ===

  readonly phase = computed(() => this._state().phase);
  readonly progress = computed(() => this._state().progress);
  readonly message = computed(() => this._state().message);
  readonly currentItem = computed(() => this._state().current);
  readonly totalItems = computed(() => this._state().total);
  readonly isComplete = computed(() => this._state().isComplete);
  readonly isError = computed(() => this._state().isError);
  readonly errorMessage = computed(() => this._state().errorMessage);
  readonly redirectUrl = computed(() => this._state().redirectUrl);
  readonly isConnected = computed(() => this._state().isConnected);
  readonly redirectCountdown = this._redirectCountdown.asReadonly();
  readonly liveUpdates = this._liveUpdates.asReadonly();

  // Violations
  readonly violations = this._violations.asReadonly();
  readonly violationsLoading = this._violationsLoading.asReadonly();
  readonly violationsError = this._violationsError.asReadonly();

  // Computed: lista de detecciones
  readonly detectionsList = computed(() => {
    return Array.from(this._state().detections.values());
  });

  readonly totalDetections = computed(() => {
    return this.detectionsList().reduce((sum, d) => sum + d.count, 0);
  });

  readonly estimatedTimeRemaining = computed(() => {
    const progress = this._state().progress;
    const elapsed = this._elapsedTime();

    if (this._state().isComplete || this._state().isError) return '—';
    if (progress === 0) return 'Calculating...';

    const estimatedTotal = (elapsed / progress) * 100;
    const remaining = Math.max(0, estimatedTotal - elapsed);

    if (remaining < 60) {
      return `~${Math.ceil(remaining)}s`;
    }
    const minutes = Math.floor(remaining / 60);
    const seconds = Math.ceil(remaining % 60);
    return `~${minutes}m ${seconds}s`;
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
    return labels[this._state().phase];
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
    return icons[this._state().phase];
  });

  // === Métodos públicos ===

  connect(videoId: string): void {
    if (!isPlatformBrowser(this.platformId)) return;

    console.log('%c[SSE] 🔌 Conectando...', 'color: #4CAF50; font-weight: bold');
    console.log(`%c[SSE] 📹 Video ID: ${videoId}`, 'color: #2196F3');

    // Desconectar conexión anterior si existe
    this.disconnect();

    // Reset estado
    this.reset();
    this.currentVideoId = videoId;
    this.startTime = Date.now();
    this.startElapsedTimer();

    // Crear y suscribirse al stream SSE
    const sseObservable = this.createSSEObservable(videoId);
    this.sseSubscription = sseObservable.pipe(
      takeUntil(this.disconnect$)
    ).subscribe();
  }

  disconnect(): void {
    console.log('%c[SSE] 🔌 Desconectando...', 'color: #FF5722');
    this.disconnect$.next();

    if (this.sseSubscription) {
      this.sseSubscription.unsubscribe();
      this.sseSubscription = null;
    }

    this.stopElapsedTimer();
    this.updateState({ isConnected: false });
  }

  reset(): void {
    console.log('%c[SSE] 🔄 Reseteando estado...', 'color: #9E9E9E');
    this._state.set({
      phase: 'idle',
      progress: 0,
      message: '',
      current: 0,
      total: 0,
      detections: new Map(),
      isComplete: false,
      isError: false,
      errorMessage: null,
      redirectUrl: null,
      isConnected: false
    });
    this._elapsedTime.set(0);
    this._redirectCountdown.set(null);
    this._liveUpdates.set([]);
    this._violations.set([]);
    this._violationsLoading.set(false);
    this._violationsError.set(null);
    this.violationsFetched = false;
    this.currentVideoId = null;
    this.stopElapsedTimer();
    this.clearCountdown();
  }

  // === Métodos privados ===

  /**
   * Crea un Observable que encapsula el EventSource SSE
   */
  private createSSEObservable(videoId: string): Observable<SSEEventUnion> {
    return new Observable<SSEEventUnion>(subscriber => {
      const apiUrl = environment.apiUrl.replace('/video', '');
      const baseUrl = `${apiUrl}/process`;
      const token = this.authService.getToken();
      const url = `${baseUrl}/${videoId}/progress${token ? `?token=${token}` : ''}`;

      console.log(`%c[SSE] 🌐 URL: ${url}`, 'color: #9C27B0');

      const eventSource = new EventSource(url);

      // Handler de conexión abierta
      eventSource.onopen = () => {
        console.log('%c[SSE] ✅ Conexión establecida', 'color: #4CAF50; font-weight: bold');
        subscriber.next({ type: 'connected' });
      };

      // Handler de errores
      eventSource.onerror = (error) => {
        console.error('%c[SSE] ❌ Error en conexión', 'color: #f44336', error);
        subscriber.next({ type: 'disconnected' });
      };

      // Handlers de eventos específicos
      const eventTypes = [
        'initial_state',
        'phase_change',
        'progress',
        'detection',
        'verification',
        'complete',
        'error',
        'heartbeat'
      ] as const;

      eventTypes.forEach(eventType => {
        eventSource.addEventListener(eventType, (event: MessageEvent) => {
          try {
            if (!event.data || event.data === 'undefined') return;
            const data = JSON.parse(event.data);
            subscriber.next({ type: eventType, data } as SSEEventUnion);
          } catch (e) {
            console.warn(`[SSE] Warning parsing ${eventType} data:`, event.data);
          }
        });
      });

      // Cleanup cuando se desuscribe
      return () => {
        console.log('%c[SSE] 🔌 Cerrando EventSource', 'color: #FF5722');
        eventSource.close();
      };
    }).pipe(
      // Procesar cada evento y actualizar estado
      tap(event => this.handleSSEEvent(event)),
      // Compartir entre múltiples suscriptores
      share(),
      // Finalize para cleanup
      finalize(() => {
        console.log('%c[SSE] 🏁 Stream finalizado', 'color: #9E9E9E');
      })
    );
  }

  /**
   * Procesa cada evento SSE y actualiza el estado
   */
  private handleSSEEvent(event: SSEEventUnion): void {
    switch (event.type) {
      case 'connected':
        // No marcamos isConnected aquí - esperamos initial_state
        break;

      case 'disconnected':
        this.updateState({ isConnected: false });
        break;

      case 'initial_state':
        this.handleInitialState(event.data);
        break;

      case 'phase_change':
        this.handlePhaseChange(event.data);
        break;

      case 'progress':
        this.handleProgress(event.data);
        break;

      case 'detection':
        this.handleDetection(event.data);
        break;

      case 'verification':
        this.handleVerification(event.data);
        break;

      case 'complete':
        this.handleComplete(event.data);
        break;

      case 'error':
        this.handleError(event.data);
        break;

      case 'heartbeat':
        console.log('%c[SSE] 💓 Heartbeat', 'color: #E91E63');
        break;
    }
  }

  private handleInitialState(data: InitialStateEvent): void {
    console.log('%c[SSE] 🎬 Estado inicial:', 'color: #00BCD4; font-weight: bold', data);

    // Convertir detections de objeto a Map
    const detectionsMap = new Map<string, DetectionCount>();
    if (data.detections) {
      Object.entries(data.detections).forEach(([type, count]) => {
        detectionsMap.set(type, {
          type,
          count: count as number,
          icon: this.getDetectionIcon(type)
        });
      });
    }

    this.updateState({
      isConnected: true,
      phase: data.phase,
      progress: data.progress || 0,
      message: data.message || '',
      current: data.current || 0,
      total: data.total || 0,
      detections: detectionsMap
    });

    this.addLiveUpdate(`Connected - ${data.phase} phase`, 'success');
  }

  private handlePhaseChange(data: PhaseChangeEvent): void {
    console.log('%c[SSE] 🔄 CAMBIO DE FASE:', 'color: #FF5722; font-weight: bold', data);

    this.updateState({
      phase: data.phase,
      message: data.message,
      progress: 0
    });

    // Detectar waiting_for_review y cargar violations
    if (data.phase === 'waiting_for_review' && !this.violationsFetched && this.currentVideoId) {
      console.log('%c[SSE] 📋 Cargando violations...', 'color: #E91E63; font-weight: bold');
      this.fetchViolations(this.currentVideoId);
    }

    this.addLiveUpdate(`Phase: ${this.phaseLabel()}`, 'phase');
  }

  private handleProgress(data: ProgressEvent): void {
    console.log(`%c[SSE] 📊 Progreso: ${data.progress}%`, 'color: #4CAF50', data);

    const currentProgress = this._state().progress;

    this.updateState({
      progress: data.progress,
      message: data.message,
      ...(data.current !== null && { current: data.current }),
      ...(data.total !== null && { total: data.total })
    });

    // Live update solo si cambio significativo (>5%)
    if (Math.abs(data.progress - currentProgress) >= 5) {
      this.addLiveUpdate(`${data.progress}% - ${data.message}`, 'progress');
    }
  }

  private handleDetection(data: DetectionEvent): void {
    console.log('%c[SSE] 🔍 DETECCIÓN:', 'color: #FF9800; font-weight: bold', data);

    this._state.update(state => {
      const newDetections = new Map(state.detections);
      newDetections.set(data.detection_type, {
        type: data.detection_type,
        count: data.count,
        icon: this.getDetectionIcon(data.detection_type)
      });

      return {
        ...state,
        detections: newDetections,
        message: data.message
      };
    });

    this.addLiveUpdate(`Found ${data.count} ${data.detection_type}`, 'detection');
  }

  private handleVerification(data: VerificationEvent): void {
    const verificationProgress = data.total_agents > 0
      ? Math.round((data.agents_completed / data.total_agents) * 100)
      : 0;

    console.log('%c[SSE] 🤖 VERIFICACIÓN:', 'color: #9C27B0; font-weight: bold', data);

    this.updateState({
      message: data.message,
      ...(data.total_agents > 0 && { progress: verificationProgress })
    });

    this.addLiveUpdate(`AI agents: ${data.agents_completed}/${data.total_agents}`, 'verification');
  }

  private handleComplete(data: CompleteEvent): void {
    console.log('%c[SSE] ✅ COMPLETADO!', 'color: #4CAF50; font-weight: bold; font-size: 16px', data);

    this.updateState({
      phase: 'completed',
      progress: 100,
      message: data.message,
      isComplete: true,
      redirectUrl: data.redirect_url
    });

    this.stopElapsedTimer();
    this.addLiveUpdate('Processing completed!', 'success');

    // Auto-redirect después de 2 segundos
    setTimeout(() => {
      if (data.redirect_url) {
        console.log(`%c[SSE] 🔀 Navegando a: ${data.redirect_url}`, 'color: #2196F3');
        this.router.navigateByUrl(data.redirect_url);
      }
    }, 2000);
  }

  private handleError(data: ErrorEvent): void {
    console.error('%c[SSE] ❌ ERROR:', 'color: #f44336; font-weight: bold', data);

    this.updateState({
      phase: 'error',
      isError: true,
      errorMessage: data.message,
      message: data.message
    });

    this.stopElapsedTimer();
    this.addLiveUpdate(`Error: ${data.message}`, 'error');

    // Iniciar countdown para redirect
    this._redirectCountdown.set(5);
    this.startCountdown();
  }

  // === Helpers ===

  private updateState(partial: Partial<ProcessingInternalState>): void {
    this._state.update(state => ({ ...state, ...partial }));
  }

  private addLiveUpdate(message: string, type: string): void {
    const timestamp = new Date().toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

    this._liveUpdates.update(updates => {
      const newUpdates = [{ timestamp, message, type }, ...updates];
      return newUpdates.slice(0, 5);
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

  private startCountdown(): void {
    this.clearCountdown();
    this.countdownInterval = setInterval(() => {
      const current = this._redirectCountdown();
      if (current !== null && current > 1) {
        this._redirectCountdown.set(current - 1);
      } else {
        this.clearCountdown();
        this._redirectCountdown.set(null);
        this.router.navigate(['/upload']);
      }
    }, 1000);
  }

  private clearCountdown(): void {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
  }

  private fetchViolations(videoId: string): void {
    if (this.violationsFetched) return;

    this.violationsFetched = true;
    this._violationsLoading.set(true);
    this._violationsError.set(null);

    this.videoService.getViolations(videoId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (response) => {
        console.log('%c[SSE] ✅ Violations recibidas:', 'color: #4CAF50', response);
        this._violations.set(response.items);
        this._violationsLoading.set(false);
        this.addLiveUpdate(`Loaded ${response.items.length} violations`, 'success');
      },
      error: (err) => {
        console.error('%c[SSE] ❌ Error cargando violations:', 'color: #f44336', err);
        this._violationsError.set(err.userMessage || 'Error loading violations');
        this._violationsLoading.set(false);
        this.violationsFetched = false; // Allow retry
        this.addLiveUpdate('Failed to load violations', 'error');
      }
    });
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
