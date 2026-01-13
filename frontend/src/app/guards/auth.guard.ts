import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import type { CanActivateFn } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from '#services/auth.service';

/**
 * Guard unificado para manejo de autenticación y roles
 *
 * Uso:
 * - Sin data: Solo verifica autenticación
 * - Con data.role: Verifica autenticación + rol específico
 * - Con data.guestOnly: Permite solo usuarios NO autenticados
 */
export const authGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);

  // En SSR, permitir render (hidratación se encargará en cliente)
  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  // Leer configuración del guard
  const requiredRole = route.data['role'] as string | undefined;
  const guestOnly = route.data['guestOnly'] === true;

  // --- GUEST ONLY MODE ---
  if (guestOnly) {
    // Ya autenticado? Redirigir a upload
    if (authService.isAuthenticated()) {
      router.navigate(['/upload']);
      return false;
    }

    // Verificar sesión por si hay cookie válida
    const hasSession = await authService.checkSession();
    if (hasSession) {
      router.navigate(['/upload']);
      return false;
    }

    // No hay sesión, permitir acceso
    return true;
  }

  // --- AUTHENTICATED MODE (con o sin rol) ---

  // Ya autenticado? Continuar
  let isAuth = authService.isAuthenticated();

  // Si no está en memoria, verificar sesión
  if (!isAuth) {
    const hasSession = await authService.checkSession();
    if (!hasSession) {
      // No hay sesión válida, ir a login
      router.navigate(['/login'], {
        queryParams: { returnUrl: state.url }
      });
      return false;
    }

    // checkSession debería haber actualizado el estado
    isAuth = authService.isAuthenticated();
    if (!isAuth) {
      // Estado inconsistente, ir a login
      router.navigate(['/login'], {
        queryParams: { returnUrl: state.url }
      });
      return false;
    }
  }

  // Autenticado confirmado
  const user = authService.user();
  if (!user) {
    // Autenticado pero sin datos de usuario (estado inconsistente)
    router.navigate(['/login'], {
      queryParams: { returnUrl: state.url }
    });
    return false;
  }

  // Si no requiere rol específico, permitir
  if (!requiredRole) {
    return true;
  }

  // Verificar rol
  if (authService.hasRole(requiredRole)) {
    return true;
  }

  // No tiene el rol requerido, redirigir a upload
  router.navigate(['/upload'], { replaceUrl: true });
  return false;
};

/**
 * DEPRECATED: Usar authGuard con data.role en su lugar
 * Se mantiene por compatibilidad
 */
export const roleGuard: CanActivateFn = authGuard;

/**
 * DEPRECATED: Usar authGuard con data.guestOnly en su lugar
 * Se mantiene por compatibilidad
 */
export const guestGuard: CanActivateFn = authGuard;
