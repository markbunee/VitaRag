# app/api/config_api.py
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import json
import os

from config import get_config, AppConfig
from service.auth_to import User, get_current_active_user

router = APIRouter(prefix="/api/config", tags=["配置管理"])

@router.get("/")
async def get_current_config(
        # current_user: User = Depends(get_current_active_user)
):
    """获取当前系统配置"""
    config = get_config()
    # 返回可序列化的字典，排除不需要暴露的属性
    config_dict = {
        key: value for key, value in config.dict().items()
        if not key.startswith('_')
    }
    return JSONResponse(content=config_dict)

@router.post("/update")
async def update_config(
        config_data: Dict[str, Any] = Body(...),
        # current_user: User = Depends(get_current_active_user)
):
    """更新系统配置"""
    config = get_config()

    # 更新配置
    for key, value in config_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown configuration key: {key}")

    # 可选：将更新后的配置保存到文件
    config_path = os.environ.get("APP_CONFIG_PATH", "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config.dict(), f, ensure_ascii=False, indent=2)

    return {"message": "Configuration updated successfully"}

@router.post("/reload")
async def reload_config(
        # current_user: User = Depends(get_current_active_user)
):
    """重新加载配置"""
    config = get_config().reload()
    return {"message": "Configuration reloaded successfully"}
