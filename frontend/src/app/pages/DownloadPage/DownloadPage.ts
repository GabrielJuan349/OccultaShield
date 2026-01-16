/**
 * Download Page Component for OccultaShield.
 *
 * Final step in the video processing pipeline. Allows users to:
 * - Preview the anonymized video
 * - Download the processed video file
 * - Copy a shareable link
 *
 * Features:
 * - Secure video streaming with authentication
 * - Download progress tracking
 * - Share URL generation
 * - Platform-aware rendering (SSR compatible)
 *
 * @example
 * Route: /download/:id
 * Flow: Upload → Processing → Review → **Download**
 */

import { Component, signal, ChangeDetectionStrategy, PLATFORM_ID, inject, OnInit } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '#services/auth.service';
import { VideoService } from '#services/video.service';
import { environment } from '#environments/environment';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

/**
 * Processed video download page.
 *
 * Provides video preview, download functionality, and link sharing
 * for completed anonymization jobs.
 */
@Component({
  imports: [RouterLink],
  templateUrl: './DownloadPage.html',
  styleUrl: './DownloadPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DownloadPage implements OnInit {
  private readonly platformId = inject(PLATFORM_ID);
  protected readonly authService = inject(AuthService);
  private readonly videoService = inject(VideoService);
  private readonly route = inject(ActivatedRoute);
  private readonly sanitizer = inject(DomSanitizer);

  // --- ESTADO (Signals) ---
  protected readonly videoUrl = signal<SafeUrl | null>(null);
  protected readonly shareUrl = signal<string>('');
  protected readonly isDownloading = signal(false);
  protected readonly isCopied = signal(false);
  protected readonly isClient = signal(false);
  protected readonly videoId = signal<string | null>(null);

  constructor() {
    // Verificación inmediata de plataforma
    if (isPlatformBrowser(this.platformId)) {
      this.isClient.set(true);
    }
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.videoId.set(id);
      // Build the video streaming URL with auth token
      const token = this.authService.getToken();
      const baseUrl = environment.apiUrl.replace('/video', '');
      const streamUrl = `${baseUrl}/video/${id}/download${token ? `?token=${token}` : ''}`;
      this.videoUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(streamUrl));

      // Build share URL
      const origin = isPlatformBrowser(this.platformId) ? window.location.origin : '';
      this.shareUrl.set(`${origin}/download/${id}`);
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
