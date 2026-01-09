import { Component, inject, OnInit, signal } from '@angular/core';
import { AdminService } from '#services/admin.service';
import { DatePipe } from '@angular/common';

@Component({
    selector: 'app-admin-audit-log',
    imports: [DatePipe],
    templateUrl: './AuditLog.html',
    styleUrl: './AuditLog.css'
})
export class AuditLogComponent implements OnInit {
    private adminService = inject(AdminService);

    auditLog = this.adminService.auditLog;
    loading = this.adminService.loading;
    selectedAction = signal<string>('all');

    readonly actionTypes = [
        { value: 'all', label: 'Todas las acciones' },
        { value: 'user_approved', label: 'Aprobaciones' },
        { value: 'user_rejected', label: 'Rechazos' },
        { value: 'role_changed', label: 'Cambios de rol' },
        { value: 'settings_changed', label: 'Cambios de config' }
    ];

    ngOnInit() {
        this.loadLogs();
    }

    loadLogs() {
        const action = this.selectedAction() === 'all' ? undefined : this.selectedAction();
        this.adminService.getAuditLog(action).subscribe();
    }

    onFilterChange(action: string) {
        this.selectedAction.set(action);
        this.loadLogs();
    }

    getActionLabel(action: string): string {
        const labels: Record<string, string> = {
            'user_approved': '✅ Usuario aprobado',
            'user_rejected': '❌ Usuario rechazado',
            'role_changed': '🔄 Rol cambiado',
            'settings_changed': '⚙️ Configuración cambiada'
        };
        return labels[action] || action;
    }
}
