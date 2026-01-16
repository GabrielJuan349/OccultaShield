/**
 * Global HTTP Error Interceptor.
 *
 * Provides centralized error handling for all HTTP requests including:
 * - Structured error logging with timestamps
 * - Automatic 401 handling (redirect to login if no token)
 * - 403 forbidden handling
 * - 500 server error logging
 * - Network error detection (status 0)
 *
 * @example
 * Automatically applied via app.config.ts provideHttpClient(withInterceptors([errorInterceptor]))
 */

import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError } from 'rxjs/operators';
import { throwError } from 'rxjs';
import { inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';

/**
 * Functional HTTP interceptor for global error handling.
 *
 * Catches all HTTP errors, logs them with structured metadata,
 * and handles authentication redirects when appropriate.
 *
 * @param req - The outgoing HTTP request.
 * @param next - The next handler in the interceptor chain.
 * @returns Observable that emits the response or throws the error.
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);

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
        // Solo redirigir si NO hay token en localStorage (usuario realmente no autenticado)
        // Si hay token, el problema es otro (backend rechazó, token expirado, etc.)
        const hasToken = isPlatformBrowser(platformId) && !!localStorage.getItem('session_token');
        const isOnLoginPage = router.url.startsWith('/login');

        if (!hasToken && !isOnLoginPage) {
          console.warn('Unauthorized - redirecting to login');
          router.navigate(['/login'], {
            queryParams: { returnUrl: router.url }
          });
        } else {
          console.warn('401 Error but user has token - not redirecting (token may be expired or endpoint issue)');
        }
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
