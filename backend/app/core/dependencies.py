from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from db.surreal_conn import SurrealConn
import os


# We will use this instance across the app
_db_instance = SurrealConn()

async def get_db():
    """
    Dependency to get the SurrealDB session.
    """
    # Use SURREALDB_DB or let getting_db use its default
    db_name = os.getenv("SURREALDB_DB")
    return await _db_instance.getting_db(db_name)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

async def get_token_from_request(
    request: Request,
    token_query: str = None, # Allow query param ?token=...
) -> str:
    # 1. Try Authorization Header (via oauth2_scheme logic manually or header inspection)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    
    # 2. Try Query Parameter
    if token_query:
        return token_query

    # 3. Try Cookies (if session token is stored in cookie)
    # Better-Auth often uses a cookie named 'better-auth.session_token' or similar?
    # For now, let's stick to query param as it's explicit for SSE.
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user(
    request: Request,
    db = Depends(get_db),
    # We can't easily rely on Depends(oauth2_scheme) because it forces header or form.
    # So we'll use a custom extractor.
):
    """
    Dependency to get the current authenticated user.
    """
    try:
        # Extract token from Header, Query Param, or Cookie
        token = request.query_params.get("token")

        if not token:
             # Fallback to header if no query param
             auth_header = request.headers.get("Authorization")
             if auth_header and auth_header.startswith("Bearer "):
                 token = auth_header.split(" ")[1]

        # Fallback to Better-Auth cookie
        if not token:
            # Intentar múltiples formatos de cookie que Better-Auth podría usar
            cookie_names = [
                "occultashield.session_token",
                "occultashield_session.token",
                "better-auth.session_token",
                "occultashield-session-token",
                "session_token",
                "occultashield.session_data",  # This is the actual cookie name from Better-Auth
            ]

            for cookie_name in cookie_names:
                session_cookie = request.cookies.get(cookie_name)
                if session_cookie:
                    # Try to parse as JSON in case it contains structured data
                    import json
                    try:
                        cookie_data = json.loads(session_cookie)
                        # Better-Auth might store token in various fields
                        token = cookie_data.get('token') or cookie_data.get('session_token') or cookie_data.get('sessionToken')
                        if token:
                            break
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, use the raw value as token
                        token = session_cookie
                        break

        if not token:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 1. Get Session only (no FETCH to avoid complexity)
        query = "SELECT * FROM session WHERE token = $session_token AND expiresAt > time::now();"
        vars = {"session_token": token}
        response = await db.query(query, vars)
        
        records = []
        if isinstance(response, list) and len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
            records = response[0]['result']
        elif isinstance(response, list):
            records = response
        
        if not records:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        session = records[0]
        user_val = session.get('userId')

        # 2. Extract User ID string
        user_id = str(user_val) if user_val else None

        # Fix: SurrealDB python client might return RecordID string with brackets (e.g. user:⟨id⟩)
        # We need to remove them to query correctly.
        if user_id:
             user_id = user_id.replace("⟨", "").replace("⟩", "")
        
        if not user_id:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has no user ID",
            )

        # 3. Fetch User Manualy
        # If it's a Record ID object, conversion to str usually gives "table:id"
        # We handle "user:id" or just "id"
        
        u_query = "SELECT * FROM user WHERE id = $id" 
        u_vars = {"id": user_id}
        
        # If the ID doesn't contain ':', assume it's a raw ID and wrap it
        if ":" not in user_id:
             u_query = "SELECT * FROM user WHERE id = type::thing('user', $id)"
        
        # If the ID is already in format "user:...", SurrealDB query works with both string "user:id" or record link.
        # But specifically for parameter usage, let's try direct string match first.
        # However, if $id is passed as "user:...", type::thing('user', ...) might double wrap it.
        # The safest way is to use the ID as provided if it has a colon.

        u_response = await db.query(u_query, u_vars)

        u_records = []
        if isinstance(u_response, list) and len(u_response) > 0 and isinstance(u_response[0], dict) and 'result' in u_response[0]:
            u_records = u_response[0]['result']
        elif isinstance(u_response, list):
            u_records = u_response

        if u_records:
            return u_records[0]
        # Fallback: Create a minimal user object so the request handles standard fields if the record is missing
        return {
            "id": user_id,
            "role": "user", # Default to user
            "name": "Unknown User",
            "email": "unknown@example.com"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
