# Plan de Resolución: Error 401 Unauthorized en Panel de Administración

## Análisis del Problema
El usuario, logueado como administrador y con un sesión válida (según los logs del cliente `tokenLength: 32`), recibe errores `401 Unauthorized` al intentar acceder a los endpoints protegidos bajo `/api/admin/*` (`/api/admin/stats`, `/api/admin/users`, etc.).

**Observaciones Clave:**
1.  **Interceptores del Cliente:** El cliente (Angular) está enviando correctamente el token. El interceptor de log muestra `hasToken: true`.
2.  **Servidor SSR (Express/Better-Auth):** El archivo `server.ts` maneja estas rutas.
3.  **Middleware `requireAdmin`:** En `frontend/server/lib/admin.ts`, la función `requireAdmin` verifica la sesión.
4.  **Causa Probable:**
    *   La verificación de sesión en `requireAdmin` usando `auth.api.getSession` está fallando o no está recibiendo las cookies/headers correctamente desde la petición original de Express.
    *   En `server.ts` (Línea 54), hay un manejo manual de headers para convertir de Express a Web Request para las rutas de auth. Sin embargo, en `admin.ts` (Línea 30), se hace una conversión similar pero podría ser incompleta o incorrecta para `getSession`, especialmente en lo referente a cookies, que son críticas para `better-auth`.
    *   El log `Admin Access Denied: No session found` sugiere que `getSession` devuelve `null`.

## Solución Propuesta
Mejorar la propagación de headers y cookies en el middleware `requireAdmin` para asegurar que `Better-Auth` pueda validar la sesión correctamente.

### Pasos de Implementación

#### 1. Modificar `requireAdmin` en `frontend/server/lib/admin.ts`
Ubicación: `frontend/server/lib/admin.ts`, función `requireAdmin`.

**Problema actual:**
El objeto `headers` se reconstruye manualmente. Es posible que falten detalles sutiles o que `getSession` requiera un objeto `headers` en un formato específico (Headers API standard vs POJO). El código actual crea un objeto `Headers` (Web API), lo cual es correcto para `better-auth`, pero la transformación de `req.headers` de Express podría estar perdiendo información if `req.headers` cookies no se están pasando tal cual.

**Cambio:**
Asegurarse de que el header `cookie` se transfiera explícitamente y sin modificaciones. Aunque el bucle automatizado debería hacerlo, es más seguro usar `auth.api.getSession({ headers: req.headers })` si `better-auth` soporta el objeto plano de headers de node, O, más probablemente, asegurarse de pasar el objeto `Headers` construido correctamente y verificar que `auth.api.getSession` lo esté consumiendo bien.

Una mejora crucial es usar `fromNodeHeaders` si better-auth provee utilidades, o simplemente robustecer la copia.

```typescript
// En requireAdmin
const headers = new Headers();
for (const [key, value] of Object.entries(req.headers)) {
    if (value) {
        // Asegurar que las cookies se pasen íntegras
        headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    }
}
// Log de depuración temporal para ver qué headers llegan
console.log('Headers passed to getSession:', Object.fromEntries(headers.entries()));

const session = await auth.api.getSession({
    headers: headers
});
```
*Nota:* El código actual ya hace esto. El problema podría ser que `req` en Express a veces tiene los headers en minúsculas y `Better-Auth` podría esperar otra cosa, aunque HTTP es case-insensitive.

Una posibilidad más fuerte: **El cliente está haciendo peticiones a `http://mise-ralph.uab.cat:4201` pero el servidor corre en ese puerto y espera cookies para `localhost` o el dominio no coincide**.
Si el cliente está en `:4200` y el server en `:4201`, y las cookies son `HttpOnly` y `SameSite=Lax` o `Strict`, podrían no estar enviándose en peticiones cruzadas (CORS) a menos que `withCredentials` sea true (que lo es) Y el servidor acepte el origen.

Revisar `server.ts`:
```typescript
app.use(cors({
  origin: ['http://localhost:4200', ...],
  credentials: true,
  // ...
}));
```
La configuración de CORS parece correcta.

**Hipótesis de fallo de `getSession`:**
`getSession` de better-auth lee los headers. Si el token viaja en `Authorization: Bearer <token>`, `better-auth` debe estar configurado para leerlo de ahí. Si viaja en cookie, debe leer la cookie.
El log del cliente dice `hasToken: true`. Normalmente esto implica un Bearer token si es un interceptor manual, o simplemente que la cookie existe.
Si es Bearer Token, `better-auth` lo soporta nativamente.

**Plan de Acción Refinado:**
1.  **Depuración Mejorada:** Añadir logs en `requireAdmin` para ver *exactamente* qué headers recibe Express (`req.headers`) vs qué headers estamos construyendo para `getSession`. Ver si llega la cookie de sesión o el header `Authorization`.
2.  **Fallback de Token:** Si la cookie falla, asegurarse de que `better-auth` esté intentando leer el Bearer Token del header `Authorization`.

**Pasos:**
1.  Editar `frontend/server/lib/admin.ts`.
2.  En `requireAdmin`, imprimir `req.headers['authorization']` y `req.headers['cookie']`.
3.  Verificar si estamos pasando el contexto de la request correctamente.

**Corrección Específica (Safe Bet):**
A veces la conversión manual de headers falla con `set-cookie` o cookies múltiples.
Vamos a asegurarnos de pasar el objeto `Headers` estándar correctamente.

### Archivos Afectados
- `frontend/server/lib/admin.ts`

### Resultado Esperado
El log imprimirá qué está recibiendo el servidor. Si el problema es la propagación de headers, el ajuste en el bucle de copia o el uso directo de `req` (si la librería lo permite) lo solucionará.
Si el problema es que el token expira o es inválido, el 401 es correcto, pero el usuario dice que "acaba de entrar", así que asumimos token válido no reconocido.
