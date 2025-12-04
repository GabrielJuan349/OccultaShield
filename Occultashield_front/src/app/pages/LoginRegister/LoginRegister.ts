import { Component, signal, effect, ChangeDetectionStrategy } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { RouterLink } from '@angular/router';
// Importamos la API real de Signal Forms (Experimental/v21)
import { form, Field, required, email, minLength, submit } from '@angular/forms/signals';

@Component({
  selector: 'app-login',
  imports: [RouterLink, NgOptimizedImage, Field],
  templateUrl: './LoginRegister.html',
  styleUrls: ['./LoginRegister.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginRegister {

  // 1. EL MODELO (Source of Truth)
  // En Signal Forms, los datos viven en un signal puro, independientes del formulario.
  protected credentials = signal({
    email: '',
    password: '',
    rememberMe: false
  });

  // 2. EL FORMULARIO
  // La función form() toma el signal y crea un "FieldTree" (árbol de campos)
  // El segundo argumento es donde aplicamos las validaciones.
  protected loginForm = form(this.credentials, (f) => {
    // f representa los campos del formulario
    required(f.email, { message: 'Email is required' });
    email(f.email, { message: 'Invalid email format' });

    required(f.password);
    minLength(f.password, 8, { message: 'Password must be at least 8 chars' });
  });

  // Estado de UI local (no del formulario)
  protected showPassword = signal(false);
  protected isLoading = signal(false);

  constructor() {
    // Podemos reaccionar a cambios en el MODELO directamente
    effect(() => {
      console.log('Model changed:', this.credentials());
    });
  }

  togglePasswordVisibility() {
    this.showPassword.update(v => !v);
  }

  onSubmit(event: Event) {
    event.preventDefault();
    // La función submit() valida automáticamente y marca campos como touched
    // Solo ejecuta el callback si el formulario es válido
    submit(this.loginForm, async () => {
      this.isLoading.set(true);

      // Leemos directamente nuestro signal 'credentials()', que ya está sincronizado.
      const payload = this.credentials();
      console.log('Authenticating:', payload);

      await new Promise(r => setTimeout(r, 1500));
      this.isLoading.set(false);
    });
  }
}
