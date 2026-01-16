/**
 * Environment Configuration for OccultaShield Auth Server.
 *
 * Loads and exports environment variables for the Better-Auth server,
 * including database connections, SMTP settings, and runtime configuration.
 *
 * Required environment variables:
 * - BETTERAUTH_SECRET: Secret for signing tokens
 * - SURREALDB_USER/PASS: Database credentials
 * - SMTP_USER/PASS: Email service credentials (optional)
 *
 * @example
 * ```typescript
 * import { ENV } from './env';
 * console.log(ENV.PORT); // 4201
 * console.log(ENV.SURREAL_URL); // http://127.0.0.1:8000
 * ```
 */

import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import path from 'path';

// Load .env from current working directory
dotenv.config();

// Note: Logger not imported here to avoid circular dependency (logger imports ENV)

// Detect Bun safely
const globalAny = globalThis as unknown as Record<string, unknown>;
const bunEnv = (globalAny['Bun'] as { env?: Record<string, string> } | undefined)?.env;
const pmIdFromProcess = process.env['pm_id'] ?? process.env['PM_ID'] ?? process.env['PM2_HOME'];
const pmIdFromBun = bunEnv ? (bunEnv['pm_id'] ?? bunEnv['PM_ID'] ?? bunEnv['PM2_HOME']) : undefined;
const PM_ID = pmIdFromBun ?? pmIdFromProcess ?? null;
const isProduction = process.env['Production'] === 'True' ? 'production' : 'development';

export const ENV = {
  NODE_ENV: isProduction,
  PORT: Number(process.env['PORT'] ?? '4201'),
  BASE_URL: process.env['CLIENT_URL'] ?? 'http://localhost:4200',
  AUTH_SECRET: process.env['BETTERAUTH_SECRET'] ?? 'development-secret-change-in-production',
  SURREAL_URL: process.env['SURREALDB_HOST'] ? `http://${process.env['SURREALDB_HOST']}:${process.env['SURREALDB_PORT'] ?? '8000'}` : 'http://127.0.0.1:8000',
  SURREAL_NAMESPACE: process.env['SURREALDB_NAMESPACE'] ?? 'occultashield',
  SURREAL_DB: process.env['SURREALDB_DB'] ?? 'main',
  SURREAL_USER: process.env['SURREALDB_USER'] ?? 'root',
  SURREAL_PASS: process.env['SURREALDB_PASS'] ?? 'root',
  // Email (SMTP)
  SMTP_USER: process.env['SMTP_USER'] ?? '',
  SMTP_PASS: process.env['SMTP_PASS'] ?? '',
  SMTP_FROM: process.env['SMTP_FROM'] ?? '',
  PM_ID,
  RUN_UNDER_PROCESS_MANAGER:
    Boolean(PM_ID) ||
    Boolean(process.env['RUN_UNDER_PROCESS_MANAGER']) ||
    process.env['CI'] === 'true',
} as const;


export type Env = typeof ENV;
