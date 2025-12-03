import { Component, OnInit, signal, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';

// @Component({
//   selector: 'app-processing-page',
//   imports: [],
//   template: `<p>ProcessingPage works!</p>`,
//   styleUrl: './ProcessingPage.css',
//   changeDetection: ChangeDetectionStrategy.OnPush,
// })
// export class ProcessingPage { }

@Component({
  selector: 'app-processing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="relative flex h-screen w-screen flex-col items-center justify-center overflow-hidden bg-[#02042B] font-sans text-white">
      <!-- Background Glows -->
      <div class="absolute -top-1/4 left-0 h-1/2 w-1/2 rounded-full bg-[#0052D4]/30 blur-3xl filter"></div>
      <div class="absolute -bottom-1/4 right-0 h-1/2 w-1/2 rounded-full bg-[#00C7FF]/30 blur-3xl filter"></div>

      <div class="z-10 flex w-full max-w-lg flex-col items-center text-center">
        <!-- Animated Loader -->
        <div class="relative mb-8 flex h-48 w-48 items-center justify-center">
          <div class="absolute inset-0 rounded-full border-4 border-t-4 border-[#00C7FF] border-t-transparent opacity-50 animate-spin-slow"></div>
          <div class="absolute inset-4 rounded-full border-4 border-b-4 border-[#0052D4] border-b-transparent opacity-50 animate-spin-slow" style="animation-direction: reverse; animation-duration: 2s;"></div>

          <div class="flex h-36 w-36 items-center justify-center rounded-full bg-[#02042B]/50 backdrop-blur-sm animate-pulse-glow border border-[#0052D4]/30">
            <img
              alt="OccultaShield falcon logo"
              class="h-20 w-auto"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCdknthLYUAndkZ7Ch0xsG8yYUVjs1AStOGt1k959PYsFqDLuYfsDKinmiakHLVKCU2_Zek2JwEYwBvVo4MSc1z7lV8G9_U5L_v4UyHV-X-qoHmmNGRYnjtttprJTzpVdtskHqt3g0sSeR8nkmEViwsJQtsY7c90Hqm7mb1kfwg0S9ftZvgTmHdSCHh_nB6aMCs7RVQIggf7BqiuXUyTd3E89VLdAhzdjwmMENB9EFoXQD-WWvkAQZMWWejVftEBzceg4vJlVU65rI"
            />
          </div>
        </div>

        <h1 class="mb-6 text-4xl font-black uppercase tracking-widest text-white sm:text-5xl font-display">
          <span class="bg-gradient-to-r from-[#00C7FF] to-white bg-clip-text text-transparent">Enhancing</span> Privacy
        </h1>

        <div class="w-full px-8">
          <div class="relative h-3 w-full rounded-full bg-slate-700/50 overflow-hidden">
            <div
              class="h-3 rounded-full bg-gradient-to-r from-[#0052D4] to-[#00C7FF] transition-all duration-100 ease-linear"
              [style.width.%]="progress()"
            ></div>
          </div>
          <div class="mt-3 flex justify-between text-sm font-medium text-slate-300">
            <span>{{ Math.round(progress()) }}%</span>
            <span>Est. time remaining: {{ secondsRemaining() }} seconds</span>
          </div>
        </div>
      </div>
    </div>
  `
})
export class ProcessingPage implements OnInit, OnDestroy {
  secondsRemaining = signal(42);
  progress = signal(0);
  Math = Math;
  private timer: any;
  private redirectTimer: any;

  constructor(private router: Router) {}

  ngOnInit() {
    this.timer = setInterval(() => {
      this.secondsRemaining.update(prev => Math.max(0, prev - 1));
      this.progress.update(prev => Math.min(100, prev + 2.5));
    }, 100);

    this.redirectTimer = setTimeout(() => {
      this.router.navigate(['/review']);
    }, 4500);
  }

  ngOnDestroy() {
    clearInterval(this.timer);
    clearTimeout(this.redirectTimer);
  }
}

