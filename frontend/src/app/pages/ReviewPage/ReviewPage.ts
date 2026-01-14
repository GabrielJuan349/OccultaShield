import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { ViolationCard } from '#components/ViolationCard/ViolationCard';
import type { ModificationType, Violation } from '#interface/violation.interface';
import { VideoService } from '#services/video.service';
import type { UserDecision } from '#interface/violation.interface';
import { environment } from '#environments/environment';

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
        // Map Backend ViolationCard to UI Violation model
        const mapped: Violation[] = response.items.map(v => {
          // Need to handle image URL.
          // If backend sends relative path or full URL. Usually relative in 'capture_image_url' like '/api/v1/...'

          let imgUrl = v.capture_image_url;
          if (imgUrl && !imgUrl.startsWith('http')) {
            // Prepend API base if needed, or assume it's a static file served by backend
            // If it is an endpoint like /api/v1/video/{id}/capture/..., we might need origin.
            // Assuming backend sends a usable URL or proxy path.
            imgUrl = `${environment.apiUrl}${imgUrl}`;
          }

          // Map backend 'recommended_action' to default selection
          let defaultOption: ModificationType = 'no_modify';
          if (v.recommended_action === 'blur') defaultOption = 'blur';
          if (v.recommended_action === 'pixelate') defaultOption = 'pixelate';
          if (v.recommended_action === 'mask') defaultOption = 'mask';

          // If specific logic needed: defaults to blur if violation
          if (v.is_violation && defaultOption === 'no_modify') defaultOption = 'blur';

          return {
            id: v.verification_id, // Important: Use verification_id for decisions
            articleTitle: `Detected: ${v.detection_type}`,
            articleSubtitle: `${v.severity} Severity`,
            description: v.description,
            fineText: v.fine_text || v.violated_articles.join(', ') || "Potential GDPR Violation",
            imageUrl: imgUrl || 'assets/images/placeholder.png',
            selectedOption: defaultOption,
            framesAnalyzed: v.frames_analyzed ?? 1,  // Temporal Consensus
            confidence: v.confidence
          };
        });

        // Always show ReviewPage, even if no violations found
        // User can still continue to download from here
        console.log(`Loaded ${mapped.length} violations for review`);
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

    // Convert UI state to UserDecision[]
    const decisions: UserDecision[] = this.violations().map(v => {
      return {
        verification_id: v.id,
        action: v.selectedOption,
        confirmed_violation: v.selectedOption !== 'no_modify'
      };
    });

    console.log('Applying modifications:', decisions);

    this.videoService.submitDecisions(id, decisions).subscribe({
      next: () => {
        // Navigate to processing (applying edits) -> Download
        // Set 'from' query param to 'review' so ProcessingPage knows next step is Download
        this.router.navigate(['/processing', id], { queryParams: { from: 'review' } });
      },
      error: (err) => console.error("Error submitting decisions", err)
    });
  }
}
