import { DecimalPipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
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

  ngOnInit(): void {
    // Leer ID de la ruta
    const videoId = this.route.snapshot.paramMap.get('id');
    const from = this.route.snapshot.queryParamMap.get('from');

    if (videoId) {
      this.sse.connect(videoId);
    }
    if (from) {
      this.comingFrom.set(from);
    }
  }

  ngOnDestroy(): void {
    this.sse.disconnect();
  }

  // Called via SSE complete event logic or manual button
  // Note: SSE service has auto-redirect logic, but we might override or use it.
  // The service tries: this.router.navigateByUrl(data.redirect_url);
  // Backend CompleteEvent sends redirect_url. We should ensure Backend sends `/review/{video_id}`.
  // Currently backend might not send formatted URL.
  // Let's rely on SSE service completion logic mostly, but if manual:

  private onComplete() {
    const videoId = this.route.snapshot.paramMap.get('id');
    if (this.comingFrom() === 'upload') {
      this.router.navigate(['/review', videoId]);
    } else {
      this.router.navigate(['/download', videoId]);
    }
  }

  protected retry(): void {
    const videoId = this.route.snapshot.paramMap.get('id');
    if (videoId) {
      this.sse.reset();
      this.sse.connect(videoId);
    }
  }
}
