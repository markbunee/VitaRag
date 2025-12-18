""" FastAPI应用入口 """
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from service import config_api, chat_api,agent  # 导入配置API路由
from config import get_config, logger  # 导入配置获取函数
from service.auth_to import auth_router  # 导入认证路由和依赖
import sys
import io
import warnings

from utils.model_health import check_model_health

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
warnings.filterwarnings("ignore")

DEBUG_MODE = os.getenv("DEBUG", "true").lower() == "true"
app = FastAPI(
    title="LangGraph智能体开发系统",
    description="基于LangGraph的流程化智能体开发系统",
    version="1.0.0",
    docs_url=None if not DEBUG_MODE else "/docs",
    redoc_url=None if not DEBUG_MODE else "/redoc",
    openapi_url=None if not DEBUG_MODE else "/openapi.json"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "GET", "DELETE"],
    allow_headers=["*"],
)

# 注册配置API路由
app.include_router(config_api.router)

# 注册认证API路由
app.include_router(auth_router.router)

# 注册会话API路由
app.include_router(chat_api.router)

# 注册会话API路由
app.include_router(agent.router)

# 存储执行中的工作流
running_workflows = {}


def get_all_model_names(config):
    return list(dict.fromkeys(config.AGENT_LLM_MODELS + config.COT_LLM_MODELS))


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    config = get_config()
    return {"status": "healthy", "config_version": id(config)}

@app.get("/api/v1/models")
async def get_models():
    """
    获取模型相关配置信息，仅返回当前健康的模型列表
    """
    config = get_config()
    LLM_MODEL_API = config.LLM_MODEL_API
    model_names = get_all_model_names(config)
    # 并发健康检查
    check_tasks = [
        check_model_health(LLM_MODEL_API[name])
        for name in model_names
        if name in LLM_MODEL_API
    ]
    status_list = await asyncio.gather(*check_tasks)
    healthy_models = [name for name, status in zip(model_names, status_list) if status]
    unhealthy_models = [name for name, status in zip(model_names, status_list) if not status]

    logger.info(f"当前可用健康模型列表: {healthy_models}")
    logger.warning(f"当前不可用模型列表: {unhealthy_models}")
    return {
        "llm_model_names": healthy_models,
    }
    # # 如果需要带可用状态（注释掉作为备份）
    # results = [
    #     {"name": name, "available": status}
    #     for name, status in zip(model_names, status_list)
    # ]
    # return {
    #     "llm_model_names": results,
    # }

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 应用启动时加载配置
    config = get_config()

    # 可以从环境变量加载配置文件路径
    import os
    config_path = os.environ.get("APP_CONFIG_PATH", "config.json")
    if os.path.exists(config_path):
        config.load_from_json(config_path)

    # 可以在这里初始化其他资源
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    # 清理所有运行中的工作流
    running_workflows.clear()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8116)
