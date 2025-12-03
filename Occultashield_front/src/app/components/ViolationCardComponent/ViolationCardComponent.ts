import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

@Component({
  selector: 'violation-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="group grid grid-cols-12 gap-0 overflow-hidden rounded-xl bg-white shadow-lg transition-all duration-300 hover:shadow-cyan-500/20 border border-slate-200">
      <!-- Options Panel -->
      <div class="col-span-12 lg:col-span-3 border-r border-slate-200 p-6 flex flex-col justify-center bg-white">
        <h3 class="text-lg font-bold text-slate-900 mb-4">Modification Options</h3>
        <div class="space-y-3">
          @for (option of options; track option.id) {
            <button
              (click)="selected.set(option.id)"
              class="flex w-full items-center gap-3 rounded-md px-4 py-3 text-left transition-all"
              [class.bg-slate-100]="selected() === option.id"
              [class.font-semibold]="selected() === option.id"
              [class.text-cyan-600]="selected() === option.id"
              [class.ring-2]="selected() === option.id"
              [class.ring-cyan-500]="selected() === option.id"
              [class.bg-slate-50]="selected() !== option.id"
              [class.font-medium]="selected() !== option.id"
              [class.text-slate-700]="selected() !== option.id"
              [class.hover:bg-slate-200]="selected() !== option.id"
            >
              <!-- Icon Logic based on ID -->
              @if (option.id === 'nomodify') { <span class="material-icons-outlined text-lg">radio_button_checked</span> }
              @if (option.id === 'pixelate') { <span class="material-icons-outlined text-lg">grid_on</span> }
              @if (option.id === 'mask') { <span class="material-icons-outlined text-lg">visibility_off</span> }
              @if (option.id === 'blur') { <span class="material-icons-outlined text-lg">blur_on</span> }

              {{ option.label }}
            </button>
          }
        </div>
      </div>

      <!-- Description Panel -->
      <div class="col-span-12 lg:col-span-5 p-6 flex flex-col bg-white">
        <h2 class="text-2xl font-bold tracking-tight text-slate-900">{{ title() }}</h2>
        <p class="text-sm font-semibold uppercase tracking-wider text-cyan-500 mb-4">{{ subtitle() }}</p>
        <p class="text-slate-600 mb-6 flex-grow leading-relaxed">
          {{ description() }}
        </p>
        <div class="mt-auto rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <h4 class="font-bold text-red-800">Potential Fine</h4>
          <p class="text-xl font-black text-red-600">Up to €20 million or 4% of annual global turnover.</p>
        </div>
      </div>

      <!-- Image Panel -->
      <div class="col-span-12 lg:col-span-4 min-h-[250px] lg:min-h-0 bg-slate-50 relative overflow-hidden">
        <img
          alt="Violation context"
          class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          [src]="image()"
        />
        <!-- Overlay simulation based on selection -->
        @if (selected() !== 'nomodify') {
             <div class="absolute inset-0 flex items-center justify-center bg-black/10 backdrop-blur-[2px]">
                 <span class="bg-black/70 text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                     Preview: {{ selected() }}
                 </span>
             </div>
        }
      </div>
    </div>
  `
})
export class ViolationCardComponent {
  title = input('');
  subtitle = input('');
  description = input('');
  image = input('');
  initialOption = input('nomodify');

  selected = signal('nomodify');

  options = [
    { id: 'nomodify', label: 'No Modify' },
    { id: 'pixelate', label: 'Pixelate' },
    { id: 'mask', label: 'Mask' },
    { id: 'blur', label: 'Blur' },
  ];

  ngOnInit() {
    this.selected.set(this.initialOption());
  }
}
