/**
 * Admin panel interfaces and types
 * Used by: AdminService, Admin pages (Dashboard, Users, Settings, AuditLog)
 */

import type { UsageType } from './auth.interface';

// === Admin User (extended version for admin panel) ===

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  isApproved: boolean;
  usageType: UsageType;
  createdAt: string;
  image?: string;
}

// === Admin Statistics ===

export interface AdminStats {
  total_users: number;
  pending_users: number;
  approved_users: number;
  total_videos: number;
  total_violations: number;
  active_sessions: number;
  recentActivity: RecentActivityItem[];
}

export interface RecentActivityItem {
  id: string;
  action: string;
  fileName?: string;
  status: string;
  createdAt: string;
}

// === App Settings ===

export interface AppSettings {
  closedBetaMode: boolean;
}

// === Audit Log ===

export interface AuditLogEntry {
  id: string;
  userId: string;
  action: AuditAction;
  targetId?: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export type AuditAction =
  | 'user_approved'
  | 'user_rejected'
  | 'role_changed'
  | 'settings_changed'
  | 'video_processed';

// === User Role ===

export type UserRole = 'user' | 'admin';
