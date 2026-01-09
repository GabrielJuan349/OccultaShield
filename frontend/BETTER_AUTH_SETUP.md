# OccultaShield - Better-Auth Setup Guide

## Stack Técnico

- **Runtime**: Bun / Node.js
- **Framework**: Angular v21 con SSR
- **Base de Datos**: SurrealDB
- **Autenticación**: Better-Auth

## Estructura de Archivos

```
├── server/
│   ├── lib/
│   │   ├── db.ts          # Conexión a SurrealDB
│   │   └── auth.ts        # Configuración de Better-Auth + Adapter
│   ├── schema.surql       # Esquema de base de datos
│   └── tsconfig.json      # Config TypeScript para servidor
├── src/
│   ├── app/
│   │   ├── lib/
│   │   │   └── auth-client.ts   # Cliente de auth para Angular
│   │   └── services/
│   │       └── auth.service.ts  # Servicio Angular de autenticación
│   └── server.ts          # Servidor Express con SSR
└── .env.example           # Variables de entorno de ejemplo
```

## Configuración Inicial

### 1. Instalar Dependencias

```bash
bun install
```

### 2. Configurar Variables de Entorno

Copiar `.env.example` a `.env` y configurar:

```bash
cp .env.example .env
```

Variables importantes:
- `SURREAL_URL`: URL de SurrealDB (default: `http://127.0.0.1:8000`)
- `SURREAL_NAMESPACE`: Namespace de la DB (default: `occultashield`)
- `SURREAL_DATABASE`: Nombre de la DB (default: `main`)
- `AUTH_SECRET`: **IMPORTANTE** - Cambiar por un secreto seguro de 32+ caracteres
- `SMTP_USER`: Email para notificaciones (ej. Gmail).
- `SMTP_PASS`: Contraseña de aplicación de Google.

### 3. Iniciar SurrealDB

```bash
# Iniciar SurrealDB en modo desarrollo
surreal start --user root --pass root memory
```

### 4. Importar Esquema de Base de Datos

```bash
# El esquema incluye las nuevas tablas app_settings y audit_log
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns occultashield --db main \
  db_files/schema.surql
```

### 5. Configurar el Primer Administrador

El sistema de roles está integrado. Para convertir un usuario en admin manualmente:
```sql
UPDATE user:id SET role = 'admin', isApproved = true;
```

---

## 🛡️ Admin API & SSR

A diferencia del resto de la app, la lógica de administración corre en el servidor **Node.js (SSR Express)** para mayor seguridad y acceso directo a SurrealDB.

### Endpoints de Administración (`/api/admin/*`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/admin/stats` | GET | Estadísticas del dashboard |
| `/api/admin/users` | GET | Lista de todos los usuarios |
| `/api/admin/users/:id/approve` | PATCH | Aprobar usuario + Envío de email |
| `/api/admin/users/:id/reject` | PATCH | Rechazar usuario + Envío de email |
| `/api/admin/settings` | GET/PUT | Configuración (Beta Cerrada) |

---

## 🚪 Flujo de Aprobación (Closed Beta)

1.  **Registro**: Al registrarse, el usuario recibe automáticamente un email de "Solicitud Recibida". Su estado inicial es `isApproved: false`.
2.  **Middlewares**: 
    *   `requireAdmin`: Protege las rutas `/admin`.
    *   `checkUserApproval`: Bloquea las rutas de la app si el usuario no está aprobado y el `closedBetaMode` está activo.
3.  **Emails**: Se utiliza **Nodemailer** para enviar plantillas HTML profesionales con el estado de la cuenta.

---

## Esquema de Base de Datos (Extendido)

Tablas principales de autenticación y control:

- **user**: Incluye `role`, `isApproved` (boolean) y `usageType`.
- **session**: Sesiones activas.
- **app_settings**: Configuración del sistema (ej: `closedBetaMode`).
- **audit_log**: Registro histórico de acciones administrativas.

---

## Señales Disponibles en AuthService

| Señal | Tipo | Descripción |
|-------|------|-------------|
| `user` | `User \| null` | Usuario autenticado |
| `isAuthenticated` | `boolean` | Si hay sesión activa |
| `userRole` | `string` | Rol actual (`user` o `admin`) |
| `isApproved` | `boolean` | Estado de aprobación del usuario |
