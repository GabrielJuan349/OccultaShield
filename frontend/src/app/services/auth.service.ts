/**
 * AuthService - Servicio de autenticación usando Better-Auth
 * Proporciona métodos reactivos para login, registro y gestión de sesión
 */
import { Injectable, signal, computed, inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { authClient, signIn, signUp, signOut, getSession } from '#lib/auth-client';

// Tipos
export interface User {
  id: string;
  email: string;
  name: string;
  image?: string;
  role?: string;
  emailVerified: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface Session {
  id: string;
  userId: string;
  token: string;
  expiresAt: Date;
}

export interface AuthState {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  error: string | null;
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

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
      this.checkSession();
    }
  }

  /**
   * Verifica si hay una sesión activa
   */
  async checkSession(): Promise<boolean> {
    if (!this.isBrowser) return false;

    this._isLoading.set(true);
    this._error.set(null);

    try {
      const result = await getSession();

      if (result.data?.session && result.data?.user) {
        this._user.set(result.data.user as User);
        this._session.set(result.data.session as Session);
        return true;
      }

      this._user.set(null);
      this._session.set(null);
      return false;
    } catch (error) {
      console.error('Error checking session:', error);
      this._user.set(null);
      this._session.set(null);
      return false;
    } finally {
      this._isLoading.set(false);
    }
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
          this._session.set({
            id: crypto.randomUUID(),
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
  async register(email: string, password: string, name: string): Promise<boolean> {
    if (!this.isBrowser) return false;

    this._isLoading.set(true);
    this._error.set(null);

    try {
      const result = await signUp.email({
        email,
        password,
        name,
      });

      if (result.error) {
        this._error.set(result.error.message ?? 'Error al registrar usuario');
        return false;
      }

      if (result.data?.user) {
        this._user.set(result.data.user as User);
        // Better-Auth devuelve token, creamos objeto session
        if (result.data.token) {
          this._session.set({
            id: crypto.randomUUID(),
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

    this._isLoading.set(true);

    try {
      await signOut();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this._user.set(null);
      this._session.set(null);
      this._isLoading.set(false);
      this.router.navigate(['/login']);
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
    return this._session()?.token ?? null;
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
