import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '#services/auth.service';
import { environment } from '#environments/environment';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const token = authService.getToken();
    const isApiUrl = req.url.startsWith(environment.apiUrl) || req.url.startsWith('/api');

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
