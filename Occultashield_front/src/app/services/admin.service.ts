import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, tap } from 'rxjs/operators';
import { of } from 'rxjs';

export interface AdminStats {
  totalUsers: number;
  activeSessions: number;
  totalProcessed: number;
  recentActivity: any[];
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  createdAt: string;
  image?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private http = inject(HttpClient);

  stats = signal<AdminStats | null>(null);
  users = signal<User[]>([]);
  loading = signal<boolean>(false);

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

  updateUserRole(userId: string, role: 'user' | 'admin') {
    return this.http.patch(`/api/admin/users/${userId}/role`, { role }).pipe(
      tap(() => {
        // Update local state
        this.users.update(users =>
          users.map(u => u.id === userId || u.id === `user:${userId}` ? { ...u, role } : u)
        );
      })
    );
  }
}
