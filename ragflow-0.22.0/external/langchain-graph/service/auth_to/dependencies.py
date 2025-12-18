from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
import logging

from config import get_config
from .models import TokenData, User, UserInDB

# OAuth2 密码流的令牌URL
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")
bearer_scheme = HTTPBearer()
logger = logging.getLogger(__name__)

def get_user(username: str) -> Optional[UserInDB]:
    """
    从配置中获取用户信息

    Args:
        username: 用户名

    Returns:
        用户信息或None
    """
    config = get_config()
    user_dict = config.USERS.get(username)
    if user_dict:
        return UserInDB(**user_dict)
    return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> User:
    """
    验证JWT令牌并获取当前用户

    Args:
        token: JWT令牌

    Returns:
        当前用户信息

    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    config = get_config()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的身份验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except JWTError as e:
        logger.warning(f"JWT error: {str(e)}")
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None:
        logger.warning(f"User not found: {token_data.username}")
        raise credentials_exception

    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    获取当前活跃用户

    Args:
        current_user: 当前用户

    Returns:
        当前活跃用户

    Raises:
        HTTPException: 如果用户被禁用
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="用户已被禁用")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    获取当前管理员用户

    Args:
        current_user: 当前活跃用户

    Returns:
        当前管理员用户

    Raises:
        HTTPException: 如果用户不是管理员
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user
