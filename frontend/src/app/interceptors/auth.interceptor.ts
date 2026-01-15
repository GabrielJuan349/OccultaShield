import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '#services/auth.service';
import { environment } from '#environments/environment';

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
