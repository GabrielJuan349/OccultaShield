import { Component, inject, OnInit } from '@angular/core';
import { AdminService } from '#services/admin.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-admin-dashboard',
  imports: [DatePipe],
  templateUrl: './Dashboard.html',
  styleUrl: './Dashboard.css'
})
export class DashboardComponent implements OnInit {
  adminService = inject(AdminService);
  stats = this.adminService.stats;
  loading = this.adminService.loading;

  ngOnInit() {
    this.adminService.getStats().subscribe();
  }
}
