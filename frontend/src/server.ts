/**
 * OccultaShield Server - Bun.serve() con Better-Auth y Angular SSR
 *
 * Este servidor maneja:
 * 1. Autenticación via Better-Auth (/api/auth/*)
 * 2. Archivos estáticos desde /browser
 * 3. SSR de Angular para el resto de rutas
 */
import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import { join } from 'node:path';
import { getAuth } from '#server/auth';
import { getDb, prepareDataForSurreal } from '#server/db';
import { ENV } from '#server/env';

// Rutas de archivos
const browserDistFolder = join(import.meta.dirname, '../browser');

// Motor de Angular SSR
const angularApp = new AngularNodeAppEngine();

// Aplicación Express (usada también por Angular CLI)
const app = express();

// =========================================================================
// MIDDLEWARE: Parsear JSON para rutas de API
// =========================================================================
app.use(express.json());

// =========================================================================
// RUTAS DE AUTENTICACIÓN (/api/auth/*)
// Better-Auth usa Web Standard Request/Response
// =========================================================================
app.all('/api/auth/*splat', async (req, res) => {
  try {
    // ✅ Esperar a que auth esté listo
    const auth = await getAuth();

    // Convertir Express Request a Web Standard Request
    const protocol = req.protocol;
    const host = req.get('host') ?? 'localhost';
    const url = `${protocol}://${host}${req.originalUrl}`;

    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value) {
        headers.set(key, Array.isArray(value) ? value.join(', ') : value);
      }
    }

    const webRequest = new Request(url, {
      method: req.method,
      headers,
      body: ['GET', 'HEAD'].includes(req.method)
        ? undefined
        : JSON.stringify(req.body),
    });

    // Better-Auth maneja la petición
    const response = await auth.handler(webRequest);

    // Convertir Web Response a Express Response
    res.status(response.status);

    response.headers.forEach((value, key) => {
      res.setHeader(key, value);
    });

    const body = await response.text();
    res.send(body);
  } catch (error) {
    console.error('Auth Error:', error);
    res.status(500).json({ error: 'Authentication error' });
  }
});

// =========================================================================
// RUTAS DE ADMINISTRACIÓN (/api/admin/*)
// Importado desde admin.ts - incluye approval workflow, settings, audit log
// =========================================================================
import { adminRouter, checkUserApproval } from '#server/admin';

app.use('/api/admin', adminRouter);

// =========================================================================
// RUTAS DE API GENERAL
// =========================================================================

// POST /api/upload/log - Registrar actividad de subida
app.post('/api/upload/log', async (req, res) => {
  try {
    const auth = await getAuth(); // ✅ Esperar a que auth esté listo

    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    }

    const session = await auth.api.getSession({ headers });
    if (!session) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }

    const { fileName, fileSize, action, status } = req.body;
    const db = await getDb();

    // prepareDataForSurreal convierte userId a record<user> automáticamente
    const logData = prepareDataForSurreal({
      userId: session.user.id,
      action: action || 'upload',
      fileName: fileName || 'unknown',
      fileSize: fileSize || 0,
      status: status || 'success',
      metadata: {}
    });

    await db.create('processing_log', logData);

    res.json({ success: true });
  } catch (error) {
    console.error('Log Error:', error);
    res.status(500).json({ error: 'Failed to log activity' });
  }
});

// =========================================================================
// ARCHIVOS ESTÁTICOS
// =========================================================================
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  })
);

// =========================================================================
// ANGULAR SSR (Todas las demás rutas)
// =========================================================================
app.use((req, res, next) => {
  angularApp
    .handle(req)
    .then((response) =>
      response ? writeResponseToNodeResponse(response, res) : next()
    )
    .catch(next);
});

// ============================================================================
// INICIALIZACIÓN DEL SERVIDOR
// ============================================================================
if (isMainModule(import.meta.url) || ENV.RUN_UNDER_PROCESS_MANAGER) {
  const PORT = Number(ENV.PORT ?? 4000);
  console.log(`🚀 OccultaShield Server starting on port ${PORT}`);

  // Inicializar conexión a SurrealDB y Better-Auth
  Promise.all([getDb(), getAuth()])
    .then(() => {
      app.listen(PORT, () => {
        console.log(`✅ OccultaShield Server running at http://localhost:${PORT}`);
        console.log(`   Auth endpoints: http://localhost:${PORT}/api/auth/*`);
        console.log(`   Angular SSR: Enabled`);
      });
    })
    .catch((error) => {
      console.error('❌ Failed to initialize server:', error);
      // Iniciar servidor sin DB para desarrollo
      app.listen(PORT, () => {
        console.log(`⚠️  Server running with errors at http://localhost:${PORT}`);
        console.log(`   Start SurrealDB and restart the server for full functionality`);
      });
    });
}

/**
 * Request handler usado por Angular CLI (dev-server y build)
 */
export const reqHandler = createNodeRequestHandler(app);
