# Documentación Detallada del Frontend (OccultaShield)

**Versión del Proyecto:** 1.2
**Fecha de Actualización:** 21/12/2025
**Angular Version:** v21 (Stable)

---

## 1. Visión General de la Arquitectura
El frontend de OccultaShield es una aplicacion **Single Page Application (SPA)** con capacidades de **Server-Side Rendering (SSR)**, construida sobre **Angular v21**. 

### 1.1 Filosofía "Zoneless" y Reactividad Fina
Dado que estamos en 2025 con Angular v21, el proyecto adopta completamente la filosofía **Zoneless** (sin `zone.js`):
*   **Signals (Señales):** Son la única fuente de verdad para el estado. No se utilizan `BehaviorSubjects` ni decoradores obsoletos como `@Input` (se usa `input()`).
*   **Change Detection:** `OnPush` por defecto en todos los componentes. La detección de cambios se dispara granularmente solo cuando una Señal cambia.
*   **RxJS Minimizado:** RxJS se utiliza únicamente para flujos de eventos complejos o llamadas HTTP que requieren operadores avanzados (`retry`, `debounce`). Para todo lo demás (estado local, promesas), se prefieren **Signals** y **Resource API**.

### 1.2 Stack Tecnológico
*   **Framework:** Angular v21.0.0
*   **Build System:** Angular CLI (esbuild based)
*   **Runtime:** Bun v1.3.1 (usado para scripts y gestión de paquetes, aunque el runtime de navegador es JS estándar).
*   **Estilos:** CSS Modules / Vanilla CSS con diseño Glassmorphism.

---

## 2. Inmersión Profunda en Componentes y Servicios

### 2.1 `UploadPage` y el uso de Resource API
Este componente representa el cambio de paradigma de Angular moderno.
*   **Ubicación:** `#pages/UploadPage/UploadPage.ts`
*   **Lógica:**
    *   En lugar de llamar a `http.post().subscribe()`, se define un **`resource`** (experimental en v19, estable en v21).
    *   El `loader` del recurso es una función asíncrona (`async/await`) que envuelve la llamada `firstValueFrom(videoService.uploadVideo(...))`.
    *   Esto expone automáticamente señales como `uploadResource.isLoading`, `uploadResource.value` y `uploadResource.error`, simplificando dramáticamente la plantilla HTML.
    *   **Efecto de Navegación:** Se utiliza `effect(() => ...)` para vigilar `uploadResource.value()`. Cuando este tiene un `video_id` válido, navega imperativamente a `/processing`.

### 2.2 `ProcessingSSEService` (El Corazón Reactivo)
Gestiona la conexión en tiempo real con el backend vía **Server-Sent Events (SSE)**.
*   **Ubicación:** `#services/processing-sse.service.ts`
*   **Arquitectura:**
    *   No usa `EventSource` nativo directamente en el componente. Lo encapsula en un servicio Singleton.
    *   **Signals Reactivos:** Mantiene señales privadas (`_progress`, `_phase`) y expone versiones `readonly` (`progress`, `phase`). Esto garantiza que nadie fuera del servicio pueda mutar el estado.
    *   **Reconexión Inteligente:** Si la conexión SSE cae (`onerror`), implementa un `setTimeout` para reintentar, crucial para redes inestables.
    *   **Mapeo de Eventos:** Escucha eventos personalizados (`phase_change`, `detection`, `verification`) y actualiza múltiples señales atómicamente. Por ejemplo, al recibir una detección, actualiza el `Map` de detecciones y el contador total simultáneamente desencadenando *una sola* actualización de vista.

### 2.3 `ReviewPage` y Gestión de Estado Local
*   **Ubicación:** `#pages/ReviewPage/ReviewPage.ts`
*   **Lógica de Selección:**
    *   Usa un `Map<string, Decision>` dentro de un `signal` para rastrear qué acción (Anonymize/Keep) ha tomado el usuario para cada violación.
    *   **Optimización de Rendimiento:** Al usar un Map y Signals, marcar una casilla en una lista de 500 violaciones es O(1) y no provoca re-renderizados de toda la lista, solo de la tarjeta afectada.

### 2.4 Autenticación (Better-Auth + Angular)
*   **Cliente (`#lib/auth-client.ts`):** Instancia configurada del cliente de Better-Auth. Es "agnóstica" del framework.
*   **Servicio (`AuthService`):**
    *   Puente entre el cliente agnóstico y Angular.
    *   Al iniciar (`constructor`), verifica la sesión (`getSession`).
    *   **Computed Signals:** `isAuthenticated`, `userName`, `isAdmin` son señales computadas derivadas de la señal base `_session`. Si la sesión caduca, todas estas derivadas se actualizan instantáneamente en toda la UI.

---

## 3. Estructura de Directorios y Alias (Detalle)

El proyecto fuerza el uso de alias para mantener una arquitectura limpia y modular ("Vertical Slice Architecture" compatible).

| Alias | Ruta Real | Propósito |
| :--- | :--- | :--- |
| `#components/*` | `src/app/components/*` | Componentes "tontos" (UI pura, reciben inputs, emiten outputs). |
| `#pages/*` | `src/app/pages/*` | Componentes "inteligentes" (tienen estado, inyectan servicios, son rutas). |
| `#services/*` | `src/app/services/*` | Lógica de negocio, estado global y llamadas API. |
| `#interface/*` | `src/app/interface/*` | Contratos de datos (Interfaces TS, Enums, Zod Schemas). |
| `#guards/*` | `src/app/guards/*` | Lógica de protección de rutas (CanActivateFn). |
| `#lib/*` | `src/app/lib/*` | Código de infraestructura (ej. cliente Better-Auth). |

---

## 4. Problemas Conocidos y Gotchas en v21

1.  **Strict Type Checking en Templates:**
    *   Angular v21 es extremadamente estricto. Un error común es intentar pasar `null` a un input que espera `string`.
    *   *Solución:* Usar el operador coalescente `{{ user()?.name ?? 'Anonymous' }}`.
2.  **Resource API vs SSR:**
    *   Las llamadas Resource se ejecutan en el servidor durante SSR. Si el endpoint requiere autenticación (Cookies/Headers), hay que asegurar que `node-fetch` en el servidor pase esas cookies desde la petición original, lo cual a veces requiere configuración extra en `server.ts`.
3.  **Hydration Mismatch con Fechas:**
    *   Si el servidor renderiza una hora (`Date.now()`) y el cliente otra al hidratar, la pantalla parpadeará y saldrá un error en consola. Asegurar formatear fechas de forma estática o usar `TransferState`.
