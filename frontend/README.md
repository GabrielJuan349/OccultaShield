<div align="center">

# 🌐 OccultaShield Frontend

### Interfaz SSR de Alta Fidelidad y Panel de Administración (Angular v21)

[![Angular](https://img.shields.io/badge/Angular-v21.0-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.io/)
[![Bun](https://img.shields.io/badge/Bun-1.3.1-000000?style=for-the-badge&logo=bun&logoColor=white)](https://bun.sh/)
[![Better-Auth](https://img.shields.io/badge/Auth-Better--Auth-blueviolet?style=for-the-badge)](https://better-auth.com)
[![Zoneless](https://img.shields.io/badge/Architecture-Zoneless-blue?style=for-the-badge)](https://angular.dev)

**Experiencia de usuario instantánea y segura con Server-Side Rendering (SSR), Signals y gestión administrativa avanzada.**

</div>

---

## 🚀 Visión General

El frontend de OccultaShield trasciende el reproductor de video convencional. Es una **Suite de Cumplimiento Normativo (Compliance Suite)** completa. Construido con la última tecnología disponible en 2025 (Angular v21), ofrece una experiencia fluida, reactiva y segura para la toma de decisiones críticas sobre privacidad.

Su arquitectura **Zoneless** garantiza que incluso con cientos de detecciones en pantalla (Bounding Boxes), la interfaz se mantenga a 60 FPS sin bloqueos.

---

## ✨ Características Técnicas Avanzadas

### 1. Arquitectura "Bleeding Edge" (Zoneless + SSR)
*   **Adiós Zone.js**: Hemos eliminado la dependencia de `zone.js` para la detección de cambios. Ahora, la UI reacciona a cambios de estado atómicos mediante **Signals**, reduciendo drásticamente el uso de CPU y memoria.
*   **Server-Side Rendering (SSR)**: Gracias a **Bun** y el adaptador de Express, la aplicación se renderiza en el servidor antes de llegar al cliente, asegurando tiempos de carga (`LCP`) casi instantáneos.
*   **Hydration no destructiva**: Angular rehidrata el estado del cliente sin parpadeos, permitiendo interacción inmediata.

### 2. Panel de Administración y Seguridad (`/admin`)
*   **Role-Based Access Control (RBAC)**: Sistema de permisos granular.
    *   *Admins*: Aprueban cuentas, ven métricas globales, acceden a registros de auditoría.
    *   *Users*: Solo ven sus propios videos.
*   **Sistema "Closed Beta"**: Flujo de registro con aprobación manual. Los nuevos usuarios quedan en estado `Pending` hasta validación.
*   **Audit Log Inmutable**: Cada acción administrativa (aprobar usuario, cambiar configuración) queda registrada y firmada en el sistema.

### 3. Experiencia de Revisión (Review Room)
*   **SSE Streaming Real-time**: Conexión continua con el backend para mostrar el progreso de detección frame a frame.
*   **Reproductor Seguro**:
    *   **Anti-Screenshot**: La UI detecta atajos de teclado de captura y ofusca el contenido sensible.
    *   **Marcas de Agua**: Superposición dinámica con el ID del usuario visualizador para trazar filtraciones.
    *   **Navegación por Infracciones**: Timeline interactivo que marca los momentos exactos de violación del RGPD.

---

## 🏃 Guía de Desarrollo

### 1. Requisitos
*   [Bun](https://bun.sh) v1.1+ instalado globalmente.
*   Node.js v20+ (opcional, Bun lo reemplaza en la mayoría de tareas).
*   Backend de OccultaShield corriendo en el puerto `8980`.

### 2. Instalación de Dependencias
Utilizamos Bun para una instalación ultrarrápida (10x más rápido que npm).
```bash
cd frontend
bun install
```

### 3. Configuración del Entorno (`.env`)
```bash
cp .env.example .env
nano .env
```
**Variables Críticas:**
*   `API_URL`: URL del backend (ej: `http://localhost:8980/api/v1`).
*   `BETTERAUTH_SECRET`: Clave secreta para firmar sesiones.
*   `SMTP_*`: Configuración para el envío de correos transaccionales (invitaciones, aprobaciones).

### 4. Ejecución (Modo Desarrollo)
Arranca el servidor de desarrollo con Hot Module Replacement (HMR).
```bash
bun run dev
```
Accede a `http://localhost:4200`. La aplicación proxyficará automáticamente las peticiones `/api` al backend si usas la configuración por defecto.

### 5. Build y Producción (SSR)
Para desplegar en entorno real:
```bash
# Compilar la aplicación (genera dist/occultashield/browser y server)
bun run build

# Servir con el motor SSR Node.js/Bun
bun run serve:ssr
```
La aplicación estará disponible en `http://localhost:4000` (o `PORT` definido en env).

---

## 📂 Arquitectura de Directorios (Subpath Imports)

El proyecto utiliza un sistema de alias moderno (`#`) definido en `tsconfig.json` para mantener modularidad estricta:

*   `#components/*`: **UI Kit**. Componentes puros de presentación (ViolationCard, ProgressBar, Header). Standalone y sin lógica de negocio compleja.
*   `#pages/*`: **Vistas**. Componentes enrutados que orquestan lógica (UploadPage, ReviewPage, AdminPage).
*   `#services/*`: **Capa de Datos**. Servicios inyectables, clientes HTTP y stores de estado (Signals).
*   `#server/*`: **Backend SSR**. Código que **solo** se ejecuta en el servidor (Rutas API de Admin, configuración de Express, Handlers de Auth).
*   `#interface/*`: **Tipos**. Contratos TypeScript compartidos.

---

## 🔒 Detalles de Seguridad (Frontend)
*   **Auth Interceptor**: Inyecta automáticamente tokens de sesión en cabeceras para peticiones API.
*   **Error Interceptor**: Gestiona globalmente respuestas 401/403, redirigiendo al login o refrescando sesiones.
*   **Sanitization**: Todo el contenido HTML renderizado pasa por `DomSanitizer` para prevenir XSS.
