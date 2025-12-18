from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List

from config import get_config
from .models import Token, User
from .password import verify_password
from .token import create_access_token
from .dependencies import get_user, get_current_active_user, get_current_admin_user
from pydantic import BaseModel
router = APIRouter(prefix="/api/v1", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str
@router.post("/token", response_model=Token)
async def login_for_access_token(login_data: LoginRequest):
    """
    用户登录获取令牌

    Args:
        form_data: OAuth2表单数据，包含username和password

    Returns:
        包含访问令牌的Token对象

    Raises:
        HTTPException: 如果认证失败
    """
    config = get_config()
    user = get_user(login_data.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证用户提供的明文密码与存储的哈希密码是否匹配
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        raise HTTPException(status_code=400, detail="用户已被禁用")

    # 创建访问令牌
    access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer","expires_in":f"{config.ACCESS_TOKEN_EXPIRE_MINUTES} min"}
@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

@router.get("/users", response_model=List[User])
async def read_users(current_user: User = Depends(get_current_admin_user)):
    """获取所有用户信息（仅管理员）"""
    config = get_config()
    users = []
    for username, user_data in config.USERS.items():
        # 不返回哈希密码
        user_data_copy = user_data.copy()
        user_data_copy.pop("hashed_password", None)
        users.append(User(**user_data_copy))
    return users
