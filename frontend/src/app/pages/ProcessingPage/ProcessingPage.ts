/**
 * Processing Page Component for OccultaShield.
 *
 * Displays real-time video processing progress via Server-Sent Events (SSE).
 * Shows detection, verification, and anonymization phases with live updates.
 *
 * Flow:
 * - From Upload: Processing → Detection → Verification → Review
 * - From Review: Processing → Anonymization → Download
 *
 * Features:
 * - Real-time progress updates via SSE
 * - Phase-specific UI feedback
 * - Automatic navigation on phase completion
 * - Retry functionality on errors
 *
 * @example
 * Route: /processing/:id
 * Query: ?from=upload|review (determines next navigation target)
 */

import { DecimalPipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, effect, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ProcessingSSEService } from '#services/processing-sse.service';
import { environment } from '#environments/environment';

/**
 * Real-time video processing status page.
 *
 * Connects to SSE endpoint for live progress updates and handles
 * automatic navigation based on processing phase transitions.
 */
@Component({
  imports: [DecimalPipe, NgOptimizedImage, RouterLink],
  templateUrl: './ProcessingPage.html',
  styleUrl: './ProcessingPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProcessingPage implements OnInit, OnDestroy {

  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly http = inject(HttpClient);
  protected readonly sse = inject(ProcessingSSEService);

  // Determina si viene de upload (va a review) o de review (va a download)
  protected readonly comingFrom = signal<string>('upload');
  private readonly videoId = signal<string | null>(null);

  // Track if we've already navigated to prevent duplicate navigations
  private hasNavigatedToReview = false;
  private hasNavigatedToDownload = false;

  constructor() {
    // Effect: Monitorear cambios de fase para navegación
    effect(() => {
      const currentPhase = this.sse.phase();
      const isConnected = this.sse.isConnected();
      const currentVideoId = this.videoId();

      console.log(`%c[PROCESSING] 📡 Phase check: ${currentPhase}, connected: ${isConnected}`, 'color: #9C27B0');

      // Solo proceder si estamos conectados
      if (!isConnected || !currentVideoId) return;

      if (currentPhase === 'waiting_for_review' && !this.hasNavigatedToReview) {
        console.log('%c[PROCESSING] 🎯 Fase waiting_for_review detectada', 'color: #FF9800; font-weight: bold');

        // Solo navegar si venimos de upload
        if (this.comingFrom() === 'upload') {
          console.log('%c[PROCESSING] 🔀 Navegando a página de revisión...', 'color: #4CAF50');
          this.hasNavigatedToReview = true;
          setTimeout(() => {
            this.router.navigate(['/review', currentVideoId]);
          }, 100);
        }
      }

      // Si está completado, navegar a download
      if (currentPhase === 'completed' && !this.hasNavigatedToDownload) {
        console.log('%c[PROCESSING] ✅ Proceso completado, navegando a descarga', 'color: #4CAF50; font-weight: bold');
        this.hasNavigatedToDownload = true;
        setTimeout(() => {
          this.router.navigate(['/download', currentVideoId]);
        }, 100);
      }
    });
  }

  ngOnInit(): void {
    const videoId = this.route.snapshot.paramMap.get('id');
    const from = this.route.snapshot.queryParamMap.get('from');

    console.log('%c[PROCESSING] 🎬 Iniciando ProcessingPage', 'color: #673AB7; font-weight: bold');
    console.log(`   videoId: ${videoId}, from: ${from}`);

    // Reset flags
    this.hasNavigatedToReview = false;
    this.hasNavigatedToDownload = false;

    if (!videoId) {
      console.error('%c[PROCESSING] ❌ No video ID found in route', 'color: #f44336');
      return;
    }

    // Setear el videoId como signal para que el effect lo detecte
    this.videoId.set(videoId);

    if (from) {
      this.comingFrom.set(from);
    }

    // Conectar al SSE - el backend detectará la conexión y auto-iniciará el procesamiento
    console.log('%c[PROCESSING] 🔌 Conectando al SSE...', 'color: #2196F3');
    console.log('%c[PROCESSING] 💡 El backend auto-iniciará el procesamiento al detectar la conexión', 'color: #2196F3');
    this.sse.connect(videoId);
  }

  ngOnDestroy(): void {
    this.sse.disconnect();
  }

  protected retry(): void {
    const videoId = this.route.snapshot.paramMap.get('id');
    if (videoId) {
      this.hasNavigatedToReview = false;
      this.hasNavigatedToDownload = false;
      this.sse.reset();
      this.sse.connect(videoId);
    }
  }
}
