import { Component, inject, OnInit } from '@angular/core';
import { AdminService } from '../../../services/admin.service';
import { DatePipe, NgOptimizedImage } from '@angular/common';

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [DatePipe, NgOptimizedImage],
  templateUrl: './Users.html',
  styleUrl: './Users.css'
})
export class UsersComponent implements OnInit {
  adminService = inject(AdminService);
  users = this.adminService.users;
  loading = this.adminService.loading;

  ngOnInit() {
    this.adminService.getUsers().subscribe();
  }

  toggleAdmin(user: any) {
    const newRole = user.role === 'admin' ? 'user' : 'admin';
    if (confirm(`¿Estás seguro de cambiar el rol de ${user.name} a ${newRole}?`)) {
      this.adminService.updateUserRole(user.id, newRole).subscribe();
    }
  }
}
