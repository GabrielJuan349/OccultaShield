<div align="center">

# 🌐 OccultaShield Frontend

### Interfaz de Alta Fidelidad para Análisis de Privacidad (Angular v21)

[![Angular](https://img.shields.io/badge/Angular-v21.0-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.io/)
[![Bun](https://img.shields.io/badge/Bun-1.3.1-000000?style=for-the-badge&logo=bun&logoColor=white)](https://bun.sh/)
[![Zoneless](https://img.shields.io/badge/Architecture-Zoneless-blue?style=for-the-badge)](https://angular.dev)

**Arquitectura de vanguardia sin Zone.js, basada íntegramente en Signals y SSR optimizado para una experiencia de usuario instantánea.**

</div>

---

## 🚀 Visión General

**OccultaShield Frontend** es una aplicación SPA/SSR construida con las tecnologías más modernas disponibles en 2025. Utiliza un paradigma de reactividad fina (**Signals API**) y comunicación en tiempo real (**SSE**) para guiar al usuario a través del proceso de cumplimiento del RGPD.

---

## ✨ Características Técnicas Destacadas

### 1. Filosofía Zoneless y Signals
- **Cero Zone.js**: Menor tamaño de bundle y mayor rendimiento al eliminar la sobrecarga de detección de cambios global.
- **Signals API**: Gestión de estado granular. Solo se re-renderizan los fragmentos de la pantalla necesarios.
- **Resource API**: Manejo declarativo de peticiones HTTP, eliminando la necesidad de subscriptions manuales en RxJS.

### 2. Monitorización en Tiempo Real (SSE)
- El servicio `ProcessingSSEService` se conecta al backend para recibir eventos de:
    - `phase_change`: Cambio entre detección, verificación y edición.
    - `detection`: Nuevas infracciones encontradas en el video.
    - `progress`: Porcentaje de avance real.

### 3. Review Quirúrgica (Human-in-the-Loop)
- **Visualización Precision**: Gracias a YOLOv11, el frontend permite ver las siluetas segmentadas exactas detectadas por la IA.
- **Gestión de Decisiones**: Un estado reactivo basado en `Map` y `Signals` permite gestionar cientos de infracciones sin degradar el rendimiento de la UI.

---

## 🏃 Guía de Inicio Rápido

### Instalación
Se recomienda usar **Bun** para una instalación ultra rápida:
```bash
cd frontend
bun install
# o
npm install
```

### Configuración (`.env`)
```bash
VITE_API_URL=http://localhost:8900/api/v1
AUTH_URL=http://localhost:4000
```

### Ejecución en Desarrollo
```bash
bun dev
# o
ng serve
```
Disponible en `http://localhost:4200`.

### Ejecución en Producción (SSR)
```bash
bun run build
bun run serve:ssr
```
Disponible en `http://localhost:4000`.

---

## 📂 Estructura y Alias
El proyecto utiliza **Subpath Imports** para mantener una estructura modular limpia:

- `#components/*`: Componentes UI puros (ViolationCard, ProgressBar).
- `#pages/*`: Páginas inteligentes (UploadPage, ProcessingPage, ReviewPage).
- `#services/*`: Lógica de negocio y comunicación SSE/REST.
- `#interface/*`: Contratos de datos y esquemas de validación.

---

## 🛡️ Seguridad y Privacidad
- **Better-Auth**: Gestión de sesiones segura y moderna.
- **Anti-Screenshot**: Las tarjetas de revisión ocultan imágenes automáticamente si se detectan atajos de teclado de captura de pantalla.
- **Watermarking Dinámico**: Superposición de marcas de agua en las previsualizaciones de infracciones para evitar filtraciones.

---

## 🔍 Notas para Desarrolladores
- **Hydration**: Uso de `withEventReplay()` para que no se pierdan interacciones del usuario durante la carga del SSR.
- **Path Aliases**: Olvídate de los `../../../`, usa prefijos como `#services/`.
- **Zoneless Debugging**: Los cambios en señales disparan `refreshView()` automáticamente sin `NgZone`.
