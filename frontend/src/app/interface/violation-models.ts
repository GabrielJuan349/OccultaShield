export type ModificationType = 'no-modify' | 'pixelate' | 'mask' | 'blur';

export interface Violation {
  id: string;
  articleTitle: string;    // Ej: GDPR Article 5
  articleSubtitle: string; // Ej: PRINCIPLES RELATING...
  description: string;
  fineText: string;
  imageUrl: string;
  selectedOption: ModificationType; // Estado mutable
}
