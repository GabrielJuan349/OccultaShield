import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';
import { inject } from '@angular/core';
import { Router } from '@angular/router';

/**
 * Interceptor global para manejo de errores HTTP
 * Captura errores y proporciona manejo centralizado con logging estructurado
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Logging estructurado
      console.error('HTTP Error:', {
        url: req.url,
        method: req.method,
        status: error.status,
        statusText: error.statusText,
        message: error.message,
        timestamp: new Date().toISOString()
      });

      // Manejar casos específicos
      if (error.status === 401) {
        console.warn('Unauthorized - redirecting to login');
        router.navigate(['/login'], {
          queryParams: { returnUrl: router.url }
        });
      } else if (error.status === 403) {
        console.warn('Forbidden - insufficient permissions');
        // Podrías mostrar un toast/notification aquí
      } else if (error.status === 500) {
        console.error('Server error:', error.error);
        // Podrías mostrar un toast/notification global aquí
      } else if (error.status === 0) {
        console.error('Network error - server unreachable');
      }

      return throwError(() => error);
    })
  );
};
