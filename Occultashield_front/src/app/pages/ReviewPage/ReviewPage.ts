import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Router } from '@angular/router';
import { ViolationCardComponent } from '../../components/ViolationCardComponent/ViolationCardComponent';
import { CommonModule } from '@angular/common';

// @Component({
//   selector: 'app-review-page',
//   imports: [],
//   template: `<p>ReviewPage works!</p>`,
//   styleUrl: './ReviewPage.css',
//   changeDetection: ChangeDetectionStrategy.OnPush,
// })
@Component({
  selector: 'app-review',
  standalone: true,
  imports: [CommonModule, ViolationCardComponent],
  template: `
    <div class="min-h-screen w-full bg-[#f0f4f8] font-roboto text-slate-800">
      <div class="w-full bg-gradient-to-b from-slate-200 to-[#f0f4f8] px-4 py-8 sm:px-6 lg:px-8">
        <header class="mx-auto max-w-7xl mb-12 text-center">
          <div class="inline-flex items-center gap-4 mb-4">
            <!-- Shield Alert Icon -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-cyan-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <h1 class="text-4xl font-black tracking-tight text-slate-900 sm:text-5xl">
              OccultaShield Privacy Review
            </h1>
          </div>
          <p class="mt-2 text-lg text-slate-600 max-w-3xl mx-auto">
            Our analysis detected potential GDPR violations in your video. Please review each item and choose a modification to ensure compliance.
          </p>
        </header>

        <main class="mx-auto max-w-7xl space-y-8 pb-12">
          <!-- Card 1: Face Detection -->
          <violation-card
            title="GDPR Article 5"
            subtitle="Principles relating to processing of personal data"
            description="A face has been detected and is considered personal data. Processing it without a lawful basis could violate the core principles of data minimization and purpose limitation."
            image="https://lh3.googleusercontent.com/aida-public/AB6AXuDwV8_DiYW7Z3UfgCFMt69MpQHAK_KaKczUC91KgdhcuM_Wf6HRSP3W-8QM8qd2TRfLzSxeI6KYr9CbW2ddpEPt7oBvq8eD8u1RfhstlzmCbuELY9STM83LkWtsup16rR-HuEi1da7M7dcyLnGbgS4sKh1cOR6cYSBzlSp2oSQUjfbcA8YTqi3DEfAy7QJfCa9fcLVtoLzOUBiJ83aQVfG4AMGHz3httteFzPe44-vZs1eSqFH_oUJtZ0wXTxFqb0qSa8Dv3MPC8xo"
            initialOption="nomodify"
          ></violation-card>

          <!-- Card 2: License Plate -->
          <violation-card
            title="GDPR Article 9"
            subtitle="Processing of special categories of personal data"
            description="A license plate has been detected. This can be linked to an individual and reveal sensitive information, which is prohibited without explicit consent or specific legal exemptions."
            image="https://lh3.googleusercontent.com/aida-public/AB6AXuCaxsSYKik6zUf1YqrggdmmTYJcckpLh1Cyja1cq7uGD8O3zJbGYM_2fPW3AcHs0lwJYpQAYmGi2fSYXVN_xWS1jqmC0N0kDvmfuHAT-467fMOKXLq38Qpiptn9j2yR7dUvlFRFVhxaqiyVi77R1chUEqwEpd1bTwL2sfsFHhw5DbNkzwMv1CDkXWPCkqiM01ESFn9Btsywu1KgX99kmHfGwjbDNmtop-KR3l52A4FPA3HBajOcJVmRdRaVhKab1Lqm9WWJqaBt0-Y"
            initialOption="blur"
          ></violation-card>

          <div class="pt-8 flex justify-end">
            <button
              (click)="navigateToResult()"
              class="rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-8 py-4 text-base font-bold text-white shadow-lg transition-transform duration-300 hover:scale-105 hover:shadow-cyan-500/40"
            >
              Apply Modifications & Continue
            </button>
          </div>
        </main>
      </div>
    </div>
  `
})
export class ReviewPage {
  constructor(private router: Router) {}

  navigateToResult() {
    this.router.navigate(['/result']);
  }
}
