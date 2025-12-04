import { DecimalPipe, NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-processing-page',
  imports: [DecimalPipe, NgOptimizedImage],
  templateUrl: './ProcessingPage.html',
  styleUrl: './ProcessingPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProcessingPage implements OnInit, OnDestroy {

  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  // --- ESTADO (Signals) ---
  protected readonly progress = signal(0);

  // Determina si viene de upload (va a review) o de review (va a download)
  private readonly comingFrom = signal<string>('upload');

  // Computamos el tiempo restante basado en el progreso (ficticio)
  protected readonly timeRemaining = computed(() => {
    const p = this.progress();
    if (p >= 100) return 'Complete';
    // Fórmula simple: (100 - progreso) * factor aprox
    const seconds = Math.ceil((100 - p) * 0.5);
    return `${seconds} seconds`;
  });

  private intervalId: ReturnType<typeof setInterval> | null = null;

  ngOnInit() {
    // Leer de dónde viene para saber a dónde ir después
    const from = this.route.snapshot.queryParamMap.get('from');
    if (from) {
      this.comingFrom.set(from);
    }
    this.startSimulation();
  }

  ngOnDestroy() {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  private startSimulation() {
    // Simulamos una carga progresiva hasta el 100%
    this.intervalId = setInterval(() => {
      this.progress.update(current => {
        if (current >= 100) {
          if (this.intervalId !== null) {
            clearInterval(this.intervalId);
            this.intervalId = null;
          }
          this.onComplete();
          return 100;
        }
        // Incremento aleatorio entre 1 y 3
        return Math.min(current + Math.random() * 2, 100);
      });
    }, 200);
  }

  private onComplete() {
    setTimeout(() => {
      if (this.comingFrom() === 'upload') {
        // Viene de Upload -> va a Review
        this.router.navigate(['/review']);
      } else {
        // Viene de Review -> va a Download
        this.router.navigate(['/download']);
      }
    }, 800);
  }
}
