import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet], // Importa aquí los módulos que necesites
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'OccultaShield';

}
