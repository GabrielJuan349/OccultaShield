# 🧪 Guía de Testing del Sistema de Autenticación

## ✅ Pasos para Probar

### 1. **Reiniciar el Servidor de Desarrollo**

```bash
# Detener el servidor actual (Ctrl+C)
# Limpiar y reiniciar
npm start
```

### 2. **Verificar que el Servidor Está Corriendo**

- Abrir el navegador en `http://localhost:4200`
- Deberías ver la Landing Page

### 3. **Probar el Guard (Ruta Protegida sin Login)**

1. Ir directamente a: `http://localhost:4200/upload`
2. **Resultado esperado:** Te redirige automáticamente a `/login?returnUrl=/upload`
3. **En la consola del navegador deberías ver:** `⚠️ Acceso denegado - Redirigiendo al login`

### 4. **Hacer Login**

**Credenciales de prueba:**
- Email: `user@occultashield.com`
- Password: `OccultaShield2024`

**Proceso:**
1. Ir a `http://localhost:4200/login`
2. Ingresar las credenciales
3. Hacer clic en "Iniciar Sesión"

**Resultado esperado:**
- En consola: `✅ Login exitoso - Token guardado en localStorage`
- Redirige automáticamente a `/upload`

### 5. **Verificar el Token en LocalStorage**

**Abrir DevTools:**
1. Presiona `F12` o `Ctrl+Shift+I`
2. Ve a la pestaña **Application** (o **Almacenamiento**)
3. En el panel izquierdo → **Local Storage** → `http://localhost:4200`
4. Busca la clave: `jwt_token`
5. Deberías ver un valor como:
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InVzZXJAb2...
   ```

### 6. **Verificar Acceso a Rutas Protegidas**

Con el token guardado:

1. Ir a `http://localhost:4200/upload` ✅ Debería funcionar
2. Ir a `http://localhost:4200/download` ✅ Debería funcionar
3. **En consola:** `✅ Usuario autenticado - permitiendo acceso a: /upload`

### 7. **Probar Logout Manual**

**En la consola del navegador:**
```javascript
localStorage.removeItem('jwt_token');
location.reload();
```

Luego intenta acceder a `/upload` → Debería redirigir a `/login`

## 🔍 Debugging

### Si el error persiste:

**1. Limpiar caché del navegador:**
```
Ctrl + Shift + Delete → Borrar todo
```

**2. Verificar que las rutas están configuradas:**

Abrir `src/app/app.routes.ts` y verificar:
```typescript
{
  path: 'upload',
  component: UploadPage,
  canActivate: [authGuard]
}
```

**3. Verificar logs en consola:**

Deberías ver uno de estos mensajes:
- `✅ Usuario autenticado - permitiendo acceso a: /upload`
- `⚠️ Acceso denegado - Redirigiendo al login`

**4. Verificar que el componente UploadPage existe:**
```bash
# Verificar que el archivo existe
dir src\app\pages\UploadPage\UploadPage.ts
```

**5. Hard reload de la app:**
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

## 🐛 Errores Comunes y Soluciones

### Error: "Cannot GET /upload"

**Causa:** El servidor de desarrollo no está corriendo o hay un problema de ruteo.

**Solución:**
```bash
# Detener el servidor (Ctrl+C)
npm start
```

### Error: "Acceso denegado" incluso después de login

**Causa:** El token no se guardó correctamente o está usando la clave incorrecta.

**Verificar:**
1. Ir a DevTools → Application → Local Storage
2. Buscar la clave `jwt_token` (NO `token`)
3. Si no existe, el login no funcionó

**Solución:**
- Volver a hacer login
- Verificar en la consola que veas: `✅ Login exitoso - Token guardado en localStorage`

### Error CSP (Content Security Policy)

El error CSP que mencionas:
```
Refused to connect to 'http://localhost:4200/.well-known/appspecific/com.chrome.devtools.json'
```

**Causa:** Este es un warning de Chrome DevTools, NO afecta la funcionalidad.

**Solución:** Ignorarlo o actualizar Chrome.

## 📊 Verificación Completa del Sistema

Ejecuta este script en la consola del navegador para verificar todo:

```javascript
// 1. Verificar que existe el token
const token = localStorage.getItem('jwt_token');
console.log('Token existe:', !!token);

if (token) {
  // 2. Decodificar el token
  const payload = JSON.parse(atob(token.split('.')[1]));
  console.log('Payload del token:', payload);
  
  // 3. Verificar expiración
  const exp = new Date(payload.exp * 1000);
  const now = new Date();
  console.log('Token expira:', exp);
  console.log('Fecha actual:', now);
  console.log('Token válido:', exp > now);
} else {
  console.log('❌ No hay token - debes hacer login');
}
```

## ✅ Checklist Final

- [ ] Servidor corriendo en `http://localhost:4200`
- [ ] `/` muestra la Landing Page
- [ ] `/login` muestra el formulario de login
- [ ] `/upload` sin token redirige a `/login`
- [ ] Login con credenciales correctas funciona
- [ ] Token se guarda en localStorage con clave `jwt_token`
- [ ] `/upload` con token permite acceso
- [ ] `/download` con token permite acceso
- [ ] Console logs muestran mensajes de autenticación

## 🚀 Próximos Pasos

Una vez que todo funcione:

1. **Crear un botón de logout** en la navbar
2. **Integrar con backend real** (reemplazar mock JWT)
3. **Agregar interceptor HTTP** para incluir token en requests
4. **Implementar refresh tokens**
5. **Agregar manejo de errores mejorado**

---

**Credenciales de Prueba:**
- Email: `user@occultashield.com`
- Password: `OccultaShield2024`
