/**
 * Violation Card Component for OccultaShield Review Page.
 *
 * Displays a detected GDPR violation with image preview, evidence details,
 * and action selection buttons. Implements screenshot protection for the
 * image preview modal.
 *
 * Features:
 * - Secure image loading via blob URLs (no tokens in URLs)
 * - AI confidence and recommendation display
 * - GDPR article violation badges
 * - Screenshot/capture protection in preview modal
 * - Keyboard navigation support
 *
 * @example
 * ```html
 * <app-violation-card
 *   [data]="violation"
 *   (selectionChange)="updateViolation($event)"
 * />
 * ```
 */

import { ChangeDetectionStrategy, Component, input, output, signal, effect, inject, DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import type { ModificationType, Violation } from '#interface/violation.interface';
import { SecureMediaService } from '#services/secure-media.service';

/**
 * Card component for displaying and selecting actions on detected violations.
 *
 * Uses signal-based inputs and outputs for reactive state management.
 * Implements OnPush change detection for optimal performance.
 */
@Component({
  selector: 'app-violation-card',
  imports: [],
  host: {
    '(document:keydown.escape)': 'onEscapeKey()',
    '(document:keydown)': 'onKeyDown($event)',
    '(document:keyup)': 'onKeyUp($event)',
    '(window:blur)': 'onWindowBlur()',
    '(window:focus)': 'onWindowFocus()'
  },
  template: `
    <div class="card-container" [class.no-risk]="!data().isViolation">
      <!-- Header with detection type and severity badge -->
      <div class="card-header">
        <div class="detection-info">
          <span class="detection-type">{{ data().articleTitle }}</span>
          <span class="severity-badge" [attr.data-severity]="data().severity">
            {{ data().articleSubtitle }}
          </span>
        </div>
        @if (data().confidence) {
          <div class="confidence-indicator">
            <span class="material-symbols-outlined">psychology</span>
            <span>{{ (data().confidence! * 100).toFixed(0) }}% confidence</span>
          </div>
        }
      </div>

      <div class="card-body">
        <!-- Image Preview Column -->
        <div class="image-section" (click)="openPreview()" (keydown.enter)="openPreview()" tabindex="0" role="button" aria-label="Click to preview image">
          <img
            [src]="secureImageUrl()"
            alt="Detection Preview"
            class="preview-img"
          >
          <div class="image-overlay">
            <span class="material-symbols-outlined">zoom_in</span>
            <span>Preview</span>
          </div>
          @if (data().framesAnalyzed && data().framesAnalyzed! > 1) {
            <div class="frames-badge">
              <span class="material-symbols-outlined">movie</span>
              {{ data().framesAnalyzed }} frames
            </div>
          }
        </div>

        <!-- Info & Options Column -->
        <div class="info-section">
          <!-- Evidence Section: Frame Range & Confidence -->
          <div class="evidence-section">
            <h4 class="section-title">
              <span class="material-symbols-outlined">analytics</span>
              Evidence
            </h4>
            <div class="evidence-grid">
              <!-- Frame Range -->
              @if (data().firstFrame && data().lastFrame) {
                <div class="evidence-item">
                  <span class="material-symbols-outlined">movie</span>
                  <div class="evidence-content">
                    <span class="evidence-label">Frame Range</span>
                    <span class="evidence-value">{{ data().firstFrame }} - {{ data().lastFrame }}</span>
                  </div>
                </div>
              }
              <!-- Frames Analyzed -->
              @if (data().framesAnalyzed) {
                <div class="evidence-item">
                  <span class="material-symbols-outlined">photo_library</span>
                  <div class="evidence-content">
                    <span class="evidence-label">Frames Analyzed</span>
                    <span class="evidence-value">{{ data().framesAnalyzed }}</span>
                  </div>
                </div>
              }
              <!-- Confidence Bar -->
              @if (data().confidence) {
                <div class="evidence-item confidence-item">
                  <span class="material-symbols-outlined">psychology</span>
                  <div class="evidence-content">
                    <span class="evidence-label">AI Confidence</span>
                    <div class="confidence-bar-container">
                      <div class="confidence-bar" [style.width.%]="(data().confidence! * 100)" [attr.data-level]="getConfidenceLevel(data().confidence!)"></div>
                      <span class="confidence-text">{{ (data().confidence! * 100).toFixed(0) }}%</span>
                    </div>
                  </div>
                </div>
              }
            </div>
          </div>

          <!-- Compliance Section: Violated Articles -->
          @if (data().violatedArticles && data().violatedArticles!.length > 0) {
            <div class="compliance-section">
              <h4 class="section-title">
                <span class="material-symbols-outlined">policy</span>
                Compliance Issues
              </h4>
              <div class="articles-chips">
                @for (article of data().violatedArticles; track article) {
                  <span class="article-chip">{{ article }}</span>
                }
              </div>
            </div>
          }

          <!-- AI Recommendation Badge -->
          @if (data().recommendedAction && data().recommendedAction !== 'no_modify') {
            <div class="ai-recommendation">
              <span class="material-symbols-outlined">smart_toy</span>
              <span>AI recommends: <strong>{{ getActionLabel(data().recommendedAction!) }}</strong></span>
            </div>
          }

          <!-- Fine Box - only show if there's a fine -->
          @if (data().fineText) {
            <div class="fine-box">
              <span class="material-symbols-outlined">gavel</span>
              <div class="fine-content">
                <span class="fine-label">Potential Fine</span>
                <span class="fine-value">{{ data().fineText }}</span>
              </div>
            </div>
          }

          <!-- Modification Options -->
          <div class="options-section">
            <h4 class="options-title">Select Action</h4>
            <div class="options-grid">
              @for (opt of options; track opt.value) {
                <button
                  class="option-btn"
                  [class.active]="currentSelection() === opt.value"
                  [class.recommended]="data().recommendedAction === opt.value && opt.value !== 'no_modify'"
                  (click)="selectOption(opt.value)"
                >
                  <span class="material-symbols-outlined">{{ opt.icon }}</span>
                  <span class="option-label">{{ opt.label }}</span>
                  @if (data().recommendedAction === opt.value && opt.value !== 'no_modify') {
                    <span class="rec-badge">AI</span>
                  }
                </button>
              }
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal de previsualización con protección contra capturas -->
    @if (isPreviewOpen()) {
      <div
        class="modal-backdrop protected-content"
        (click)="closePreview()"
        (contextmenu)="preventAction($event)"
        (dragstart)="preventAction($event)"
      >
        <div class="modal-content" (click)="$event.stopPropagation()">
          <button class="modal-close" (click)="closePreview()" aria-label="Close preview (ESC)">
            <span class="material-symbols-outlined">close</span>
          </button>
          <div class="protected-image-container" [class.hidden-for-capture]="isHiddenForCapture()">
            <img
              [src]="secureImageUrl()"
              alt="Full size preview"
              class="modal-image"
              (contextmenu)="preventAction($event)"
              (dragstart)="preventAction($event)"
              draggable="false"
            >
            <div class="watermark-overlay">
              <span>PREVIEW ONLY</span>
              <span>PREVIEW ONLY</span>
              <span>PREVIEW ONLY</span>
            </div>
          </div>
          @if (isHiddenForCapture()) {
            <div class="capture-blocked-message">
              <span class="material-symbols-outlined">screenshot_monitor</span>
              <p>Screenshot blocked</p>
            </div>
          }
          <p class="modal-hint">🔒 Protected preview - Press ESC or click outside to close</p>
        </div>
      </div>
    }
  `,
  styleUrl: './ViolationCard.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ViolationCard {
  // Services
  private readonly secureMedia = inject(SecureMediaService);
  private readonly destroyRef = inject(DestroyRef);

  // Inputs requeridos (Signal Inputs de Angular moderno)
  readonly data = input.required<Violation>();

  // Output para notificar al padre cuando cambia la selección
  readonly selectionChange = output<ModificationType>();

  // Estado local sincronizado inicialmente con la data
  protected readonly currentSelection = signal<ModificationType>('no_modify');

  // Estado para el modal de previsualización
  protected readonly isPreviewOpen = signal(false);

  // Estado para ocultar imagen durante capturas
  protected readonly isHiddenForCapture = signal(false);

  // URL segura de la imagen (blob URL)
  protected readonly secureImageUrl = signal<string>('');

  // Configuración de botones para el HTML
  protected readonly options: readonly { label: string; value: ModificationType; icon: string }[] = [
    { label: 'No Modify', value: 'no_modify', icon: 'block' },
    { label: 'Pixelate', value: 'pixelate', icon: 'grid_on' },
    { label: 'Mask', value: 'mask', icon: 'visibility_off' },
    { label: 'Blur', value: 'blur', icon: 'blur_on' }
  ] as const;

  // Map for action labels
  private readonly actionLabels: Record<ModificationType, string> = {
    'no_modify': 'No Modify',
    'pixelate': 'Pixelate',
    'mask': 'Mask',
    'blur': 'Blur'
  };

  constructor() {
    // Sync currentSelection with input data when it changes
    effect(() => {
      const selectedOption = this.data().selectedOption;
      if (selectedOption) {
        this.currentSelection.set(selectedOption);
      }
    });

    // Load image securely when data changes
    effect(() => {
      const url = this.data().imageUrl;
      if (url && !url.startsWith('blob:') && !url.startsWith('assets/')) {
        // Load via SecureMediaService (uses HttpClient with Authorization header)
        this.secureMedia.loadImage(url).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe(blobUrl => {
          if (blobUrl) {
            this.secureImageUrl.set(blobUrl);
          }
        });
      } else if (url) {
        // Fallback for placeholders or already-blob URLs
        this.secureImageUrl.set(url);
      }
    });
  }

  getActionLabel(action: ModificationType): string {
    return this.actionLabels[action] || action;
  }

  getConfidenceLevel(confidence: number): string {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    return 'low';
  }

  selectOption(value: ModificationType): void {
    this.currentSelection.set(value);
    this.selectionChange.emit(value);
  }

  openPreview(): void {
    this.isPreviewOpen.set(true);
  }

  closePreview(): void {
    this.isPreviewOpen.set(false);
  }

  onEscapeKey(): void {
    if (this.isPreviewOpen()) {
      this.closePreview();
    }
  }

  // Bloquear atajos de teclado para capturas cuando el modal está abierto
  onKeyDown(event: KeyboardEvent): void {
    if (!this.isPreviewOpen()) return;

    // Detectar PrintScreen - ocultar imagen inmediatamente
    if (event.key === 'PrintScreen') {
      this.hideImageForCapture();
      return;
    }

    // Bloquear Ctrl+P (imprimir), Ctrl+S (guardar), Ctrl+Shift+S
    if (event.ctrlKey && ['p', 's', 'P', 'S'].includes(event.key)) {
      event.preventDefault();
      this.hideImageForCapture();
      return;
    }

    // Bloquear Ctrl+Shift+I (DevTools)
    if (event.ctrlKey && event.shiftKey && ['i', 'I'].includes(event.key)) {
      event.preventDefault();
      return;
    }

    // Bloquear Windows+Shift+S (Windows screenshot)
    if (event.metaKey && event.shiftKey && ['s', 'S'].includes(event.key)) {
      event.preventDefault();
      this.hideImageForCapture();
      return;
    }
  }

  // Restaurar imagen cuando se suelta la tecla
  onKeyUp(event: KeyboardEvent): void {
    if (event.key === 'PrintScreen') {
      // Mantener oculto un poco más para asegurar que la captura ya se hizo
      setTimeout(() => this.showImage(), 500);
    }
  }

  // Ocultar cuando la ventana pierde foco (herramientas de captura externas)
  onWindowBlur(): void {
    if (this.isPreviewOpen()) {
      this.hideImageForCapture();
    }
  }

  // Mostrar cuando la ventana recupera el foco
  onWindowFocus(): void {
    // Pequeño delay para asegurar que cualquier captura ya terminó
    setTimeout(() => this.showImage(), 300);
  }

  private hideImageForCapture(): void {
    this.isHiddenForCapture.set(true);
  }

  private showImage(): void {
    this.isHiddenForCapture.set(false);
  }

  // Prevenir clic derecho y arrastre de imagen
  preventAction(event: Event): void {
    event.preventDefault();
  }
}
