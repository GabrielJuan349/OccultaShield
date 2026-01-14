/**
 * Toast notification interfaces and types
 * Used by: ToastService, ToastComponent
 */

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
  duration: number;
}

export interface ToastOptions {
  message: string;
  type?: ToastType;
  duration?: number;
}
