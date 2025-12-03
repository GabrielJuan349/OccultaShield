import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { Router } from '@angular/router';

// @Component({
//   selector: 'app-upload-page',
//   imports: [],
//   template: `<p>UploadPage works!</p>`,
//   styleUrl: './UploadPage.css',
//   changeDetection: ChangeDetectionStrategy.OnPush,
// })
// export class UploadPage { }
@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="min-h-screen bg-[#F0F4F8] font-sans text-gray-800 flex flex-col items-center justify-center p-4">
      <header class="mb-8 text-center">
        <div class="flex items-center justify-center gap-4 mb-2">
          <img
            alt="OccultaShield falcon mascot"
            class="h-16 w-16 sm:h-20 sm:w-20"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCg5sxHGSgIYK7j6VIsiUdKc7VTSWM0FMsWKC4dot1rBzK2c3hHor4XwN3jCLT209CRL-IRnIExwQoKd-_2ARK5-zOYtK-PSWk0uJRMfigIhB333czlaxnDA2A_s59jxX6d-qL3vBfXfFRWHHDhKgcYw2Y9vRXPW8rRaTi4WNJGgOvyCKKcxCDlC33CTyrzFzgmZRY8JtNickwlExKwFAUTcpNSZ3POmBJr8IwuuyOx-mCkIAQzNZKLLxeH48MoMKAocma_kzIg4SY"
          />
          <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight">
            <span class="text-[#007BA7]">Occulta</span><span class="text-[#08203E]">Shield</span>
          </h1>
        </div>
        <p class="text-lg text-gray-600">Securely upload and process your video files.</p>
      </header>

      <main class="w-full max-w-3xl">
        <div class="bg-white p-6 sm:p-10 rounded-2xl shadow-2xl border border-gray-200">

          @if (uploadState() === 'idle') {
            <div
              class="relative flex flex-col items-center justify-center w-full px-6 py-12 border-2 border-dashed rounded-xl text-center cursor-pointer transition-all duration-300 ease-in-out transform hover:-translate-y-1"
              [class.border-[#00A9E0]]="isDragging()"
              [class.bg-blue-50]="isDragging()"
              [class.border-gray-300]="!isDragging()"
              [class.bg-gray-50]="!isDragging()"
              [class.hover:border-[#00A9E0]]="true"
              (dragover)="handleDragOver($event)"
              (dragleave)="handleDragLeave()"
              (drop)="handleDrop($event)"
              (click)="fileInput.click()"
            >
              <div class="absolute -top-5 -right-5 bg-[#00A9E0] rounded-full p-3 shadow-lg">
                <!-- Lucide Upload Icon placeholder -->
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
              </div>

              <h2 class="text-2xl sm:text-3xl font-bold text-[#08203E]">Drop Your Video Here</h2>
              <p class="mt-2 text-gray-500">to start the secure upload process</p>

              <div class="my-6 w-full max-w-xs flex items-center justify-center">
                <hr class="w-full border-gray-300" />
                <span class="px-3 text-sm font-medium text-gray-400 bg-gray-50">OR</span>
                <hr class="w-full border-gray-300" />
              </div>

              <button
                type="button"
                class="mt-2 px-8 py-3 bg-[#00A9E0] text-white font-bold text-lg rounded-full shadow-lg hover:bg-[#007BA7] transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-[#00A9E0]/50"
              >
                Select File from Device
              </button>
              <input
                #fileInput
                accept="video/*"
                class="hidden"
                type="file"
                (change)="onFileSelected($event)"
              />
              <p class="mt-8 text-xs text-gray-400">Max file size: 2GB. Supported formats: MP4, MOV, AVI</p>
            </div>
          } @else {
            <div class="mt-6">
              <div class="flex justify-between items-center mb-2">
                <p class="text-base font-semibold text-gray-700 truncate pr-4">{{ fileName() }}</p>
                <p class="text-xl font-bold text-[#00A9E0]">{{ Math.round(progress()) }}%</p>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-5 overflow-hidden shadow-inner">
                <div
                  class="bg-gradient-to-r from-[#007BA7] to-[#00A9E0] h-5 rounded-full transition-all duration-500 ease-out"
                  [style.width.%]="progress()"
                ></div>
              </div>
              @if (uploadState() === 'complete') {
                <div class="mt-4 text-center text-green-600 font-medium animate-fade-in-up">
                  <div class="flex items-center justify-center gap-2 text-lg">
                    <!-- CheckCircle Icon -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    <span>Upload complete! Processing video...</span>
                  </div>
                </div>
              }
            </div>
          }

        </div>
      </main>
    </div>
  `
})
export class UploadPage {
  isDragging = signal(false);
  uploadState = signal<'idle' | 'uploading' | 'complete'>('idle');
  progress = signal(0);
  fileName = signal('');
  Math = Math;

  constructor(private router: Router) {}

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileSelect(input.files);
    }
  }

  handleFileSelect(files: FileList) {
    if (files.length > 0) {
      const file = files[0];
      this.fileName.set(file.name);
      this.startUpload();
    }
  }

  startUpload() {
    this.uploadState.set('uploading');
    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += Math.random() * 15;
      if (currentProgress >= 100) {
        currentProgress = 100;
        clearInterval(interval);
        this.uploadState.set('complete');
        this.progress.set(100);
        setTimeout(() => {
           this.router.navigate(['/processing']);
        }, 1000);
      } else {
        this.progress.set(currentProgress);
      }
    }, 300);
  }

  handleDragOver(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(true);
  }

  handleDragLeave() {
    this.isDragging.set(false);
  }

  handleDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(false);
    if (e.dataTransfer?.files) {
      this.handleFileSelect(e.dataTransfer.files);
    }
  }
}

