import { DecimalPipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ProcessingSSEService } from '../../services/processing-sse.service';

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

  ngOnInit():void {
    // Leer de dónde viene para saber a dónde ir después
    const from = this.route.snapshot.queryParamMap.get('from');
    const videoId = this.route.snapshot.queryParamMap.get('video_id');
    if (videoId) {
      this.sse.connect(videoId);
    }
    if (from) {
      this.comingFrom.set(from);
    }
  }

  ngOnDestroy(): void {
    this.onComplete();
    this.sse.disconnect();
  }

  private onComplete() {
      if (this.comingFrom() === 'upload') {
        // Viene de Upload -> va a Review
        this.router.navigate(['/review']);
      } else {
        // Viene de Review -> va a Download
        this.router.navigate(['/download']);
      }
  }

  protected retry(): void {
    const videoId = this.route.snapshot.queryParamMap.get('video_id');
    if (videoId) {
      this.sse.reset();
      this.sse.connect(videoId);
    }
  }
}
