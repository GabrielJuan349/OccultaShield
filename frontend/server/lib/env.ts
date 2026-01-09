import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import path from 'path';

// Cargar .env por defecto (busca en process.cwd())
dotenv.config();

console.log(`⚙️ Variables de entorno cargadas.`);

// Detect Bun safely
const globalAny = globalThis as unknown as Record<string, unknown>;
const bunEnv = (globalAny['Bun'] as { env?: Record<string, string> } | undefined)?.env;
const pmIdFromProcess = process.env['pm_id'] ?? process.env['PM_ID'] ?? process.env['PM2_HOME'];
const pmIdFromBun = bunEnv ? (bunEnv['pm_id'] ?? bunEnv['PM_ID'] ?? bunEnv['PM2_HOME']) : undefined;
const PM_ID = pmIdFromBun ?? pmIdFromProcess ?? null;
const isProduction = process.env['Production'] === 'True' ? 'production' : 'development';

export const ENV = {
  NODE_ENV: isProduction,
  PORT: Number(process.env['PORT'] ?? '4000'),
  BASE_URL: process.env['CLIENT_URL'] ?? 'http://localhost:4000',
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
