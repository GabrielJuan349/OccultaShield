import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import type { ModificationType, Violation } from '#interface/violation.interface';

@Component({
  selector: 'app-violation-card',
  imports: [NgOptimizedImage],
  host: {
    '(document:keydown.escape)': 'onEscapeKey()',
    '(document:keydown)': 'onKeyDown($event)',
    '(document:keyup)': 'onKeyUp($event)',
    '(window:blur)': 'onWindowBlur()',
    '(window:focus)': 'onWindowFocus()'
  },
  template: `
    <div class="card-grid group">

      <div class="col-options">
        <h3 class="section-title">Modification Options</h3>
        <div class="options-list">

          @for (opt of options; track opt.value) {
            <button
              class="option-btn"
              [class.active]="currentSelection() === opt.value"
              (click)="selectOption(opt.value)"
            >
              <span class="material-symbols-outlined icon">
                {{ currentSelection() === opt.value ? 'radio_button_checked' : opt.icon }}
              </span>
              {{ opt.label }}
            </button>
          }

        </div>
      </div>

      <div class="col-info">
        <h2 class="article-title">{{ data().articleTitle }}</h2>
        <p class="article-subtitle">{{ data().articleSubtitle }}</p>
        <p class="description">{{ data().description }}</p>

        <div class="fine-box">
          <h4 class="fine-label">Potential Fine</h4>
          <p class="fine-value">{{ data().fineText }}</p>
        </div>
      </div>

      <div class="col-image" (click)="openPreview()" (keydown.enter)="openPreview()" tabindex="0" role="button" aria-label="Click to preview image">
        <img
          [ngSrc]="data().imageUrl"
          fill
          alt="Violation Preview"
          class="preview-img"
        >
        <div class="image-overlay">
          <span class="material-symbols-outlined">zoom_in</span>
          <span>Click to preview</span>
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
              [src]="data().imageUrl"
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

  // Configuración de botones para el HTML
  protected readonly options: readonly { label: string; value: ModificationType; icon: string }[] = [
    { label: 'No Modify', value: 'no_modify', icon: 'radio_button_unchecked' },
    { label: 'Pixelate', value: 'pixelate', icon: 'grid_on' },
    { label: 'Mask', value: 'mask', icon: 'visibility_off' },
    { label: 'Blur', value: 'blur', icon: 'blur_on' }
  ] as const;

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
