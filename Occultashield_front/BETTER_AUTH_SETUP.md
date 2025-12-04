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

### 3. Iniciar SurrealDB

```bash
# Iniciar SurrealDB en modo desarrollo
surreal start --user root --pass root memory

# O con persistencia en disco
surreal start --user root --pass root file:./data/surreal.db
```

### 4. Importar Esquema de Base de Datos

```bash
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns occultashield --db main \
  server/schema.surql
```

### 5. Ejecutar la Aplicación

```bash
# Desarrollo (Angular CLI)
bun run start

# Producción con SSR
bun run start:ssr
```

## Endpoints de Autenticación

Better-Auth expone automáticamente estos endpoints en `/api/auth/*`:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/sign-up/email` | POST | Registro con email/password |
| `/api/auth/sign-in/email` | POST | Login con email/password |
| `/api/auth/sign-out` | POST | Cerrar sesión |
| `/api/auth/session` | GET | Obtener sesión actual |

### Ejemplo de Registro

```typescript
// Usando el AuthService de Angular
const authService = inject(AuthService);

const success = await authService.register(
  'user@example.com',
  'password123',
  'John Doe'
);
```

### Ejemplo de Login

```typescript
const success = await authService.login(
  'user@example.com',
  'password123'
);

if (success) {
  console.log('Usuario:', authService.user());
}
```

## Uso en Componentes Angular

```typescript
import { Component, inject } from '@angular/core';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-profile',
  template: `
    @if (auth.isAuthenticated()) {
      <p>Bienvenido, {{ auth.userName() }}</p>
      <button (click)="auth.logout()">Cerrar Sesión</button>
    } @else {
      <p>No has iniciado sesión</p>
    }
  `
})
export class ProfileComponent {
  readonly auth = inject(AuthService);
}
```

## Proteger Rutas

Usa el guard de autenticación existente:

```typescript
// app.routes.ts
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/Dashboard'),
    canActivate: [authGuard]
  }
];
```

## Esquema de Base de Datos

El esquema en `server/schema.surql` crea las siguientes tablas:

- **user**: Usuarios registrados
- **session**: Sesiones activas
- **account**: Cuentas vinculadas (providers)
- **verification**: Tokens de verificación

## Adaptador SurrealDB

El adaptador custom en `server/lib/auth.ts` maneja:

- Conversión de RecordId de SurrealDB (`table:id`) a strings simples
- Traducción de operadores WHERE de Better-Auth a SurrealQL
- CRUD completo para todas las tablas de autenticación

## Troubleshooting

### Error: "Failed to connect to SurrealDB"
- Verificar que SurrealDB esté corriendo
- Verificar las variables de entorno `SURREAL_*`

### Error: "Authentication error"
- Verificar que `AUTH_SECRET` esté configurado
- Verificar que el esquema esté importado en la DB

### Error de CORS
- Añadir el origen a `trustedOrigins` en `server/lib/auth.ts`

## Señales Disponibles en AuthService

| Señal | Tipo | Descripción |
|-------|------|-------------|
| `user` | `User \| null` | Usuario autenticado |
| `session` | `Session \| null` | Sesión actual |
| `isLoading` | `boolean` | Estado de carga |
| `error` | `string \| null` | Último error |
| `isAuthenticated` | `boolean` | Si hay sesión activa |
| `userName` | `string \| null` | Nombre del usuario |
| `userEmail` | `string \| null` | Email del usuario |
| `userRole` | `string` | Rol del usuario |
