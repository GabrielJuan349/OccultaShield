import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

// @Component({
//   selector: 'app-download-page',
//   imports: [],
//   template: `<p>DownloadPage works!</p>`,
//   styleUrl: './DownloadPage.css',
//   changeDetection: ChangeDetectionStrategy.OnPush,
// })
// export class DownloadPage { }
@Component({
  selector: 'app-result',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="bg-[#f0f4f8] font-roboto text-slate-800 min-h-screen">
      <div class="flex min-h-screen items-center justify-center p-4 sm:p-6 lg:p-8">
        <main class="w-full max-w-7xl">
          <header class="mb-8 text-center">
            <h1 class="text-4xl font-black text-slate-900 sm:text-5xl md:text-6xl">
              Your Video is <span class="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">Ready</span>
            </h1>
            <p class="mt-4 max-w-3xl mx-auto text-lg text-slate-600">
              Your video has been successfully processed with the selected privacy modifications. Preview the final result below before downloading.
            </p>
          </header>

          <div class="flex flex-col gap-8">
            <!-- Video Player Placeholder -->
            <div class="rounded-xl border border-slate-200 bg-white shadow-lg shadow-cyan-500/10 overflow-hidden">
              <div class="aspect-video w-full bg-[#0a0c1c] flex items-center justify-center group cursor-pointer relative">
                <div class="text-center text-slate-400 flex flex-col items-center transition-transform group-hover:scale-110 duration-300">
                  <!-- Play Circle Icon -->
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-20 h-20 text-slate-600 group-hover:text-cyan-400 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polygon points="10 8 16 12 10 16 10 8"></polygon></svg>
                  <p class="mt-2 font-medium">Video Preview</p>
                </div>
              </div>
            </div>

            <!-- Action Grid -->
            <div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">

              <!-- Main CTA -->
              <div class="lg:col-span-2 flex flex-col items-center justify-center rounded-xl border border-blue-500/50 bg-white p-6 shadow-[0_0_15px_0_rgba(6,182,212,0.5)]">
                <h2 class="text-2xl font-bold text-slate-900 mb-4">Download Your Video</h2>
                <p class="text-slate-600 mb-6 text-center">Get the final, privacy-enhanced version of your video file.</p>
                <button class="w-full max-w-xs flex items-center justify-center gap-3 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-8 py-4 text-lg font-bold text-white shadow-lg transition-all hover:from-cyan-600 hover:to-blue-700 hover:shadow-blue-500/30 focus:outline-none focus:ring-4 focus:ring-blue-300 transform active:scale-95">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                  Download Video
                </button>
              </div>

              <!-- Share -->
              <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-lg">
                <div class="flex items-center gap-4 mb-4">
                  <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                  </div>
                  <div>
                    <h3 class="text-xl font-bold text-slate-900">Share Video</h3>
                    <p class="text-sm text-slate-500">Get a shareable link</p>
                  </div>
                </div>
                <div class="relative flex items-center">
                  <input
                    class="w-full rounded-md border-slate-200 bg-slate-100 p-2 pr-10 text-sm text-slate-500 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    readonly
                    type="text"
                    value="https://occultashield.io/v/xY2zAbc..."
                  />
                  <button class="absolute right-2 text-slate-500 hover:text-blue-500 transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  </button>
                </div>
              </div>

              <!-- Further Actions -->
              <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-lg">
                <div class="flex items-center gap-4 mb-4">
                  <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                  </div>
                  <div>
                    <h3 class="text-xl font-bold text-slate-900">Further Actions</h3>
                    <p class="text-sm text-slate-500">Need more options?</p>
                  </div>
                </div>
                <div class="flex flex-col space-y-3">
                  <a href="#" class="flex items-center gap-2 text-slate-600 hover:text-cyan-600 font-medium transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg> Re-edit Modifications
                  </a>
                  <a routerLink="/upload" class="flex items-center gap-2 text-slate-600 hover:text-cyan-600 font-medium transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg> Process Another Video
                  </a>
                </div>
              </div>

            </div>
          </div>
        </main>
      </div>
    </div>
  `
})
export class DownloadPage {}
