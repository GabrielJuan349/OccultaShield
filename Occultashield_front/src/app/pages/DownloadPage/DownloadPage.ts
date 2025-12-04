import { Component, signal, ChangeDetectionStrategy, afterNextRender, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-download-page',
  imports: [RouterLink],
  templateUrl: './DownloadPage.html',
  styleUrl: './DownloadPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DownloadPage {
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly authService = inject(AuthService);

  // --- ESTADO (Signals) ---
  protected readonly videoUrl = signal('https://files.vidstack.io/sprite-fight/720p.mp4');
  protected readonly shareUrl = signal('https://occultashield.io/v/xY2zAbc...');
  protected readonly isDownloading = signal(false);
  protected readonly isCopied = signal(false);
  protected readonly isClient = signal(false);

  constructor() {
    // Verificación inmediata de plataforma
    if (isPlatformBrowser(this.platformId)) {
      this.isClient.set(true);
    }
  }

  logout() {
    this.authService.logout();
  }

  protected startDownload() {
    this.isDownloading.set(true);
    // Simulación de descarga
    setTimeout(() => {
      this.isDownloading.set(false);
      alert('Download started!');
    }, 2000);
  }

  protected copyLink() {
    navigator.clipboard.writeText(this.shareUrl());
    this.isCopied.set(true);
    setTimeout(() => this.isCopied.set(false), 2000);
  }
}
