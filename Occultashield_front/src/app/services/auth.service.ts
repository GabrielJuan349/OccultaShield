import { Injectable, signal, PLATFORM_ID, inject } from '@angular/core';
import { Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly TOKEN_KEY = 'jwt_token';
  private platformId = inject(PLATFORM_ID);
  private isBrowser: boolean;

  // Signal para el estado de autenticación
  isAuthenticated = signal<boolean>(false);

  constructor(private router: Router) {
    this.isBrowser = isPlatformBrowser(this.platformId);

    // Solo verificar el token en el navegador
    if (this.isBrowser) {
      this.isAuthenticated.set(this.hasValidToken());
      this.checkTokenValidity();
    }
  }

  /**
   * Verifica si existe un token en localStorage
   */
  private hasValidToken(): boolean {
    if (!this.isBrowser) {
      return false;
    }

    const token = this.getToken();
    if (!token) {
      return false;
    }

    // Verificar si el token ha expirado
    return !this.isTokenExpired(token);
  }

  /**
   * Obtiene el token del localStorage
   */
  getToken(): string | null {
    if (!this.isBrowser) {
      return null;
    }
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Guarda el token en localStorage
   */
  setToken(token: string): void {
    if (!this.isBrowser) {
      return;
    }
    localStorage.setItem(this.TOKEN_KEY, token);
    this.isAuthenticated.set(true);
  }

  /**
   * Elimina el token y cierra sesión
   */
  logout(): void {
    if (this.isBrowser) {
      localStorage.removeItem(this.TOKEN_KEY);
    }
    this.isAuthenticated.set(false);
    this.router.navigate(['/login']);
  }

  /**
   * Verifica si el token JWT ha expirado
   */
  private isTokenExpired(token: string): boolean {
    try {
      const payload = this.decodeToken(token);
      if (!payload || !payload.exp) {
        return true;
      }

      // exp está en segundos, Date.now() está en milisegundos
      const expirationDate = payload.exp * 1000;
      return Date.now() >= expirationDate;
    } catch (error) {
      console.error('Error al decodificar el token:', error);
      return true;
    }
  }

  /**
   * Decodifica el payload del JWT (sin verificar la firma)
   */
  private decodeToken(token: string): any {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error('Token JWT inválido');
      }

      const payload = parts[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded);
    } catch (error) {
      console.error('Error al decodificar el token:', error);
      return null;
    }
  }

  /**
   * Verifica la validez del token actual
   */
  checkTokenValidity(): void {
    if (!this.isBrowser) {
      this.isAuthenticated.set(false);
      return;
    }

    const isValid = this.hasValidToken();
    this.isAuthenticated.set(isValid);

    if (!isValid && this.getToken()) {
      // Si hay un token pero no es válido, eliminarlo
      this.logout();
    }
  }

  /**
   * Obtiene información del usuario desde el token
   */
  getUserInfo(): any {
    if (!this.isBrowser) {
      return null;
    }

    const token = this.getToken();
    if (!token) {
      return null;
    }

    return this.decodeToken(token);
  }
}
