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

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);
  private _sessionCheckPromise: Promise<boolean> | null = null;

  // Estado reactivo
  private readonly _user = signal<User | null>(null);
  private readonly _session = signal<Session | null>(null);
  private readonly _isLoading = signal(false);
  private readonly _error = signal<string | null>(null);

  // Señales públicas de solo lectura
  readonly user = this._user.asReadonly();
  readonly session = this._session.asReadonly();
  readonly isLoading = this._isLoading.asReadonly();
  readonly error = this._error.asReadonly();

  // Señales computadas
  readonly isAuthenticated = computed(() => this._user() !== null);
  readonly userEmail = computed(() => this._user()?.email ?? null);
  readonly userName = computed(() => this._user()?.name ?? null);
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

    this._isLoading.set(true);
    this._error.set(null);
    console.log('🔄 AuthService: Iniciando checkSession...');

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
   * Verifica si el usuario tiene un rol específico
   */
  hasRole(role: string): boolean {
    return this._user()?.role === role;
  }

  /**
   * Verifica si el usuario es administrador
   */
  isAdmin(): boolean {
    return this.hasRole('admin');
  }
}
