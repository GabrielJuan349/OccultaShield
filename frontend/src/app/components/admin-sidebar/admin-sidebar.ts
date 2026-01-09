import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '#services/auth.service';

@Component({
    selector: 'app-admin-sidebar',
    imports: [RouterLink, RouterLinkActive],
    template: `
    <aside class="admin-sidebar">
      <div class="sidebar-header">
        <span class="logo">🛡️</span>
        <span class="title">Admin Panel</span>
      </div>
      
      <nav class="sidebar-nav">
        <a routerLink="/admin" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">
          <span class="icon">📊</span>
          <span>Dashboard</span>
        </a>
        <a routerLink="/admin/users" routerLinkActive="active">
          <span class="icon">👥</span>
          <span>Usuarios</span>
        </a>
        <a routerLink="/admin/settings" routerLinkActive="active">
          <span class="icon">⚙️</span>
          <span>Configuración</span>
        </a>
        <a routerLink="/admin/audit-log" routerLinkActive="active">
          <span class="icon">📋</span>
          <span>Auditoría</span>
        </a>
      </nav>
      
      <div class="sidebar-footer">
        <a routerLink="/">
          <span class="icon">🏠</span>
          <span>Volver al sitio</span>
        </a>
      </div>
    </aside>
  `,
    styles: [`
    .admin-sidebar {
      width: 240px;
      height: 100vh;
      background: var(--surface-elevated);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      position: fixed;
      left: 0;
      top: 0;
    }

    .sidebar-header {
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--border-color);
    }

    .logo {
      font-size: 1.5rem;
    }

    .title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--text-primary);
    }

    .sidebar-nav {
      flex: 1;
      padding: 16px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sidebar-nav a,
    .sidebar-footer a {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: 8px;
      color: var(--text-secondary);
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .sidebar-nav a:hover,
    .sidebar-footer a:hover {
      background: var(--surface);
      color: var(--text-primary);
    }

    .sidebar-nav a.active {
      background: var(--primary);
      color: white;
    }

    .icon {
      font-size: 1.1rem;
      width: 24px;
      text-align: center;
    }

    .sidebar-footer {
      padding: 16px 12px;
      border-top: 1px solid var(--border-color);
    }

    .sidebar-footer a {
      color: var(--text-secondary);
    }
  `]
})
export class AdminSidebarComponent { }
