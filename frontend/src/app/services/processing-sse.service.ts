// services/processing-sse.service.ts
import { Injectable, signal, computed, inject, PLATFORM_ID, OnDestroy } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
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
import { VideoService, ViolationCard } from './video.service';
import { environment } from '#environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ProcessingSSEService implements OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly videoService = inject(VideoService);

  private eventSource: EventSource | null = null;
  private startTime: number = 0;
  private elapsedInterval: ReturnType<typeof setInterval> | null = null;
  private redirectTimeout: ReturnType<typeof setTimeout> | null = null;
  private countdownInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;
  private currentVideoId: string | null = null;
  private violationsFetched: boolean = false;  // Track if we've already fetched violations

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
  private readonly _redirectCountdown = signal<number | null>(null);

  // Violations from verification module (fetched when waiting_for_review)
  private readonly _violations = signal<ViolationCard[]>([]);
  private readonly _violationsLoading = signal<boolean>(false);
  private readonly _violationsError = signal<string | null>(null);

  // Live updates (últimos 5 eventos)
  private readonly _liveUpdates = signal<Array<{ timestamp: string, message: string, type: string }>>([]);

  // Para cálculo dinámico de tiempo restante
  private lastProgressUpdate: number = 0;
  private lastProgressValue: number = 0;

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
  readonly redirectCountdown = this._redirectCountdown.asReadonly();
  readonly liveUpdates = this._liveUpdates.asReadonly();

  // Violations signals (public readonly)
  readonly violations = this._violations.asReadonly();
  readonly violationsLoading = this._violationsLoading.asReadonly();
  readonly violationsError = this._violationsError.asReadonly();

  // ===== COMPUTED SIGNALS =====

  readonly detectionsList = computed(() => {
    return Array.from(this._detections().values());
  });

  readonly totalDetections = computed(() => {
    return this.detectionsList().reduce((sum, d) => sum + d.count, 0);
  });

  readonly estimatedTimeRemaining = computed(() => {
    const progress = this._progress();
    const elapsed = this._elapsedTime();

    if (this._isComplete() || this._isError()) return '—';
    if (progress === 0) return 'Calculating...';

    // Cálculo dinámico: estimar basado en velocidad actual
    // Si tenemos X% completado en Y segundos, entonces 100% tomará (100/X)*Y segundos
    const estimatedTotal = (elapsed / progress) * 100;
    const remaining = Math.max(0, estimatedTotal - elapsed);

    if (remaining < 60) {
      return `~${Math.ceil(remaining)}s`;
    } else {
      const minutes = Math.floor(remaining / 60);
      const seconds = Math.ceil(remaining % 60);
      return `~${minutes}m ${seconds}s`;
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

    // Si es una nueva conexión (diferente video), resetear intentos
    if (this.currentVideoId !== videoId) {
      this.reconnectAttempts = 0;
      this.currentVideoId = videoId;
      console.log('%c[SSE] 🔌 Iniciando conexión...', 'color: #4CAF50; font-weight: bold');
      console.log(`%c[SSE] 📹 Video ID: ${videoId}`, 'color: #2196F3');
    } else {
      this.reconnectAttempts++;
      console.log(`%c[SSE] 🔄 Reintento #${this.reconnectAttempts}/${this.maxReconnectAttempts}`, 'color: #FF9800; font-weight: bold');
    }

    // Si excedemos los reintentos, mostrar error
    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      console.error('%c[SSE] ❌ Máximo de reintentos alcanzado', 'color: #f44336; font-weight: bold');
      this._isError.set(true);
      this._errorMessage.set('No se pudo conectar con el servidor después de varios intentos');
      return;
    }

    this.disconnect();
    if (this.reconnectAttempts === 0) {
      this.reset(); // Solo reset en primera conexión
    }

    // Construir URL del SSE usando el environment
    // Reemplazar /video con /process para el endpoint de SSE
    const apiUrl = environment.apiUrl.replace('/video', '');
    const baseUrl = `${apiUrl}/process`;
    const token = this.authService.getToken();
    const url = `${baseUrl}/${videoId}/progress${token ? `?token=${token}` : ''}`;

    console.log(`%c[SSE] 🌐 URL: ${url}`, 'color: #9C27B0');
    console.log(`%c[SSE] 🔑 Token presente: ${!!token}`, 'color: #FF9800');

    if (this.reconnectAttempts === 0) {
      this.startTime = Date.now();
      this.startElapsedTimer();
    }

    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        console.log('%c[SSE] ✅ Conexión establecida exitosamente', 'color: #4CAF50; font-weight: bold; font-size: 14px');
        this._isConnected.set(true);
        this.reconnectAttempts = 0; // Reset exitoso
      };

      this.eventSource.onerror = (error) => {
        console.error('%c[SSE] ❌ Error en la conexión', 'color: #f44336; font-weight: bold', error);
        console.log(`%c[SSE] 🔄 Estado de conexión: ${this.eventSource?.readyState}`, 'color: #FF5722');
        this._isConnected.set(false);

        // Intentar reconectar con backoff exponencial limitado
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          // Backoff: 500ms, 1s, 1.5s, 2s, 2.5s, luego siempre 3s
          const delay = Math.min(500 + (this.reconnectAttempts * 500), 3000);
          console.log(`%c[SSE] ⏳ Reintentando conexión en ${delay}ms...`, 'color: #FFC107');

          // Limpiar timeout anterior si existe
          if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
          }

          this.reconnectTimeout = setTimeout(() => {
            console.log('%c[SSE] 🔄 Reconectando...', 'color: #03A9F4; font-weight: bold');
            this.connect(videoId);
          }, delay);
        }
      };

      // Registrar handlers para cada tipo de evento
      this.registerEventHandlers();
    } catch (error) {
      console.error('%c[SSE] 💥 Error al crear EventSource', 'color: #f44336; font-weight: bold', error);
      this._isError.set(true);
      this._errorMessage.set('Error al conectar con el servidor de eventos');
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      console.log('%c[SSE] 🔌 Cerrando conexión...', 'color: #FF5722');
      this.eventSource.close();
      this.eventSource = null;
      console.log('%c[SSE] ✅ Conexión cerrada', 'color: #9E9E9E');
    }
    this._isConnected.set(false);
    this.stopElapsedTimer();
  }

  reset(): void {
    console.log('%c[SSE] 🔄 Reseteando estado...', 'color: #9E9E9E');
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
    this._redirectCountdown.set(null);
    this._liveUpdates.set([]);
    // Reset violations state
    this._violations.set([]);
    this._violationsLoading.set(false);
    this._violationsError.set(null);
    this.violationsFetched = false;
    this.reconnectAttempts = 0;
    this.currentVideoId = null;
    this.lastProgressUpdate = 0;
    this.lastProgressValue = 0;
  }

  // Agregar evento a live updates (máximo 5)
  private addLiveUpdate(message: string, type: string = 'info'): void {
    const timestamp = new Date().toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

    this._liveUpdates.update(updates => {
      const newUpdates = [{ timestamp, message, type }, ...updates];
      return newUpdates.slice(0, 5); // Mantener solo los últimos 5
    });
  }

  ngOnDestroy(): void {
    this.disconnect();
    this.stopElapsedTimer();

    // Limpiar todos los timers para evitar memory leaks
    if (this.redirectTimeout) {
      clearTimeout(this.redirectTimeout);
      this.redirectTimeout = null;
    }

    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  // ===== MÉTODOS PRIVADOS =====

  private registerEventHandlers(): void {
    if (!this.eventSource) return;

    console.log('%c[SSE] 📡 Registrando handlers de eventos', 'color: #673AB7; font-weight: bold');

    // Estado inicial
    this.eventSource.addEventListener('initial_state', (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      console.log('%c[SSE] 🎬 Estado inicial recibido:', 'color: #00BCD4; font-weight: bold', {
        fase: data.phase,
        progreso: `${data.progress || 0}%`,
        mensaje: data.message || '',
        items: `${data.current || 0}/${data.total || 0}`
      });
      this._phase.set(data.phase);
      this._progress.set(data.progress || 0);
      this._message.set(data.message || '');
      this._currentItem.set(data.current || 0);
      this._totalItems.set(data.total || 0);

      // 🎯 Si el estado inicial ya es waiting_for_review, hacer fetch de violations
      if (data.phase === 'waiting_for_review' && this.currentVideoId && !this.violationsFetched) {
        console.log('%c[SSE] 📋 Initial state waiting_for_review - Solicitando violations...', 'color: #E91E63; font-weight: bold');
        this.fetchViolations(this.currentVideoId);
      }

      // Live update
      this.addLiveUpdate(`Connected - ${data.phase} phase`, 'success');
    });

    // Cambio de fase
    this.eventSource.addEventListener('phase_change', (event: MessageEvent) => {
      const data: PhaseChangeEvent = JSON.parse(event.data);
      console.log('%c[SSE] 🔄 CAMBIO DE FASE:', 'color: #FF5722; font-weight: bold; font-size: 14px', {
        nuevaFase: data.phase,
        mensaje: data.message,
        tiempoEstimado: data.estimated_time_seconds ? `${data.estimated_time_seconds}s` : 'N/A'
      });
      this._phase.set(data.phase);
      this._message.set(data.message);
      this._progress.set(0);  // Reset en cambio de fase

      if (data.estimated_time_seconds) {
        this._estimatedTime.set(data.estimated_time_seconds);
      }

      // 🎯 Detectar waiting_for_review y hacer petición de violations
      if (data.phase === 'waiting_for_review' && this.currentVideoId && !this.violationsFetched) {
        console.log('%c[SSE] 📋 Phase waiting_for_review detectada - Solicitando violations...', 'color: #E91E63; font-weight: bold');
        this.fetchViolations(this.currentVideoId);
      }

      // Live update
      this.addLiveUpdate(`Phase: ${this.phaseLabel()}`, 'phase');
    });

    // Progreso
    this.eventSource.addEventListener('progress', (event: MessageEvent) => {
      const data: ProgressEvent = JSON.parse(event.data);
      console.log(`%c[SSE] 📊 Progreso: ${data.progress}% - ${data.message}`, 'color: #4CAF50', {
        items: data.current !== null && data.total !== null ? `${data.current}/${data.total}` : 'N/A'
      });

      const currentProgress = this._progress();
      this._progress.set(data.progress);
      this._message.set(data.message);

      if (data.current !== null) this._currentItem.set(data.current);
      if (data.total !== null) this._totalItems.set(data.total);

      // Live update solo si el progreso cambió significativamente (>5%)
      if (Math.abs(data.progress - currentProgress) >= 5) {
        this.addLiveUpdate(`${data.progress}% - ${data.message}`, 'progress');
      }
    });

    // Detección
    this.eventSource.addEventListener('detection', (event: MessageEvent) => {
      const data: DetectionEvent = JSON.parse(event.data);
      console.log('%c[SSE] 🔍 DETECCIÓN:', 'color: #FF9800; font-weight: bold', {
        tipo: data.detection_type,
        cantidad: data.count,
        mensaje: data.message
      });

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

      // Live update
      this.addLiveUpdate(`Found ${data.count} ${data.detection_type}`, 'detection');
    });

    // Verificación
    this.eventSource.addEventListener('verification', (event: MessageEvent) => {
      const data: VerificationEvent = JSON.parse(event.data);
      const verificationProgress = data.total_agents > 0 ?
        Math.round((data.agents_completed / data.total_agents) * 100) : 0;

      console.log('%c[SSE] 🤖 VERIFICACIÓN IA:', 'color: #9C27B0; font-weight: bold', {
        agentes: `${data.agents_completed}/${data.total_agents}`,
        progreso: `${verificationProgress}%`,
        mensaje: data.message
      });

      this._message.set(data.message);

      // Calcular progreso de verificación
      if (data.total_agents > 0) {
        this._progress.set(verificationProgress);
      }

      // Live update
      this.addLiveUpdate(`AI agents: ${data.agents_completed}/${data.total_agents}`, 'verification');
    });

    // Completado
    this.eventSource.addEventListener('complete', (event: MessageEvent) => {
      const data: CompleteEvent = JSON.parse(event.data);
      console.log('%c[SSE] ✅ PROCESO COMPLETADO!', 'color: #4CAF50; font-weight: bold; font-size: 16px; background: #C8E6C9; padding: 5px 10px;', {
        mensaje: data.message,
        urlRedirect: data.redirect_url
      });

      this._phase.set('completed');
      this._progress.set(100);
      this._message.set(data.message);
      this._isComplete.set(true);
      this._redirectUrl.set(data.redirect_url);

      this.stopElapsedTimer();

      // Live update
      this.addLiveUpdate('✅ Processing completed!', 'success');

      // Auto-redirect después de 2 segundos
      console.log('%c[SSE] 🔀 Redirigiendo en 2 segundos...', 'color: #2196F3');
      this.redirectTimeout = setTimeout(() => {
        if (data.redirect_url) {
          console.log(`%c[SSE] 🔀 Navegando a: ${data.redirect_url}`, 'color: #2196F3; font-weight: bold');
          this.router.navigateByUrl(data.redirect_url);
        }
      }, 2000);
    });

    // Error
    this.eventSource.addEventListener('error', (event: MessageEvent) => {
      const data: ErrorEvent = JSON.parse(event.data);
      console.error('%c[SSE] ❌ ERROR EN EL PROCESO:', 'color: #f44336; font-weight: bold; font-size: 14px; background: #FFCDD2; padding: 5px 10px;', {
        mensaje: data.message
      });

      this._phase.set('error');
      this._isError.set(true);
      this._errorMessage.set(data.message);
      this._message.set(data.message);

      // Live update
      this.addLiveUpdate(`❌ Error: ${data.message}`, 'error');

      this.stopElapsedTimer();
      this.disconnect();

      // Start countdown and redirect to upload after 5 seconds
      this._redirectCountdown.set(5);
      console.log('%c[SSE] ⏱️ Redirigiendo a /upload en 5 segundos...', 'color: #FFC107');

      // Limpiar countdown anterior si existe
      if (this.countdownInterval) {
        clearInterval(this.countdownInterval);
      }

      this.countdownInterval = setInterval(() => {
        const current = this._redirectCountdown();
        if (current !== null && current > 1) {
          this._redirectCountdown.set(current - 1);
          console.log(`%c[SSE] ⏱️ Redireccionando en ${current - 1}...`, 'color: #FFC107');
        } else {
          if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
          }
          this._redirectCountdown.set(null);
          console.log('%c[SSE] 🔀 Navegando a /upload', 'color: #2196F3; font-weight: bold');
          this.router.navigate(['/upload']);
        }
      }, 1000);
    });

    // Heartbeat
    this.eventSource.addEventListener('heartbeat', () => {
      console.log('%c[SSE] 💓 Heartbeat', 'color: #E91E63');
    });

    // Mensaje genérico (catch-all)
    this.eventSource.addEventListener('message', (event: MessageEvent) => {
      console.log('%c[SSE] 📨 Mensaje genérico:', 'color: #607D8B', event.data);
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

  /**
   * Fetches all violations from the verification module when waiting_for_review phase is detected.
   * This preloads the violations data so it's available when navigating to the review page.
   */
  private fetchViolations(videoId: string): void {
    if (this.violationsFetched) {
      console.log('%c[SSE] 📋 Violations already fetched, skipping...', 'color: #9E9E9E');
      return;
    }

    this.violationsFetched = true;
    this._violationsLoading.set(true);
    this._violationsError.set(null);

    console.log(`%c[SSE] 📋 Fetching violations for video: ${videoId}`, 'color: #E91E63; font-weight: bold');

    this.videoService.getViolations(videoId).subscribe({
      next: (response) => {
        console.log('%c[SSE] ✅ Violations received:', 'color: #4CAF50; font-weight: bold', {
          total: response.total,
          itemsCount: response.items.length
        });

        // Log full JSON response for debugging
        console.log('%c[SSE] 📦 Full violations JSON:', 'color: #2196F3; font-weight: bold');
        console.log(JSON.stringify(response, null, 2));

        this._violations.set(response.items);
        this._violationsLoading.set(false);

        // Live update
        this.addLiveUpdate(`Loaded ${response.items.length} violations`, 'success');
      },
      error: (err) => {
        console.error('%c[SSE] ❌ Error fetching violations:', 'color: #f44336; font-weight: bold', err);
        this._violationsError.set(err.userMessage || 'Error loading violations');
        this._violationsLoading.set(false);
        this.violationsFetched = false; // Allow retry

        // Live update
        this.addLiveUpdate('Failed to load violations', 'error');
      }
    });
  }
}
