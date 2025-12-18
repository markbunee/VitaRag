"""
输出数据模型定义，用于FastAPI响应格式化
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    """错误响应模型"""
    status: str = "error"
    message: str
    details: Optional[Any] = None

class SuccessResponse(BaseModel):
    """成功响应模型"""
    status: str = "success"
    data: Any

class StreamingResponse(BaseModel):
    """流式响应的单个片段"""
    content: str
    finished: bool = False
    source_files: Optional[List[str]] = None
