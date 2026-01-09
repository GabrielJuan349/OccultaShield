from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db.surreal_conn import SurrealConn
import os

# We will use this instance across the app
_db_instance = SurrealConn()

async def get_db():
    """
    Dependency to get the SurrealDB session.
    """
    db_name = os.getenv("SURREALDB_ITEM", "test")
    return await _db_instance.getting_db(db_name)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    """
    Dependency to get the current authenticated user.
    Note: Approval check is handled by Angular SSR server.
    """
    try:
        # Check Better-Auth Session
        query = "SELECT * FROM session WHERE token = $token AND expiresAt > time::now() FETCH userId;"
        vars = {"token": token}
        response = await db.query(query, vars)
        
        if not response or not response[0] or 'result' not in response[0]:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        records = response[0]['result']
        if not records:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        session = records[0]
        user = session.get('userId')
        
        if not user or isinstance(user, str):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found for session",
            )
            
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
