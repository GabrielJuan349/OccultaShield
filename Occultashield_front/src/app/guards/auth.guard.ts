import { inject } from '@angular/core';
import type { CanActivateFn } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Guard funcional para proteger rutas que requieren autenticación
 * Verifica si existe un JWT válido antes de permitir el acceso
 */
export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Verificar la validez del token
  authService.checkTokenValidity();

  if (authService.isAuthenticated()) {
    console.log('✅ Usuario autenticado - permitiendo acceso a:', state.url);
    return true;
  }

  // Si no está autenticado, redirigir al login
  // Guardar la URL intentada para redirigir después del login
  console.log('⚠️ Acceso denegado - Redirigiendo al login');
  router.navigate(['/login']);

  return false;
};
