import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import type { CanActivateFn } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from '#services/auth.service';

/**
 * Guard funcional para proteger rutas que requieren autenticación
 * Compatible con Better-Auth - verifica la sesión de forma asíncrona
 */
export const authGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Si ya tenemos usuario en memoria, permitir acceso
  if (authService.isAuthenticated()) {
    console.log('✅ Usuario autenticado - permitiendo acceso a:', state.url);
    return true;
  }

  // Verificar sesión con el servidor (por si hay cookie válida)
  const hasSession = await authService.checkSession();

  if (hasSession) {
    console.log('✅ Sesión válida - permitiendo acceso a:', state.url);
    return true;
  }

  // Si no está autenticado, redirigir al login
  console.log('⚠️ Acceso denegado - Redirigiendo al login');
  router.navigate(['/login'], {
    queryParams: { returnUrl: state.url },
  });

  return false;
};

/**
 * Guard para rutas que requieren un rol específico
 * Lee el rol requerido de route.data['role']
 */
export const roleGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);
  const requiredRole = route.data['role'] as string;

  // En SSR no tenemos acceso a cookies, permitir render y verificar en cliente
  if (!isPlatformBrowser(platformId)) {
    console.log('🔐 roleGuard: SSR detected, allowing render');
    return true;
  }

  if (!requiredRole) {
    console.error('❌ roleGuard: No se especificó el rol requerido en route.data');
    return false;
  }

  // Primero verificar autenticación
  if (!authService.isAuthenticated()) {
    console.log('🔐 roleGuard: Usuario no autenticado, verificando sesión...');
    const hasSession = await authService.checkSession();

    if (!hasSession) {
      console.log('🔐 roleGuard: No hay sesión válida, redirigiendo a login');
      router.navigate(['/login'], {
        queryParams: { returnUrl: state.url },
      });
      return false;
    }

    // CRUCIAL: Después de checkSession, verificar que el usuario se haya cargado
    // Si checkSession retornó true pero user() sigue siendo null, hay un problema
    if (!authService.isAuthenticated()) {
      console.error('🔐 roleGuard: checkSession retornó true pero usuario no se cargó');
      router.navigate(['/login'], {
        queryParams: { returnUrl: state.url },
      });
      return false;
    }
  }

  // Debug: ver qué usuario y rol tenemos
  const user = authService.user();
  console.log('🔐 roleGuard - User:', user);
  console.log('🔐 roleGuard - Required role:', requiredRole, '| User role:', user?.role);

  // Verificar que tengamos un usuario válido
  if (!user) {
    console.error('🔐 roleGuard: Usuario autenticado pero datos de usuario faltantes');
    router.navigate(['/login'], {
      queryParams: { returnUrl: state.url },
    });
    return false;
  }

  // Verificar rol
  if (authService.hasRole(requiredRole)) {
    console.log(`✅ Usuario tiene rol ${requiredRole} - permitiendo acceso`);
    return true;
  }

  // Si no tiene el rol, redirigir a upload sin dejar rastro
  console.log(`⚠️ Usuario no tiene rol ${requiredRole} - redirigiendo a upload`);
  router.navigate(['/upload'], { replaceUrl: true });
  return false;
};


/**
 * Guard para rutas de solo invitados (login, register)
 * Redirige a upload si el usuario ya está autenticado
 */
export const guestGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);

  // En SSR, permitir render
  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  // Si ya está autenticado, redirigir a upload
  if (authService.isAuthenticated()) {
    console.log('ℹ️ Usuario ya autenticado - redirigiendo a upload');
    router.navigate(['/upload']);
    return false;
  }

  // Verificar si hay sesión activa
  const hasSession = await authService.checkSession();

  if (hasSession) {
    console.log('ℹ️ Sesión activa encontrada - redirigiendo a upload');
    router.navigate(['/upload']);
    return false;
  }

  return true;
};
