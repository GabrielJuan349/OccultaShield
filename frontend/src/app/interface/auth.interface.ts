/**
 * Authentication-related interfaces and types
 * Used by: AuthService, Guards, Login/Register pages
 */

// === User Types ===

export interface User {
  id: string;
  email: string;
  name: string;
  image?: string;
  role?: string;
  emailVerified: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// === Session Types ===

export interface Session {
  id: string;
  userId: string;
  token: string;
  expiresAt: Date;
}

// === Auth State ===

export interface AuthState {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  error: string | null;
}

// === Usage Types ===

export type UsageType = 'individual' | 'researcher' | 'agency';

// === Auth Request/Response Types ===

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
  usageType?: UsageType;
}
