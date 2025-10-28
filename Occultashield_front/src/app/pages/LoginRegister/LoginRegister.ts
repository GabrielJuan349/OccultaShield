import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'login-register',
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './LoginRegister.html',
  styleUrl: './LoginRegister.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginRegister {
  protected logo = 'halcon_logo_2.png'
  protected isRegisterMode = signal<boolean>(false);
  authForm: FormGroup;
  protected errorMessage = signal<string | null>(null);
  protected loading = signal<boolean>(false);
  private returnUrl: string = '/upload'; // URL por defecto después del login
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private authService = inject(AuthService);
  private fb = inject(FormBuilder);

  constructor() {
    // Verificar si ya está autenticado
    if (this.authService.isAuthenticated()) {
      this.router.navigate([this.returnUrl]);
    }

    // Obtener la URL de retorno si existe
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/upload';

    this.authForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['']
    });

    // Actualiza los validadores para confirmPassword cuando cambia el modo
    this.authForm.get('confirmPassword')?.setValidators(
      this.isRegisterMode() ? [Validators.required, this.passwordMatchValidator.bind(this)] : null
    );
    this.authForm.get('confirmPassword')?.updateValueAndValidity();
  }

  // Alterna entre los modos de login y registro
  toggleMode(): void {
    this.isRegisterMode.update(value => !value);
    // Vaciamos el formulario al cambiar de modo para evitar datos residuales
    this.authForm.reset();
    this.errorMessage.set(null);

    // Actualiza los validadores de confirmPassword
    this.authForm.get('confirmPassword')?.setValidators(
      this.isRegisterMode() ? [Validators.required, this.passwordMatchValidator.bind(this)] : null
    );
    this.authForm.get('confirmPassword')?.updateValueAndValidity();
  }

  // Validador personalizado para confirmar que las contraseñas coinciden
  passwordMatchValidator(control: any): { [key: string]: boolean } | null {
    const password = this.authForm?.get('password')?.value;
    const confirmPassword = control.value;
    if (this.isRegisterMode() && password && confirmPassword && password !== confirmPassword) {
      return { 'passwordMismatch': true };
    }
    return null;
  }

  // Maneja el envío del formulario (login o registro)
  onSubmit(): void {
    this.errorMessage.set(null);
    if (this.authForm.invalid) {
      this.authForm.markAllAsTouched(); // Marca todos los campos como tocados para mostrar errores
      return;
    }

    const { email, password } = this.authForm.value;
    this.loading.set(true);

    // --- LÓGICA DE AUTENTICACIÓN / REGISTRO ---
    // En un proyecto real, aquí harías una llamada HTTP a tu backend
    // Por ahora, simulamos la respuesta del backend

    if (this.isRegisterMode()) {
      // Simula el registro
      console.log('Intentando registrar usuario:', { email, password });
      setTimeout(() => {
        this.loading.set(false);
        if (email === 'test@example.com') {
          this.errorMessage.set('Este email ya está registrado.');
        } else {
          alert('¡Registro exitoso! Ahora puedes iniciar sesión.');
          this.toggleMode();
        }
      }, 1500);
    } else {
      // Simula el login
      console.log('Intentando iniciar sesión:', { email, password });

      // SIMULACIÓN: En producción esto vendría del backend
      setTimeout(() => {
        this.loading.set(false);

        // Credenciales de prueba
        if (email === 'user@occultashield.com' && password === 'OccultaShield2024') {
          // Token JWT de ejemplo (generado para pruebas)
          // En producción, este token vendría del backend
          const mockJWT = this.generateMockJWT(email);

          // Guardar el token usando el AuthService
          this.authService.setToken(mockJWT);

          console.log('✅ Login exitoso - Token guardado en localStorage');

          // Redirigir a la URL de retorno o a /upload por defecto
          this.router.navigate([this.returnUrl]);
        } else {
          this.errorMessage.set('Email o contraseña incorrectos.');
        }
      }, 1500);
    }
  }

  /**
   * Genera un JWT mock para pruebas
   * En producción, el token vendrá del backend
   */
  private generateMockJWT(email: string): string {
    const header = {
      alg: 'HS256',
      typ: 'JWT'
    };

    const payload = {
      email: email,
      sub: '12345',
      name: 'Usuario OccultaShield',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // Expira en 24 horas
    };

    // Codificar en base64 (simulación simplificada)
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    const signature = 'mock-signature-for-testing';

    return `${encodedHeader}.${encodedPayload}.${signature}`;
  }

  // Helpers para acceder fácilmente a los controles del formulario en la plantilla
  get email() {
    return this.authForm.get('email');
  }
  get password() {
    return this.authForm.get('password');
  }
  get confirmPassword() {
    return this.authForm.get('confirmPassword');
  }
}
