/**
 * Toast Notification Service.
 *
 * Provides a signal-based toast notification system for displaying
 * temporary feedback messages to users. Supports success, error,
 * warning, and info notification types.
 *
 * @example
 * ```typescript
 * toastService.success('File uploaded successfully');
 * toastService.error('Upload failed', 8000);
 * ```
 */
import { Injectable, signal, computed } from '@angular/core';
import type { Toast, ToastType } from '#interface/toast.interface';

// Re-export for backwards compatibility
export type { Toast, ToastType };

/**
 * Signal-based toast notification service.
 *
 * Manages a stack of toast notifications with automatic removal
 * after configurable durations.
 */
@Injectable({ providedIn: 'root' })
export class ToastService {
  private toasts = signal<Toast[]>([]);
  private nextId = 0;

  readonly activeToasts = computed(() => this.toasts());

  show(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = this.nextId++;
    const toast: Toast = { id, message, type, duration };

    this.toasts.update(t => [...t, toast]);

    // Auto-remove after duration
    setTimeout(() => this.remove(id), duration);
  }

  success(message: string, duration = 4000): void {
    this.show(message, 'success', duration);
  }

  error(message: string, duration = 5000): void {
    this.show(message, 'error', duration);
  }

  warning(message: string, duration = 4500): void {
    this.show(message, 'warning', duration);
  }

  info(message: string, duration = 4000): void {
    this.show(message, 'info', duration);
  }

  remove(id: number): void {
    this.toasts.update(t => t.filter(toast => toast.id !== id));
  }
}
