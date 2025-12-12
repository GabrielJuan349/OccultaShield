import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ViolationCard } from '../../components/ViolationCard/ViolationCard';
import { ModificationType, Violation } from '../../interface/violation-models';

@Component({
  imports: [ViolationCard],
  templateUrl: './ReviewPage.html',
  styleUrl: './ReviewPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewPage implements OnInit {

  private readonly router = inject(Router);

  // Signal que contiene el array de vulneraciones
  protected readonly violations = signal<Violation[]>([]);

  ngOnInit() {
    this.loadViolations();
  }

  // Simulación de carga desde API/JSON
  loadViolations() {
    const mockData: Violation[] = [
      {
        id: 'v1',
        articleTitle: 'GDPR Article 5',
        articleSubtitle: 'Principles relating to processing of personal data',
        description: 'A face has been detected and is considered personal data. Processing it without a lawful basis could violate the core principles of data minimization.',
        fineText: 'Up to €20 million or 4% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      },
      {
        id: 'v2',
        articleTitle: 'GDPR Article 9',
        articleSubtitle: 'Processing of special categories of personal data',
        description: 'A license plate has been detected. This can be linked to an individual and reveal sensitive information, which is prohibited without explicit consent.',
        fineText: 'Up to €20 million or 4% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      },
      {
        id: 'v3',
        articleTitle: 'GDPR Article 6',
        articleSubtitle: 'Lawfulness of processing',
        description: 'An ID card or passport has been detected in the video frame. This document contains highly sensitive personal identifiers that require explicit consent for processing.',
        fineText: 'Up to €20 million or 4% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      },
      {
        id: 'v4',
        articleTitle: 'GDPR Article 17',
        articleSubtitle: 'Right to erasure (right to be forgotten)',
        description: 'A minor (child) has been detected in the footage. Special protections apply to children\'s data, requiring parental consent and heightened security measures.',
        fineText: 'Up to €20 million or 4% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      },
      {
        id: 'v5',
        articleTitle: 'GDPR Article 13',
        articleSubtitle: 'Information to be provided where data is collected',
        description: 'A credit card or bank card has been detected. Financial information is classified as sensitive data and must be protected to prevent identity theft and fraud.',
        fineText: 'Up to €20 million or 4% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      },
      {
        id: 'v6',
        articleTitle: 'GDPR Article 32',
        articleSubtitle: 'Security of processing',
        description: 'A computer screen displaying personal data has been captured. This indirect exposure of third-party information requires appropriate anonymization measures.',
        fineText: 'Up to €10 million or 2% of annual global turnover.',
        imageUrl: 'supervision_humana.png',
        selectedOption: 'no-modify'
      }
    ];
    this.violations.set(mockData);
  }

  // Actualiza el modelo cuando el hijo emite un cambio
  updateViolation(id: string, selection: ModificationType): void {
    this.violations.update(list =>
      list.map(v => v.id === id ? { ...v, selectedOption: selection } : v)
    );
  }

  applyAndContinue(): void {
    console.log('Applying modifications:', this.violations());
    // Navegar a processing indicando que viene de review (para que luego vaya a download)
    this.router.navigate(['/processing'], { queryParams: { from: 'review' } });
  }
}
