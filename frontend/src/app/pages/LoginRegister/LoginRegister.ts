import { Component, signal, computed, ChangeDetectionStrategy, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { form, Field, required, email, minLength, submit, validate } from '@angular/forms/signals';
import { AuthService } from '#services/auth.service';

@Component({
  imports: [RouterLink, Field],
  templateUrl: './LoginRegister.html',
  styleUrls: ['./LoginRegister.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginRegister {
  protected readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  // UI State
  protected showPassword = signal(false);
  protected isLoading = signal(false);
  protected currentView = signal<'login' | 'register'>('login');
  protected registrationPending = signal(false);

  // Login Model
  protected loginCredentials = signal({
    email: '',
    password: '',
    rememberMe: false
  });

  // Register Model (with usageType)
  protected registerCredentials = signal({
    nameSurname: '',
    email: '',
    password: '',
    confirmPassword: '',
    usageType: 'individual' as 'individual' | 'researcher' | 'agency',
    privacyCheck: false,
  });

  // Password Strength Meter (computed signal)
  protected passwordStrength = computed(() => {
    const password = this.registerCredentials().password;
    if (!password) return { score: 0, label: '', color: '' };

    let score = 0;

    // Length checks
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    if (password.length >= 16) score += 1;

    // Character variety
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;

    // Map score to label
    if (score <= 2) return { score: 1, label: 'Débil', color: '#ef4444' };
    if (score <= 4) return { score: 2, label: 'Media', color: '#f59e0b' };
    if (score <= 5) return { score: 3, label: 'Buena', color: '#22c55e' };
    return { score: 4, label: 'Excelente', color: '#10b981' };
  });

  // Login Form
  protected loginForm = form(this.loginCredentials, (f) => {
    required(f.email, { message: 'Email is required' });
    email(f.email, { message: 'Invalid email format' });
    required(f.password);
    minLength(f.password, 8, { message: 'Password must be at least 8 chars' });
  });

  // Register Form
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
        return { kind: 'mismatch', message: 'Passwords do not match' };
      }
      return null;
    });
    required(f.privacyCheck, { message: 'You must accept the privacy policy' });
  });

  togglePasswordVisibility() {
    this.showPassword.update(v => !v);
  }

  toggleAuthMode() {
    this.currentView.update(v => v === 'login' ? 'register' : 'login');
    this.registrationPending.set(false);
  }

  setUsageType(type: 'individual' | 'researcher' | 'agency') {
    this.registerCredentials.update(c => ({ ...c, usageType: type }));
  }

  onLoginSubmit(event: Event) {
    event.preventDefault();
    submit(this.loginForm, async () => {
      this.isLoading.set(true);
      const { email, password } = this.loginCredentials();
      const success = await this.authService.login(email, password);
      if (success) {
        this.router.navigate(['/upload']);
      } else {
        console.error('Login failed:', this.authService.error());
      }
      this.isLoading.set(false);
    });
  }

  onRegisterSubmit(event: Event) {
    event.preventDefault();
    submit(this.registerForm, async () => {
      this.isLoading.set(true);
      const { nameSurname, email, password } = this.registerCredentials();
      const success = await this.authService.register(email, password, nameSurname);

      if (success) {
        // In closed beta mode, show pending approval message
        // The backend will set isApproved = false by default
        this.registrationPending.set(true);
      } else {
        console.error('Register failed:', this.authService.error());
      }
      this.isLoading.set(false);
    });
  }
}
