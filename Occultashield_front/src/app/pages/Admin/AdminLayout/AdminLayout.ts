import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './AdminLayout.html',
  styleUrl: './AdminLayout.css'
})
export class AdminLayoutComponent {
  private readonly authService = inject(AuthService);

  logout() {
    this.authService.logout();
  }
}
