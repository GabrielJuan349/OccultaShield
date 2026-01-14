import { Component, inject, OnInit, signal, computed, ChangeDetectionStrategy } from '@angular/core';
import { AdminService } from '#services/admin.service';
import type { AdminUser as User } from '#interface/admin.interface';
import { ToastService } from '#services/toast.service';
import { DatePipe, NgOptimizedImage } from '@angular/common';

@Component({
  selector: 'app-admin-users',
  imports: [DatePipe, NgOptimizedImage],
  templateUrl: './Users.html',
  styleUrl: './Users.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UsersComponent implements OnInit {
  private adminService = inject(AdminService);
  private toast = inject(ToastService);

  // From service
  users = this.adminService.users;
  pendingUsers = this.adminService.pendingUsers;
  approvedUsers = this.adminService.approvedUsers;
  loading = this.adminService.loading;

  // Local state
  activeTab = signal<'all' | 'pending' | 'approved'>('pending');

  // Computed: beta mode from settings
  closedBetaMode = computed(() => this.adminService.settings().closedBetaMode);

  // Computed: displayed users based on tab
  displayedUsers = computed(() => {
    switch (this.activeTab()) {
      case 'pending': return this.pendingUsers();
      case 'approved': return this.approvedUsers();
      default: return this.users();
    }
  });

  ngOnInit() {
    this.adminService.getUsers().subscribe();
    this.adminService.getSettings().subscribe();
  }

  setTab(tab: 'all' | 'pending' | 'approved') {
    this.activeTab.set(tab);
  }

  toggleBetaMode(event: Event) {
    const enabled = (event.target as HTMLInputElement).checked;
    this.adminService.toggleClosedBetaMode(enabled).subscribe({
      next: () => this.toast.success(enabled ? 'Modo beta activado' : 'Modo beta desactivado'),
      error: () => this.toast.error('Error al cambiar modo beta')
    });
  }

  approveUser(user: User) {
    if (confirm(`¿Aprobar acceso para ${user.name}?`)) {
      this.adminService.approveUser(user.id).subscribe({
        next: () => this.toast.success(`${user.name} aprobado y notificado por email`),
        error: () => this.toast.error('Error al aprobar usuario')
      });
    }
  }

  rejectUser(user: User) {
    if (confirm(`¿Rechazar y eliminar la cuenta de ${user.name}? Esta acción no se puede deshacer.`)) {
      this.adminService.rejectUser(user.id).subscribe({
        next: () => this.toast.success(`${user.name} rechazado y eliminado`),
        error: () => this.toast.error('Error al rechazar usuario')
      });
    }
  }

  toggleAdmin(user: User) {
    const newRole = user.role === 'admin' ? 'user' : 'admin';
    if (confirm(`¿Cambiar el rol de ${user.name} a ${newRole}?`)) {
      this.adminService.updateUserRole(user.id, newRole).subscribe({
        next: () => this.toast.success(`Rol de ${user.name} cambiado a ${newRole}`),
        error: () => this.toast.error('Error al cambiar rol')
      });
    }
  }
}
