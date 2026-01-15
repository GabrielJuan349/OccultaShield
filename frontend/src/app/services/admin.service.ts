import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, tap } from 'rxjs/operators';
import { of } from 'rxjs';
import { environment } from '#environments/environment';
import type {
  AdminStats,
  AdminUser,
  AppSettings,
  AuditLogEntry,
  UserRole
} from '#interface/admin.interface';

// Re-export for backwards compatibility
export type {
  AdminStats,
  AdminUser,
  AppSettings,
  AuditLogEntry,
  UserRole
};

// Alias for backwards compatibility
export type User = AdminUser;

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private http = inject(HttpClient);
  // Admin API está en el servidor de auth (puerto 4201), NO en el backend de video (8980)
  private readonly baseUrl = environment.authUrl; // e.g., http://host:4201/api

  // Signals
  stats = signal<AdminStats | null>(null);
  users = signal<AdminUser[]>([]);
  settings = signal<AppSettings>({ closedBetaMode: true });
  auditLog = signal<AuditLogEntry[]>([]);
  loading = signal<boolean>(false);

  // Computed signals
  pendingUsers = computed(() => this.users().filter(u => !u.isApproved));
  approvedUsers = computed(() => this.users().filter(u => u.isApproved));

  // ==========================================================================
  // STATS
  // ==========================================================================

  getStats() {
    this.loading.set(true);
    return this.http.get<AdminStats>(`${this.baseUrl}/admin/stats`).pipe(
      tap(stats => {
        this.stats.set(stats);
        this.loading.set(false);
      }),
      catchError(err => {
        console.error('Error fetching stats', err);
        this.loading.set(false);
        return of(null);
      })
    );
  }

  // ==========================================================================
  // USERS
  // ==========================================================================

  getUsers() {
    this.loading.set(true);
    return this.http.get<AdminUser[]>(`${this.baseUrl}/admin/users`).pipe(
      tap(users => {
        this.users.set(users);
        this.loading.set(false);
      }),
      catchError(err => {
        console.error('Error fetching users', err);
        this.loading.set(false);
        return of([]);
      })
    );
  }

  approveUser(userId: string) {
    return this.http.patch(`${this.baseUrl}/admin/users/${userId}/approve`, {}).pipe(
      tap(() => {
        this.users.update(users =>
          users.map(u =>
            u.id === userId || u.id === `user:${userId}`
              ? { ...u, isApproved: true }
              : u
          )
        );
      })
    );
  }

  rejectUser(userId: string) {
    return this.http.patch(`${this.baseUrl}/admin/users/${userId}/reject`, {}).pipe(
      tap(() => {
        this.users.update(users =>
          users.filter(u => u.id !== userId && u.id !== `user:${userId}`)
        );
      })
    );
  }

  updateUserRole(userId: string, role: UserRole) {
    return this.http.patch(`${this.baseUrl}/admin/users/${userId}/role`, { role }).pipe(
      tap(() => {
        this.users.update(users =>
          users.map(u =>
            u.id === userId || u.id === `user:${userId}`
              ? { ...u, role }
              : u
          )
        );
      })
    );
  }

  // ==========================================================================
  // SETTINGS
  // ==========================================================================

  getSettings() {
    return this.http.get<AppSettings>(`${this.baseUrl}/admin/settings`).pipe(
      tap(settings => this.settings.set(settings)),
      catchError(err => {
        console.error('Error fetching settings', err);
        return of({ closedBetaMode: true });
      })
    );
  }

  toggleClosedBetaMode(enabled: boolean) {
    return this.http.put(`${this.baseUrl}/admin/settings/closedBetaMode`, { value: enabled }).pipe(
      tap(() => {
        this.settings.update(s => ({ ...s, closedBetaMode: enabled }));
      })
    );
  }

  // ==========================================================================
  // AUDIT LOG
  // ==========================================================================

  getAuditLog(action?: string, limit = 50) {
    const params: Record<string, string | number> = { limit };
    if (action) params['action'] = action;

    return this.http.get<AuditLogEntry[]>(`${this.baseUrl}/admin/audit-log`, { params }).pipe(
      tap(log => this.auditLog.set(log)),
      catchError(err => {
        console.error('Error fetching audit log', err);
        return of([]);
      })
    );
  }
}
