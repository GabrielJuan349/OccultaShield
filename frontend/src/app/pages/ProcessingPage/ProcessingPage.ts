import { DecimalPipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, effect, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ProcessingSSEService } from '#services/processing-sse.service';

@Component({
  imports: [DecimalPipe, NgOptimizedImage, RouterLink],
  templateUrl: './ProcessingPage.html',
  styleUrl: './ProcessingPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProcessingPage implements OnInit, OnDestroy {

  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  protected readonly sse = inject(ProcessingSSEService);

  // Determina si viene de upload (va a review) o de review (va a download)
  protected readonly comingFrom = signal<string>('upload');

  constructor() {
    // Effect to monitor phase changes
    effect(() => {
      const currentPhase = this.sse.phase();
      const videoId = this.route.snapshot.paramMap.get('id');

      if (currentPhase === 'waiting_for_review' && videoId) {
        console.log('%c[PROCESSING] 🎯 Fase waiting_for_review detectada', 'color: #FF9800; font-weight: bold');
        console.log(`%c[PROCESSING] 📡 Solicitando datos de violaciones para video: ${videoId}`, 'color: #2196F3');

        // Only navigate if we are coming from upload
        if (this.comingFrom() === 'upload') {
          // Navigate to review page which will fetch violations
          console.log('%c[PROCESSING] 🔀 Navegando a página de revisión...', 'color: #4CAF50');
          this.router.navigate(['/review', videoId]);
        }
      }

      // If completed, navigate to download
      // Can come from upload (no violations) or review (after edition)
      if (currentPhase === 'completed' && videoId) {
        console.log('%c[PROCESSING] ✅ Proceso completado, navegando a descarga', 'color: #4CAF50; font-weight: bold');
        this.router.navigate(['/download', videoId]);
      }
    });
  }

  ngOnInit(): void {
    // Leer ID de la ruta
    const videoId = this.route.snapshot.paramMap.get('id');
    const from = this.route.snapshot.queryParamMap.get('from');

    console.log('ProcessingPage ngOnInit - videoId:', videoId, 'from:', from);

    if (videoId) {
      console.log('Connecting to SSE for video:', videoId);
      this.sse.connect(videoId);
    } else {
      console.error('No video ID found in route');
    }

    if (from) {
      this.comingFrom.set(from);
    }
  }

  ngOnDestroy(): void {
    this.sse.disconnect();
  }

  protected retry(): void {
    const videoId = this.route.snapshot.paramMap.get('id');
    if (videoId) {
      this.sse.reset();
      this.sse.connect(videoId);
    }
  }
}
