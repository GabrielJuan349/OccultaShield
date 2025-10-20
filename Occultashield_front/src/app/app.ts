import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [CommonModule, RouterOutlet], // Importa aquí los módulos que necesites
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'OccultaShield';
  protected today = new Date();
  protected complianceImage = 'supervision_humana.png';

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
}
