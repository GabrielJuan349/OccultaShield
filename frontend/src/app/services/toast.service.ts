/**
 * Toast Notification Service
 * Signal-based toast notifications for admin actions
 */
import { Injectable, signal, computed } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
    id: number;
    message: string;
    type: ToastType;
    duration: number;
}

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
