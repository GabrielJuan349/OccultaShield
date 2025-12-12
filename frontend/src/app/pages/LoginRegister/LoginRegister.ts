import { Component, signal, effect, ChangeDetectionStrategy, inject } from '@angular/core';
import { NgOptimizedImage } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
// Importamos la API real de Signal Forms (Experimental/v21)
import { form, Field, required, email, minLength, submit, validate } from '@angular/forms/signals';
import { AuthService } from '../../services/auth.service';

@Component({
  imports: [RouterLink, Field],
  templateUrl: './LoginRegister.html',
  styleUrls: ['./LoginRegister.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginRegister {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  // Estado de UI local (no del formulario)
  protected showPassword = signal(false);
  protected isLoading = signal(false);
  protected currentView = signal<'login' | 'register'>('login');

  // 1. EL MODELO (Source of Truth)
  // En Signal Forms, los datos viven en un signal puro, independientes del formulario.
  protected loginCredentials = signal({
    email: '',
    password: '',
    rememberMe: false
  });
  protected registerCredentials = signal({
    nameSurname: '',
    email: '',
    password: '',
    confirmPassword: '',
    privacyCheck: false,
  });

  // 2. EL FORMULARIO
  // La función form() toma el signal y crea un "FieldTree" (árbol de campos)
  // El segundo argumento es donde aplicamos las validaciones.
  protected loginForm = form(this.loginCredentials, (f) => {
    // f representa los campos del formulario
    required(f.email, { message: 'Email is required' });
    email(f.email, { message: 'Invalid email format' });

    required(f.password);
    minLength(f.password, 8, { message: 'Password must be at least 8 chars' });
  });

  protected registerForm = form(this.registerCredentials, (f) => {
    required(f.nameSurname, { message: 'Name and surname are required' });
    required(f.email, { message: 'Email is required' });
    email(f.email, { message: 'Invalid email format' });

    required(f.password);
    minLength(f.password, 8, { message: 'Password must be at least 8 chars' });

    required(f.confirmPassword);
    validate(f.confirmPassword, ({ value, valueOf }) => {
      const password = valueOf(f.password);
      if (value() !== password) {
        return {
          kind: 'mismatch',
          message: 'Passwords do not match'
        };
      }
      return null;
});
    required(f.privacyCheck, { message: 'You must accept the privacy policy' });
  });


  constructor() {
    // Podemos reaccionar a cambios en el MODELO directamente
    effect(() => {
      console.log('Model changed:', this.loginCredentials());
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
      const payload = this.loginCredentials();
      console.log('Authenticating:', payload);

      await new Promise(r => setTimeout(r, 1500));
      this.isLoading.set(false);
    });
  }
}
