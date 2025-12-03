import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Field, form } from '@angular/forms/signals';

@Component({
  selector: 'app-login-register',
  standalone: true,
  imports: [Field],
  templateUrl: './LoginRegister.html',
  styleUrl: './LoginRegister.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginRegister {
  private router = inject(Router);

  protected formState = signal({
    email: '',
    password: '',
    rememberMe: false,
  });

  protected loginForm = form(this.formState);

  handleSignIn(): void {
    const values = this.formState();
    if (values.email && values.password) {
      // Aquí iría la lógica de autenticación real
      console.log('Form value:', values);
      this.router.navigate(['/upload']);
    } else {
      // Manejo de errores o validación manual si es necesario
      console.log('Form invalid');
    }
  }
}
