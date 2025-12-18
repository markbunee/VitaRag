from pydantic import BaseModel
from typing import Optional, List

class Token(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str
    expires_in: str

class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    """用户模型"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    is_admin: bool = False
    scopes: List[str] = []

class UserInDB(User):
    """数据库中的用户模型，包含哈希密码"""
    hashed_password: str
