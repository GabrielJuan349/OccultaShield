import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { ViolationCard } from '#components/ViolationCard/ViolationCard';
import type { ModificationType, Violation, UserDecision } from '#interface/violation.interface';
import { VideoService } from '#services/video.service';
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

          // Build image URL - SecureMediaService will handle auth via HttpClient
          let imgUrl = v.capture_image_url;
          if (imgUrl && !imgUrl.startsWith('http')) {
            // Prepend API base if needed
            imgUrl = `${environment.apiUrl}${imgUrl}`;
          }
          // No token in URL - ViolationCard uses SecureMediaService with Authorization header

          // Map backend 'recommended_action' to ModificationType
          let recommendedAction: ModificationType = 'no_modify';
          if (v.recommended_action === 'blur') recommendedAction = 'blur';
          if (v.recommended_action === 'pixelate') recommendedAction = 'pixelate';
          if (v.recommended_action === 'mask') recommendedAction = 'mask';

          // Determine default selection based on violation status
          let defaultOption: ModificationType;
          if (!v.is_violation || v.severity === 'none') {
            // No risk identified - default to no_modify
            defaultOption = 'no_modify';
          } else if (recommendedAction !== 'no_modify') {
            // Use AI recommendation if available
            defaultOption = recommendedAction;
          } else {
            // Fallback to blur for violations without specific recommendation
            defaultOption = 'blur';
          }

          // Build fine text - hide if no risk
          const showFine = v.is_violation && v.severity !== 'none';
          const fineText = showFine
            ? (v.fine_text || v.violated_articles.join(', ') || "Potential GDPR Violation")
            : '';

          return {
            id: v.verification_id, // Important: Use verification_id for decisions
            articleTitle: `Detected: ${v.detection_type}`,
            articleSubtitle: v.severity.toUpperCase() + ' SEVERITY',
            description: v.description,
            fineText,
            imageUrl: imgUrl || 'assets/images/placeholder.png',
            selectedOption: defaultOption,
            framesAnalyzed: v.frames_analyzed ?? 1,
            confidence: v.confidence,
            recommendedAction,
            isViolation: v.is_violation,
            severity: v.severity,
            // Structured data for improved UI
            violatedArticles: v.violated_articles || [],
            firstFrame: v.first_frame,
            lastFrame: v.last_frame,
            detectionType: v.detection_type,
            durationSeconds: v.duration_seconds
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
