from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

http_bearer = HTTPBearer()

def _get_token_from_header(credentials: HTTPAuthorizationCredentials) -> str:
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing",
        )

    token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header"
        )
    
    return token

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    return _get_token_from_header(credentials)
