/**
 * AuthService - Servicio de autenticación usando Better-Auth
 * Proporciona métodos reactivos para login, registro y gestión de sesión
 */
import { Injectable, signal, computed, inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { authClient, signIn, signUp, signOut, getSession } from '#lib/auth-client';
import type { User, Session, UsageType } from '#interface/auth.interface';

// Re-export for backwards compatibility
export type { User, Session, UsageType };

/**
 * Genera un UUID v4 compatible con navegador y servidor
 */
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  // Fallback para Node.js o navegadores antiguos
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Authentication service using Better-Auth with reactive Angular signals.
 *
 * Provides reactive state management for user authentication including:
 * - Email/password login and registration
 * - Session persistence and validation
 * - Role-based access control (admin/user)
 * - Automatic session refresh
 *
 * @example
 * ```typescript
 * const authService = inject(AuthService);
 *
 * // Check authentication
 * if (authService.isAuthenticated()) {
 *   console.log('User:', authService.userName());
 * }
 *
 * // Login
 * await authService.login('user@example.com', 'password');
 * ```
 */
@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private _sessionCheckPromise: Promise<boolean> | null = null;

  /** Private signal for current user state */
  private readonly _user = signal<User | null>(null);
  /** Private signal for current session state */
  private readonly _session = signal<Session | null>(null);
  /** Private signal for loading state */
  private readonly _isLoading = signal(false);
  /** Private signal for error messages */
  private readonly _error = signal<string | null>(null);

  /** Readonly signal exposing current user */
  readonly user = this._user.asReadonly();
  /** Readonly signal exposing current session */
  readonly session = this._session.asReadonly();
  /** Readonly signal indicating async operations in progress */
  readonly isLoading = this._isLoading.asReadonly();
  /** Readonly signal with last error message */
  readonly error = this._error.asReadonly();

  /** Computed signal - true if user is authenticated */
  readonly isAuthenticated = computed(() => this._user() !== null);
  /** Computed signal - user's email address */
  readonly userEmail = computed(() => this._user()?.email ?? null);
  /** Computed signal - user's display name */
  readonly userName = computed(() => this._user()?.name ?? null);
  /** Computed signal - user's role (admin/user) */
  readonly userRole = computed(() => this._user()?.role ?? 'user');

  constructor() {
    // Verificar sesión existente al inicializar (solo en browser)
    if (this.isBrowser) {
      // Guardar la promesa para que los guards puedan esperarla
      this._sessionCheckPromise = this.checkSession();
    }
  }

  /**
   * Verifica si hay una sesión activa
   * Usa localStorage para verificación rápida, luego refresca en background
   */
  async checkSession(): Promise<boolean> {
    if (!this.isBrowser) {
      console.log('🔄 AuthService: Not in browser, returning false');
      return false;
    }

    // Si ya hay una verificación en progreso, esperar a que termine
    if (this._sessionCheckPromise) {
      console.log('🔄 AuthService: Esperando verificación en progreso...');
      return this._sessionCheckPromise;
    }

    // Si ya tenemos un usuario autenticado, verificar rápidamente
    if (this._user() !== null) {
      console.log('✅ AuthService: Usuario ya en memoria:', this._user()?.email);
      return true;
    }

    // NUEVO: Verificación rápida con localStorage
    const savedToken = localStorage.getItem('session_token');
    const savedRole = localStorage.getItem('user_role');

    if (savedToken && savedRole) {
      console.log('⚡ AuthService: Verificación rápida con localStorage - rol:', savedRole);

      // Crear usuario temporal con rol para acceso inmediato
      this._user.set({
        id: 'pending',
        email: 'loading...',
        name: 'loading...',
        role: savedRole,
        emailVerified: false,
        createdAt: new Date(),
        updatedAt: new Date(),
      } as User);

      this._session.set({
        id: 'pending',
        userId: 'pending',
        token: savedToken,
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
      });

      // Refrescar datos completos del servidor en background (no bloquea)
      this.refreshUserFromServer();

      return true;
    }

    this._isLoading.set(true);
    this._error.set(null);
    console.log('🔄 AuthService: Iniciando checkSession (sin localStorage)...');

    // Create new promise for this check
    const checkPromise = (async () => {
      try {
        console.log('🔄 AuthService: Calling getSession()...');
        const result = await getSession({
          fetchOptions: {
            credentials: 'include',
          },
        });
        console.log('🔄 AuthService: getSession raw result:', JSON.stringify(result, null, 2));

        if (result.data?.session && result.data?.user) {
          const userData = result.data.user as unknown as User;
          console.log('✅ AuthService: Sesión válida para:', userData.email);
          console.log('   Rol del usuario:', userData.role || 'no role set');

          // Recuperar token de localStorage si better-auth no lo devuelve
          let token = result.data.session.token;
          if (!token) {
            token = localStorage.getItem('session_token') || '';
            console.log('   Token recuperado de localStorage:', !!token);
          }

          this._user.set(result.data.user as User);
          this._session.set({
            ...result.data.session,
            token: token
          } as Session);

          return true;
        }

        // Check if there was an error response
        if (result.error) {
          console.warn('⚠️ AuthService: getSession returned error:', result.error);
        }

        console.warn('⚠️ AuthService: No hay sesión activa');
        this._user.set(null);
        this._session.set(null);
        // Don't remove token here, it might still be valid for API calls
        return false;
      } catch (error) {
        console.error('❌ AuthService: Error en checkSession:', error);
        // Don't clear user state on error - the session might still be valid
        // Only clear if we're sure it's an auth error
        return false;
      } finally {
        this._isLoading.set(false);
        // Clear the promise after completion
        this._sessionCheckPromise = null;
      }
    })();

    // Store and return the promise
    this._sessionCheckPromise = checkPromise;
    return checkPromise;
  }

  /**
   * Inicia sesión con email y contraseña
   */
  async login(email: string, password: string): Promise<boolean> {
    if (!this.isBrowser) return false;

    this._isLoading.set(true);
    this._error.set(null);

    try {
      const result = await signIn.email({
        email,
        password,
      });

      if (result.error) {
        this._error.set(result.error.message ?? 'Error al iniciar sesión');
        return false;
      }

      if (result.data?.user) {
        const userData = result.data.user as User;
        this._user.set(userData);
        // Better-Auth devuelve token, creamos objeto session
        if (result.data.token) {
          localStorage.setItem('session_token', result.data.token);
          // Guardar rol para verificación rápida (localStorage)
          const userRole = userData.role || 'user';
          localStorage.setItem('user_role', userRole);
          console.log('💾 Guardado en localStorage: token + role =', userRole);

          this._session.set({
            id: generateUUID(),
            userId: userData.id,
            token: result.data.token,
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 días
          });
        }
        return true;
      }

      this._error.set('Respuesta inesperada del servidor');
      return false;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error de conexión';
      this._error.set(message);
      console.error('Login error:', error);
      return false;
    } finally {
      this._isLoading.set(false);
    }
  }

  /**
   * Registra un nuevo usuario
   */
  async register(
    email: string,
    password: string,
    name: string,
    usageType: UsageType = 'individual'
  ): Promise<boolean> {
    if (!this.isBrowser) return false;

    this._isLoading.set(true);
    this._error.set(null);

    try {
      // Note: usageType is passed as additional field; Better-Auth will save it
      const result = await signUp.email({
        email,
        password,
        name,
        // @ts-expect-error - usageType is defined in server-side additionalFields
        usageType,
      });

      if (result.error) {
        this._error.set(result.error.message ?? 'Error al registrar usuario');
        return false;
      }

      if (result.data?.user) {
        this._user.set(result.data.user as User);
        // Better-Auth devuelve token, creamos objeto session
        if (result.data.token) {
          localStorage.setItem('session_token', result.data.token);
          this._session.set({
            id: generateUUID(),
            userId: result.data.user.id,
            token: result.data.token,
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 días
          });
        }
        return true;
      }

      this._error.set('Respuesta inesperada del servidor');
      return false;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error de conexión';
      this._error.set(message);
      console.error('Register error:', error);
      return false;
    } finally {
      this._isLoading.set(false);
    }
  }

  /**
   * Cierra la sesión actual
   */
  async logout(): Promise<void> {
    if (!this.isBrowser) return;

    console.log('🚪 AuthService: Starting logout...');
    this._isLoading.set(true);

    try {
      console.log('🚪 AuthService: Calling signOut()...');
      // signOut necesita enviar la cookie para que el servidor sepa qué sesión borrar
      const result = await signOut({
        fetchOptions: {
          credentials: 'include',
        },
      });
      console.log('🚪 AuthService: signOut result:', result);
    } catch (error) {
      console.error('❌ AuthService: Logout error:', error);
    } finally {
      console.log('🚪 AuthService: Clearing local state...');
      this._user.set(null);
      this._session.set(null);
      this._isLoading.set(false);
      localStorage.removeItem('session_token');
      localStorage.removeItem('user_role');

      // Redirigir y forzar recarga completa para limpiar todo el estado
      window.location.href = '/login';
    }
  }

  /**
   * Limpia el error actual
   */
  clearError(): void {
    this._error.set(null);
  }

  /**
   * Obtiene el token de sesión actual (para headers de API)
   */
  getToken(): string | null {
    // Primero intentar desde la sesión en memoria
    const sessionToken = this._session()?.token;
    if (sessionToken) {
      return sessionToken;
    }

    // Fallback a localStorage si no está en memoria
    if (this.isBrowser) {
      return localStorage.getItem('session_token');
    }

    return null;
  }

  /**
   * Verifica si el usuario tiene un rol específico (case-insensitive)
   */
  hasRole(role: string): boolean {
    const userRole = this._user()?.role;
    if (!userRole) {
      // Fallback: verificar en localStorage para verificación rápida
      if (this.isBrowser) {
        const savedRole = localStorage.getItem('user_role');
        if (savedRole) {
          console.log('🔐 hasRole check (localStorage):', { savedRole, requiredRole: role });
          return savedRole.toLowerCase() === role.toLowerCase();
        }
      }
      return false;
    }
    console.log('🔐 hasRole check:', { userRole, requiredRole: role });
    return userRole.toLowerCase() === role.toLowerCase();
  }

  /**
   * Verifica si el usuario es administrador
   */
  isAdmin(): boolean {
    return this.hasRole('admin');
  }

  /**
   * Refresca los datos del usuario desde el servidor en background
   */
  private async refreshUserFromServer(): Promise<void> {
    try {
      const result = await getSession({ fetchOptions: { credentials: 'include' } });
      if (result.data?.user) {
        const userData = result.data.user as User;
        this._user.set(userData);
        // Actualizar rol en localStorage si cambió
        if (this.isBrowser && userData.role) {
          localStorage.setItem('user_role', userData.role);
        }
        console.log('🔄 Usuario refrescado desde servidor:', userData.email);
      }
    } catch (e) {
      console.warn('⚠️ No se pudo refrescar usuario del servidor:', e);
    }
  }
}
