import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, tap } from 'rxjs/operators';
import { of } from 'rxjs';

export interface AdminStats {
  total_users: number;
  pending_users: number;
  approved_users: number;
  total_videos: number;
  total_violations: number;
  active_sessions: number;
  recentActivity: {
    id: string;
    action: string;
    fileName?: string;
    status: string;
    createdAt: string;
  }[];
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  isApproved: boolean;
  usageType: 'individual' | 'researcher' | 'agency';
  createdAt: string;
  image?: string;
}

export interface AppSettings {
  closedBetaMode: boolean;
}

export interface AuditLogEntry {
  id: string;
  userId: string;
  action: string;
  targetId?: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private http = inject(HttpClient);

  // Signals
  stats = signal<AdminStats | null>(null);
  users = signal<User[]>([]);
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
    return this.http.get<AdminStats>('/api/admin/stats').pipe(
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
    return this.http.get<User[]>('/api/admin/users').pipe(
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
    return this.http.patch(`/api/admin/users/${userId}/approve`, {}).pipe(
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
    return this.http.patch(`/api/admin/users/${userId}/reject`, {}).pipe(
      tap(() => {
        this.users.update(users =>
          users.filter(u => u.id !== userId && u.id !== `user:${userId}`)
        );
      })
    );
  }

  updateUserRole(userId: string, role: 'user' | 'admin') {
    return this.http.patch(`/api/admin/users/${userId}/role`, { role }).pipe(
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
    return this.http.get<AppSettings>('/api/admin/settings').pipe(
      tap(settings => this.settings.set(settings)),
      catchError(err => {
        console.error('Error fetching settings', err);
        return of({ closedBetaMode: true });
      })
    );
  }

  toggleClosedBetaMode(enabled: boolean) {
    return this.http.put('/api/admin/settings/closedBetaMode', { value: enabled }).pipe(
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

    return this.http.get<AuditLogEntry[]>('/api/admin/audit-log', { params }).pipe(
      tap(log => this.auditLog.set(log)),
      catchError(err => {
        console.error('Error fetching audit log', err);
        return of([]);
      })
    );
  }
}
