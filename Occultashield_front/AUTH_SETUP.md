# 🔐 Sistema de Autenticación JWT - OccultaShield

## 📋 Resumen

Sistema completo de autenticación basado en JWT que protege las rutas `/upload` y `/download` usando Angular Signals y Guards funcionales.

## 🏗️ Arquitectura

### 1. **AuthService** (`src/app/services/auth.service.ts`)
Servicio central que maneja toda la lógica de autenticación:

```typescript
// Métodos principales:
setToken(token: string)      // Guarda el JWT en localStorage
getToken()                   // Obtiene el token actual
logout()                     // Cierra sesión y limpia el token
checkTokenValidity()         // Verifica si el token es válido
getUserInfo()               // Extrae info del usuario del JWT
isAuthenticated()           // Signal reactivo del estado de auth
```

**Características:**
- ✅ Usa Angular Signals para reactividad
- ✅ Almacena el token en `localStorage` con clave `jwt_token`
- ✅ Valida la expiración del token automáticamente
- ✅ Decodifica el payload del JWT (sin verificar firma - esto es responsabilidad del backend)

### 2. **AuthGuard** (`src/app/guards/auth.guard.ts`)
Guard funcional que protege rutas sensibles:

```typescript
export const authGuard: CanActivateFn = (route, state) => {
  // Verifica si hay un JWT válido
  // Si NO → redirige a /login
  // Si SÍ → permite el acceso
}
```

**Características:**
- ✅ Guard funcional moderno (no basado en clases)
- ✅ Guarda la URL intentada en `returnUrl` para redirigir después del login
- ✅ Logs en consola para debugging

### 3. **LoginRegister Component** (`src/app/pages/LoginRegister/`)
Componente de login/registro integrado con el sistema de auth:

**Flujo de Login:**
1. Usuario ingresa credenciales (`user@occultashield.com` / `OccultaShield2024`)
2. Se genera un JWT mock (en producción vendría del backend)
3. Se guarda el token usando `authService.setToken(token)`
4. El token se almacena en `localStorage`
5. Se redirige a la ruta protegida

**Signals usados:**
```typescript
isRegisterMode = signal<boolean>(false)
errorMessage = signal<string | null>(null)
loading = signal<boolean>(false)
```

### 4. **Rutas Protegidas** (`src/app/app.routes.ts`)

```typescript
{
  path: 'upload',
  component: UploadPage,
  canActivate: [authGuard]  // 🔒 Protegida
},
{
  path: 'download',
  component: DownloadPage,
  canActivate: [authGuard]  // 🔒 Protegida
}
```

## 🔄 Flujo de Autenticación

### Login Exitoso:
```
Usuario → LoginComponent → AuthService.setToken() → localStorage
                                ↓
                    Signal isAuthenticated → true
                                ↓
                    Router → /upload (o returnUrl)
```

### Acceso a Ruta Protegida (SIN token):
```
Usuario → /upload → AuthGuard → checkTokenValidity() 
                        ↓
                    NO válido
                        ↓
            Router → /login?returnUrl=/upload
```

### Acceso a Ruta Protegida (CON token):
```
Usuario → /upload → AuthGuard → checkTokenValidity()
                        ↓
                    Válido ✅
                        ↓
                Permite acceso → UploadPage
```

## 💾 Estructura del localStorage

```javascript
// Clave del token
localStorage.getItem('jwt_token')

// Ejemplo de valor almacenado:
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InVzZXJAb2NjdWx0YXNoaWVsZC5jb20iLCJzdWIiOiIxMjM0NSIsIm5hbWUiOiJVc3VhcmlvIE9jY3VsdGFTaGllbGQiLCJpYXQiOjE3MzAwMDAwMDAsImV4cCI6MTczMDA4NjQwMH0.mock-signature"
```

## 🔧 Estructura del JWT Mock

```json
// Header
{
  "alg": "HS256",
  "typ": "JWT"
}

// Payload
{
  "email": "user@occultashield.com",
  "sub": "12345",
  "name": "Usuario OccultaShield",
  "iat": 1730000000,        // Timestamp de emisión
  "exp": 1730086400         // Timestamp de expiración (24h)
}

// Signature
"mock-signature-for-testing"
```

## 🧪 Credenciales de Prueba

Para testing en desarrollo:

```
Email: user@occultashield.com
Password: OccultaShield2024
```

## 🚀 Integración con Backend Real

Cuando conectes con tu backend real:

### 1. Crear un servicio HTTP:

```typescript
// auth-http.service.ts
@Injectable({ providedIn: 'root' })
export class AuthHttpService {
  constructor(private http: HttpClient) {}

  login(email: string, password: string): Observable<{token: string}> {
    return this.http.post<{token: string}>('/api/auth/login', {
      email,
      password
    });
  }

  register(email: string, password: string): Observable<any> {
    return this.http.post('/api/auth/register', {
      email,
      password
    });
  }
}
```

### 2. Actualizar el LoginRegister component:

```typescript
// Reemplazar el setTimeout por:
this.authHttpService.login(email, password).subscribe({
  next: (response) => {
    this.authService.setToken(response.token);
    this.router.navigate([this.returnUrl]);
  },
  error: (error) => {
    this.errorMessage.set('Email o contraseña incorrectos.');
    this.loading.set(false);
  }
});
```

### 3. Agregar interceptor para incluir token en requests:

```typescript
// auth.interceptor.ts
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req);
};
```

## 📊 Testing

### Verificar que el token se guarda:
1. Abrir DevTools → Application → Local Storage
2. Buscar la clave `jwt_token`
3. Verificar que contiene el JWT

### Verificar el guard:
1. Sin login, intentar acceder a `/upload` → Redirige a `/login`
2. Hacer login → Verificar que `isAuthenticated()` es `true`
3. Acceder a `/upload` → Permite el acceso
4. Borrar el token del localStorage → Intentar acceder → Redirige a login

### Verificar expiración:
1. Modificar el `exp` del token a una fecha pasada
2. Intentar acceder a ruta protegida
3. Debería cerrar sesión automáticamente

## 🛠️ Comandos Útiles

```typescript
// En la consola del navegador:

// Ver el token actual
localStorage.getItem('jwt_token')

// Eliminar el token manualmente
localStorage.removeItem('jwt_token')

// Decodificar un token JWT
const token = localStorage.getItem('jwt_token');
const payload = JSON.parse(atob(token.split('.')[1]));
console.log(payload);

// Ver fecha de expiración
const exp = payload.exp;
console.log(new Date(exp * 1000));
```

## ⚠️ Notas de Seguridad

1. **No validar firma en frontend**: La validación de la firma JWT DEBE hacerse en el backend
2. **HTTPS en producción**: Los tokens solo deben transmitirse por HTTPS
3. **Tokens de corta duración**: Configura expiración corta (15-60 min) con refresh tokens
4. **XSS Protection**: Angular protege contra XSS, pero siempre sanitiza inputs
5. **CSRF Protection**: Implementa tokens CSRF si usas cookies

## 📝 TODO para Producción

- [ ] Conectar con backend real
- [ ] Implementar refresh tokens
- [ ] Agregar interceptor HTTP
- [ ] Implementar recuperación de contraseña
- [ ] Agregar rate limiting en login
- [ ] Implementar 2FA (opcional)
- [ ] Agregar tests unitarios
- [ ] Configurar CORS correctamente

## 🎯 Estado Actual

✅ AuthService implementado con Signals
✅ AuthGuard funcional protegiendo rutas
✅ LoginRegister integrado con AuthService
✅ Token almacenado en localStorage
✅ Validación de expiración
✅ Redirección con returnUrl
✅ Mock JWT para testing

🔄 Pendiente integración con backend real
