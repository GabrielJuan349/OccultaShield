import { Component, signal, ChangeDetectionStrategy, afterNextRender, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '#services/auth.service';
import { VideoService } from '#services/video.service';

@Component({
  imports: [RouterLink],
  templateUrl: './DownloadPage.html',
  styleUrl: './DownloadPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DownloadPage {
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly authService = inject(AuthService);
  private readonly videoService = inject(VideoService);
  private readonly route = inject(ActivatedRoute);

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
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;

    this.isDownloading.set(true);

    this.videoService.downloadVideo(id).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `anonymized_${id}.mp4`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        this.isDownloading.set(false);
      },
      error: (err) => {
        console.error('Download failed', err);
        this.isDownloading.set(false);
        alert('Download failed. Please try again.');
      }
    });
  }

  protected copyLink() {
    navigator.clipboard.writeText(this.shareUrl());
    this.isCopied.set(true);
    setTimeout(() => this.isCopied.set(false), 2000);
  }
}
