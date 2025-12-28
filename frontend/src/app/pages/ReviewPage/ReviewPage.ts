import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { ViolationCard } from '#components/ViolationCard/ViolationCard';
import { ModificationType, Violation } from '#interface/violation-models';
import { VideoService } from '#services/video.service';

@Component({
  imports: [ViolationCard],
  templateUrl: './ReviewPage.html',
  styleUrl: './ReviewPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewPage implements OnInit {

  private readonly router = inject(Router);

  private readonly route = inject(ActivatedRoute);
  private readonly videoService = inject(VideoService);

  // Signal que contiene el array de vulneraciones
  protected readonly violations = signal<Violation[]>([]);
  protected videoId = signal<string | null>(null);

  ngOnInit() {
    this.videoId.set(this.route.snapshot.paramMap.get('id'));
    if (this.videoId()) {
      this.loadViolations(this.videoId()!);
    }
  }

  loadViolations(id: string) {
    this.videoService.getViolations(id).subscribe({
      next: (response) => {
        // Map ValidatedResponse items (ViolationCard) to UI Violation model
        // Interface ViolationCard: { id, timestamp, threat_level, description, detection_type ... }
        // UI Violation: { id, articleTitle, articleSubtitle, description, fineText, imageUrl, selectedOption }
        // We need to map backend data to UI.

        const mapped: Violation[] = response.items.map(v => ({
          id: v.id,
          articleTitle: `Detected: ${v.detection_type}`,
          articleSubtitle: v.threat_level + " Severity",
          description: v.description,
          fineText: "Potential GDPR Violation",
          imageUrl: 'supervision_humana.png', // Placeholder or use capture URL if available
          selectedOption: 'no-modify' // Default
        }));
        this.violations.set(mapped);
      },
      error: (err) => console.error("Error loading violations", err)
    });
  }

  // Actualiza el modelo cuando el hijo emite un cambio
  updateViolation(id: string, selection: ModificationType): void {
    this.violations.update(list =>
      list.map(v => v.id === id ? { ...v, selectedOption: selection } : v)
    );
  }

  applyAndContinue(): void {
    const id = this.videoId();
    if (!id) return;

    // Map decisions
    // Backend expects { decisions: { "violation_id": "anonymize" | "keep" } }
    const decisions: Record<string, 'anonymize' | 'keep'> = {};

    this.violations().forEach(v => {
      // Map UI selection to backend expected values
      // UI: 'blur' | 'pixelate' | 'black-box' | 'no-modify'
      // Simplication for now: if 'no-modify', keep. Else anonymize.
      if (v.selectedOption === 'no-modify') {
        decisions[v.id] = 'keep';
      } else {
        decisions[v.id] = 'anonymize';
      }
    });

    console.log('Applying modifications:', decisions);

    this.videoService.submitDecisions(id, decisions).subscribe({
      next: () => {
        // Navigate to processing (applying edits) -> Download
        // We reuse processing page for 'edition' phase or creating download
        // Or direct to download if synchronous? But Backend is async.
        // Usually go back to processing to await completion.
        this.router.navigate(['/processing', id], { queryParams: { from: 'review' } });
      },
      error: (err) => console.error("Error submitting decisions", err)
    });
  }
}
