import { Component, inject } from '@angular/core';
import { ToastService } from '#services/toast.service';

@Component({
  selector: 'toast-container',
  template: `
    <div class="toast-container">
      @for (toast of toastService.activeToasts(); track toast.id) {
        <div class="toast" [class]="toast.type" (click)="toastService.remove(toast.id)">
          <span class="icon">
            @switch (toast.type) {
              @case ('success') { ✓ }
              @case ('error') { ✕ }
              @case ('warning') { ⚠ }
              @case ('info') { ℹ }
            }
          </span>
          <span class="message">{{ toast.message }}</span>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-width: 400px;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      border-radius: 8px;
      background: var(--surface-elevated, #1a1a2e);
      color: var(--text-primary, #fff);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
      cursor: pointer;
      animation: slideIn 0.3s ease-out;
      border-left: 4px solid;
    }

    .toast.success {
      border-left-color: #4CAF50;
      background: linear-gradient(135deg, rgba(76, 175, 80, 0.15), var(--surface-elevated, #1a1a2e));
    }

    .toast.error {
      border-left-color: #f44336;
      background: linear-gradient(135deg, rgba(244, 67, 54, 0.15), var(--surface-elevated, #1a1a2e));
    }

    .toast.warning {
      border-left-color: #ff9800;
      background: linear-gradient(135deg, rgba(255, 152, 0, 0.15), var(--surface-elevated, #1a1a2e));
    }

    .toast.info {
      border-left-color: #2196F3;
      background: linear-gradient(135deg, rgba(33, 150, 243, 0.15), var(--surface-elevated, #1a1a2e));
    }

    .icon {
      font-size: 1.2rem;
      font-weight: bold;
    }

    .toast.success .icon { color: #4CAF50; }
    .toast.error .icon { color: #f44336; }
    .toast.warning .icon { color: #ff9800; }
    .toast.info .icon { color: #2196F3; }

    .message {
      flex: 1;
      font-size: 0.95rem;
    }

    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(100%);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }

    .toast:hover {
      transform: scale(1.02);
      transition: transform 0.2s ease;
    }
  `]
})
export class ToastContainerComponent {
  toastService = inject(ToastService);
}
