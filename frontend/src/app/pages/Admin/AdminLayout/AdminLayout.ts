import { Component, inject, signal, OnInit, PLATFORM_ID } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { AuthService } from '#services/auth.service';

@Component({
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './AdminLayout.html',
  styleUrl: './AdminLayout.css'
})
export class AdminLayoutComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly platformId = inject(PLATFORM_ID);

  // Estado de acceso - solo muestra contenido cuando está verificado
  hasAccess = signal(false);

  async ngOnInit() {
    // En SSR, no hacer nada (el cliente verificará)
    if (!isPlatformBrowser(this.platformId)) {
      console.log('🔐 AdminLayout: SSR detected, skipping');
      return;
    }

    console.log('🔐 AdminLayout: Browser - Starting verification');
    console.log('🔐 AdminLayout: isAuthenticated =', this.authService.isAuthenticated());

    // Verificar sesión si no está autenticado
    if (!this.authService.isAuthenticated()) {
      console.log('🔐 AdminLayout: No auth, calling checkSession...');
      const result = await this.authService.checkSession();
      console.log('🔐 AdminLayout: checkSession result =', result);
    }

    const user = this.authService.user();
    console.log('🔐 AdminLayout: Current user =', user);
    console.log('🔐 AdminLayout: User role =', user?.role);
    console.log('🔐 AdminLayout: hasRole("admin") =', this.authService.hasRole('admin'));

    // Verificar si tiene rol admin
    if (this.authService.hasRole('admin')) {
      console.log('✅ AdminLayout: Access granted!');
      this.hasAccess.set(true);
    } else {
      console.log('⚠️ AdminLayout: Access denied, redirecting to /upload');
      // No tiene permisos, redirigir a upload sin dejar rastro en historial
      this.router.navigate(['/upload'], { replaceUrl: true });
    }
  }

  async logout() {
    console.log('🚪 AdminLayout: Logout button clicked');
    try {
      await this.authService.logout();
      console.log('✅ AdminLayout: Logout completed');
    } catch (error) {
      console.error('❌ AdminLayout: Logout error:', error);
    }
  }
}
