from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Tuple
import json
import time
from db.surreal_conn import SurrealConn

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, surreal_conn: SurrealConn):
        super().__init__(app)
        self.conn_manager = surreal_conn
        # Cache de tokens verificados: {token: (timestamp, is_valid)}
        self._token_cache: Dict[str, Tuple[float, bool]] = {}
        self._cache_ttl = 300  # 5 minutos de caché
        
        # Rutas que no requieren autenticación
        self.public_routes = ["/", "/auth/login", "/auth/register", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Permitir rutas públicas
        if request.url.path in self.public_routes or request.method == "OPTIONS":
            return await call_next(request)
        
        # Verificar el header de autorización
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        # Fallback: Verificar query param (necesario para SSE)
        if not token:
            token = request.query_params.get("token")
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "No token provided"}
            )
        
        try:
            # Si venía del header ya lo tenemos limpio, si es query param es el token directo
             
            # Verificar el token con SurrealDB
            
            # Verificar el token con SurrealDB
            is_valid = await self.verify_token(token)
            
            if not is_valid:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Invalid token"}
                )
            
            # Token válido, continuar con la petición
            response = await call_next(request)
            return response
            
        except IndexError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid authorization header format"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Authentication error: {str(e)}"}
            )
    
    async def verify_token(self, token: str) -> bool:
        """Verifica el token usando SurrealDB con caché"""
        try:
            # 1. Verificar caché primero
            current_time = time.time()
            if token in self._token_cache:
                cached_time, is_valid = self._token_cache[token]
                # Si el caché es reciente y válido, usarlo
                if current_time - cached_time < self._cache_ttl:
                    print(f"DEBUG: Token verificado desde caché (edad: {current_time - cached_time:.1f}s)")
                    return is_valid
                else:
                    # Caché expirado, eliminar
                    del self._token_cache[token]
            
            # 2. Verificar con la base de datos
            if not self.conn_manager.db:
                return False
            
            query = "SELECT * FROM session WHERE token = $session_token AND expiresAt > time::now();"
            vars = {"session_token": token}
            print(f"DEBUG: Verifying token from DB: {token[:10]}...")
            response = await self.conn_manager.db.query(query, vars)
            print(f"DEBUG: SurrealDB Auth Response: {response}")
            
            if not response: 
                print("DEBUG: No response from DB")
                self._token_cache[token] = (current_time, False)
                return False
                
            # Handle different response formats
            # Case 1: Wrapped response [{'result': [...], 'status': 'OK'}]
            if isinstance(response, list) and len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                records = response[0]['result']
            # Case 2: Direct list of records [{...}, {...}]
            elif isinstance(response, list):
                records = response
            else:
                print(f"DEBUG: Unexpected response type: {type(response)}")
                self._token_cache[token] = (current_time, False)
                return False
                
            is_valid = len(records) > 0
            print(f"DEBUG: Records found: {len(records)}, is_valid: {is_valid}")
            
            # 3. Actualizar caché
            self._token_cache[token] = (current_time, is_valid)
            
            # 4. Limpiar caché antigua (cada 100 verificaciones)
            if len(self._token_cache) > 100:
                self._cleanup_cache(current_time)
            
            return is_valid
                
        except Exception as e:
            print(f"Token verification failed: {e}")
            return False
    
    def _cleanup_cache(self, current_time: float):
        """Elimina entradas de caché expiradas"""
        expired_tokens = [
            token for token, (cached_time, _) in self._token_cache.items()
            if current_time - cached_time >= self._cache_ttl
        ]
        for token in expired_tokens:
            del self._token_cache[token]
        print(f"DEBUG: Cache cleanup - removed {len(expired_tokens)} expired tokens")
