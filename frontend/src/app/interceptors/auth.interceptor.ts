/**
 * Authentication HTTP Interceptor.
 *
 * Automatically attaches Bearer tokens to outgoing API requests.
 * Handles both backend API calls and SSR admin endpoint calls.
 *
 * Token attachment rules:
 * - Requests to environment.apiUrl get the token
 * - Requests starting with /api get the token
 * - Requests containing /api/admin get the token (SSR endpoints)
 *
 * Also sets withCredentials: true for cookie handling.
 */

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '#services/auth.service';
import { environment } from '#environments/environment';

/**
 * Functional HTTP interceptor that attaches authentication tokens.
 *
 * @param req - The outgoing HTTP request.
 * @param next - The next handler in the interceptor chain.
 * @returns Observable emitting the (possibly modified) request.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const token = authService.getToken();

    // Check if URL is an API endpoint (backend or SSR admin endpoints)
    const isApiUrl = req.url.startsWith(environment.apiUrl) ||
                     req.url.startsWith('/api') ||
                     req.url.includes('/api/admin');  // FIX: Include SSR admin endpoints

    console.log('🔐 Auth Interceptor:', {
        url: req.url,
        isApiUrl,
        hasToken: !!token,
        tokenLength: token?.length,
        environmentApiUrl: environment.apiUrl
    });

    if (isApiUrl) {
        req = req.clone({
            withCredentials: true,
            setHeaders: token ? {
                Authorization: `Bearer ${token}`
            } : {}
        });
    }

    return next(req);
};
