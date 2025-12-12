import { inject } from '@angular/core';
import type { CanActivateFn } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

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
  const requiredRole = route.data['role'] as string;

  if (!requiredRole) {
    console.error('❌ roleGuard: No se especificó el rol requerido en route.data');
    return false;
  }

  // Primero verificar autenticación
  if (!authService.isAuthenticated()) {
    const hasSession = await authService.checkSession();
    if (!hasSession) {
      router.navigate(['/login'], {
        queryParams: { returnUrl: state.url },
      });
      return false;
    }
  }

  // Verificar rol
  if (authService.hasRole(requiredRole)) {
    console.log(`✅ Usuario tiene rol ${requiredRole} - permitiendo acceso`);
    return true;
  }

  console.log(`⚠️ Usuario no tiene rol ${requiredRole} - acceso denegado`);
  router.navigate(['/']);
  return false;
};


/**
 * Guard para rutas de solo invitados (login, register)
 * Redirige a home si el usuario ya está autenticado
 */
export const guestGuard: CanActivateFn = async (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Si ya está autenticado, redirigir a home
  if (authService.isAuthenticated()) {
    console.log('ℹ️ Usuario ya autenticado - redirigiendo a home');
    router.navigate(['/']);
    return false;
  }

  // Verificar si hay sesión activa
  const hasSession = await authService.checkSession();

  if (hasSession) {
    console.log('ℹ️ Sesión activa encontrada - redirigiendo a home');
    router.navigate(['/']);
    return false;
  }

  return true;
};
