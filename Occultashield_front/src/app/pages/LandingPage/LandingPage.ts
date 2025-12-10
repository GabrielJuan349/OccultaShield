import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule, NgOptimizedImage } from '@angular/common';


@Component({
  selector: 'landing-page',
  imports: [CommonModule, NgOptimizedImage],
  templateUrl: './LandingPage.html',
  styleUrl: './LandingPage.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingPage {

  protected today = new Date();
  protected complianceImage = 'supervision_humana.png';

  // Signal para el estado del menú móvil
  protected mobileMenuOpen = signal<boolean>(false);

  // Array para las características, basado en tu tesis
  features = [
    {
      icon: '🔎',
      title: '1. Detección por IA (YOLO)',
      description: 'Nuestro sistema utiliza modelos YOLO de última generación para escanear cada fotograma y localizar con precisión datos personales como rostros y matrículas.'
    },
    {
      icon: '✅',
      title: '2. Validación Inteligente (MVP)',
      description: 'El núcleo de nuestro cumplimiento legal. La IA no decide por ti; te presenta las detecciones para que tú apliques las reglas y tengas la supervisión final.'
    },
    {
      icon: '🛡️',
      title: '3. Edición Precisa (CV)',
      description: 'Algoritmos de Computer Vision aplican una anonimización (blur o pixelado) selectiva y persistente, solo en las coordenadas validadas por el usuario.'
    }
  ];

  toggleMobileMenu(): void {
    this.mobileMenuOpen.update(value => !value);
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }
 }
