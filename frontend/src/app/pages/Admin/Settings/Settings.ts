import { Component, inject, OnInit } from '@angular/core';
import { AdminService } from '#services/admin.service';
import { ToastService } from '#services/toast.service';

@Component({
    selector: 'app-admin-settings',
    templateUrl: './Settings.html',
    styleUrl: './Settings.css'
})
export class SettingsComponent implements OnInit {
    private adminService = inject(AdminService);
    private toast = inject(ToastService);

    settings = this.adminService.settings;
    loading = this.adminService.loading;

    ngOnInit() {
        this.adminService.getSettings().subscribe();
    }

    toggleClosedBeta() {
        const current = this.settings()?.closedBetaMode ?? true;
        this.adminService.toggleClosedBetaMode(!current).subscribe({
            next: () => {
                this.toast.success(
                    !current
                        ? 'Modo beta cerrado activado. Los nuevos usuarios requerirán aprobación.'
                        : 'Modo beta cerrado desactivado. Los nuevos usuarios tendrán acceso inmediato.'
                );
            },
            error: () => this.toast.error('Error al cambiar la configuración')
        });
    }
}
