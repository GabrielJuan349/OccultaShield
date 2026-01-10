from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import json
from db.surreal_conn import SurrealConn

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, surreal_conn: SurrealConn):
        super().__init__(app)
        self.conn_manager = surreal_conn
        # database selection should be handled in lifespan or per-request
        # self.surreal_conn = surreal_conn.getting_db("test")
        # Rutas que no requieren autenticación
        self.public_routes = ["/", "/auth/login", "/auth/register", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Permitir rutas públicas
        if request.url.path in self.public_routes or request.method == "OPTIONS":
            return await call_next(request)
        
        # Verificar el header de autorización
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "No token provided"}
            )
        
        try:
            # Extraer el token (formato: "Bearer <token>")
            token = auth_header.split(" ")[1]
            
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
        """Verifica el token usando SurrealDB"""
        try:
            # Autenticar con el token JWT
            if not self.conn_manager.db:
                return False
            
            query = "SELECT * FROM session WHERE token = $session_token AND expiresAt > time::now();"
            vars = {"session_token": token}
            print(f"DEBUG: Verifying token: {token[:10]}... Vars: {vars}")
            response = await self.conn_manager.db.query(query, vars)
            print(f"DEBUG: SurrealDB Auth Response: {response}")
            
            if not response: 
                print("DEBUG: No response from DB")
                return False
                
            # Accessing result
            # SDK response format: [{'result': [...], 'status': 'OK', 'time': ...}]
            result_data = response[0]
            if not result_data or 'result' not in result_data:
                print(f"DEBUG: Unexpected response structure: {result_data}")
                return False
                
            records = result_data['result']
            print(f"DEBUG: Records found: {len(records)}")
            return len(records) > 0
                
        except Exception as e:
            print(f"Token verification failed: {e}")
            return False
        except Exception as e:
            print(f"Token verification failed: {e}")
            return False
