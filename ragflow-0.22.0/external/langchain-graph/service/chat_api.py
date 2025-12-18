# app/api/config_api.py
from utils.utils import save_uploaded_files
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from sse_starlette import EventSourceResponse

from api_process.input import DocumentQueryForm
from api_process.output import ErrorResponse
from config import get_config
from graph.llm_processor import two_phase_query_process
from service.auth_to import User, get_current_active_user
from utils.validators import validate_inputs

# 新增导入
from utils.db_manager import (
    save_session_files_to_db,
    get_session_files_from_db,
    save_conversation_history_to_db,
    get_conversation_history_from_db,
    delete_session_from_db,
    get_session_info
)
from utils.file_manager import save_uploaded_files_safely, cleanup_old_sessions

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["智能对话"])
@router.post("/v1/chat-conversation", response_model=None)
async def chat_conversation(
        query_form: DocumentQueryForm = Depends()
):
    """
    多轮对话接口，支持文件上传和会话历史管理。
    - 通过表单提交用户输入和文件
    - 支持会话历史的保存和获取
    - 使用SQLite持久化存储会话和文件信息
    - 支持多进程安全访问
    """
    # 获取最新配置
    config = get_config()

    # 验证输入
    is_valid, error_message = validate_inputs(
        query_form.file_names,
        query_form.tags,
        query_form.files,
        query_form.kb_names,
        query_form.sys_query
    )
    if not is_valid:
        return ErrorResponse(message=error_message)

    session_id = query_form.session_id
    # 查找或创建会话ID
    # session_id = None
    if query_form.conversation_history and len(query_form.conversation_history) > 0:
        for message in query_form.conversation_history:
            if isinstance(message, dict) and "session_id" in message:
                session_id = message.get("session_id")
                break

    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session with ID: {session_id}")
    else:
        logger.info(f"Using existing session with ID: {query_form.session_id}")

    try:
        # 处理上传的文件
        file_paths = []
        if query_form.files:
            logger.info(f"Processing {len(query_form.files)} uploaded files for session {session_id}")
            file_paths = await save_uploaded_files_safely(query_form.files, session_id)

            if file_paths:
                # 保存文件信息到数据库
                if not save_session_files_to_db(session_id, file_paths, query_form.file_names):
                    logger.warning(f"Failed to save file information to database for session {session_id}")

        # 从数据库获取该会话所有相关文件
        all_file_paths = get_session_files_from_db(session_id)
        logger.info(f"Found {len(all_file_paths)} files associated with session {session_id}")

        # 保存会话历史
        if query_form.conversation_history:
            if not save_conversation_history_to_db(session_id, query_form.conversation_history):
                logger.warning(f"Failed to save conversation history for session {session_id}")

        # 准备初始状态
        initial_state = {
            "file_names": query_form.file_names,
            "tags":query_form.tags,
            "file_paths": all_file_paths,  # 使用从数据库获取的所有文件路径
            "knowledge_base_type":query_form.knowledge_base_type,
            "kb_names": query_form.kb_names,
            "kb_token": query_form.kb_token if hasattr(query_form, "kb_token") else "",
            "top_k": query_form.top_k or config.DEFAULT_TOP_K,
            "top_n": query_form.top_n or config.DEFAULT_TOP_N,
            "key_weight": query_form.key_weight or config.DEFAULT_KEY_WEIGHT,
            "input_body": query_form.input_body,
            "system_prompt": query_form.system_prompt or config.DEFAULT_SYSTEM_PROMPT,
            "sys_query": query_form.sys_query,
            "session_id": session_id,
            "output_body": query_form.output_body if hasattr(query_form, "output_body") else "",
            "task_type": query_form.task_type,
            "temperature": query_form.temperature,
            "model_name": query_form.model_name,
            "config": config,
            "user": "admin",
            "conversation_history": query_form.conversation_history or [],
            "force_ocr": query_form.force_ocr
        }

        # 使用工作流处理请求
        return EventSourceResponse(two_phase_query_process(initial_state))
    except Exception as e:
        import traceback
        logger.error(f"Error processing chat conversation: {str(e)}")
        logger.error(traceback.format_exc())
        return ErrorResponse(message=f"处理请求时发生错误: {str(e)}")

# 修改会话文件管理API
@router.delete("/v1/session-files/{session_id}")
async def delete_session_files(session_id: str, delete_physical_files: bool = False):
    """删除指定会话ID关联的文件"""
    try:
        # 删除会话相关信息
        if delete_session_from_db(session_id, delete_physical_files):
            return JSONResponse(content={"message": f"会话 {session_id} 的数据已删除"})
        else:
            return ErrorResponse(message=f"删除会话 {session_id} 数据失败")
    except Exception as e:
        logger.error(f"Error deleting session files: {str(e)}")
        return ErrorResponse(message=f"删除会话文件时出错: {str(e)}")

@router.get("/v1/session-files/{session_id}")
async def get_session_files(session_id: str):
    """获取指定会话ID关联的文件信息"""
    try:
        # 获取会话信息
        session_info = get_session_info(session_id)

        if not session_info.get("exists", False):
            return ErrorResponse(message=f"会话 {session_id} 不存在或没有关联的文件")

        return JSONResponse(content={
            "session_id": session_id,
            "file_names": session_info.get("recent_files", []),
            "file_count": session_info.get("file_count", 0),
            "history_count": session_info.get("history_count", 0),
            "last_updated": session_info.get("last_updated", "")
        })
    except Exception as e:
        logger.error(f"Error getting session files: {str(e)}")
        return ErrorResponse(message=f"获取会话文件时出错: {str(e)}")

# 添加新的会话管理端点
@router.get("/v1/session/{session_id}")
async def get_session_details(session_id: str):
    """获取会话详细信息，包括历史记录"""
    try:
        # 获取会话基本信息
        session_info = get_session_info(session_id)

        if not session_info.get("exists", False):
            return ErrorResponse(message=f"会话 {session_id} 不存在")

        # 获取会话历史
        history = get_conversation_history_from_db(session_id)

        # 组合结果
        result = {
            "session_id": session_id,
            "file_names": session_info.get("recent_files", []),
            "file_count": session_info.get("file_count", 0),
            "created_at": session_info.get("created_at", ""),
            "last_updated": session_info.get("last_updated", ""),
            "conversation_history": history
        }

        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error getting session details: {str(e)}")
        return ErrorResponse(message=f"获取会话详情时出错: {str(e)}")

@router.post("/v1/session/cleanup")
async def cleanup_sessions(
        days: int = 7,
        background_tasks: BackgroundTasks = None,
        current_user: User = Depends(get_current_active_user)
):
    """
    清理指定天数前的会话数据（需要管理员权限）
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    # 在后台任务中执行清理操作
    if background_tasks:
        background_tasks.add_task(cleanup_old_sessions, days)
        return {"message": f"已启动清理任务，将删除 {days} 天前的会话数据"}
    else:
        # 直接执行清理
        count = cleanup_old_sessions(days)
        return {"message": f"已清理 {count} 个过期会话"}

@router.post("/v1/chat-messages", response_model=None)
async def query_documents_upload(
        query_form: DocumentQueryForm = Depends()
):
    """通过表单上传文件并查询文档"""
    # 获取最新配置
    config = get_config()

    # 验证输入
    is_valid, error_message = validate_inputs(
        query_form.file_names,
        query_form.files,
        query_form.kb_names,
        query_form.sys_query
    )
    if not is_valid:
        return ErrorResponse(message=error_message)

    # 使用前端传入的会话ID或创建新的会话ID
    session_id = query_form.conversation_history[0].get("session_id") if (
        query_form.conversation_history and
        len(query_form.conversation_history) > 0 and
        isinstance(query_form.conversation_history[0], dict) and
        "session_id" in query_form.conversation_history[0]
    ) else str(uuid.uuid4())

    try:
        # 保存上传的文件
        file_paths = await save_uploaded_files(query_form.files)


        # 准备初始状态，从动态配置获取默认值
        initial_state = {
            "file_names": query_form.file_names,
            "tags":query_form.tags,
            "file_paths": file_paths,
            "knowledge_base_type":query_form.knowledge_base_type,
            "kb_names": query_form.kb_names,
            "kb_token": query_form.kb_token,
            "top_k": query_form.top_k or config.DEFAULT_TOP_K,
            "top_n": query_form.top_n or config.DEFAULT_TOP_N,
            "key_weight": query_form.key_weight or config.DEFAULT_KEY_WEIGHT,
            "input_body": query_form.input_body,
            "system_prompt": query_form.system_prompt or config.DEFAULT_SYSTEM_PROMPT,
            "sys_query": query_form.sys_query,
            "session_id": session_id,
            "output_body": query_form.output_body,
            "task_type": query_form.task_type,
            "temperature": query_form.temperature,
            "model_name": query_form.model_name,  # 新增模型名称
            # 可以额外传入配置对象，让处理函数根据最新配置运行
            "config": config,
            # 添加用户信息
            "user": "admin",
            # 添加OCR控制参数
            "force_ocr": query_form.force_ocr
        }

        # 使用优化的两阶段处理
        return EventSourceResponse(two_phase_query_process(initial_state))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(message=f"处理请求时发生错误: {str(e)}")

@router.post("/v2/chat-messages", response_model=None)
async def query_documents_upload(
        query_form: DocumentQueryForm = Depends(),
        current_user: User = Depends(get_current_active_user)  # 添加用户认证
):
    """通过表单上传文件并查询文档"""
    # 获取最新配置
    config = get_config()

    # 验证输入
    is_valid, error_message = validate_inputs(
        query_form.file_names,
        query_form.files,
        query_form.kb_names,
        query_form.sys_query
    )
    if not is_valid:
        return ErrorResponse(message=error_message)

    # 使用前端传入的会话ID或创建新的会话ID
    session_id = query_form.conversation_history[0].get("session_id") if (
        query_form.conversation_history and
        len(query_form.conversation_history) > 0 and
        isinstance(query_form.conversation_history[0], dict) and
        "session_id" in query_form.conversation_history[0]
    ) else str(uuid.uuid4())

    try:
        # 保存上传的文件
        file_paths = await save_uploaded_files(query_form.files)

        # 准备初始状态，从动态配置获取默认值
        initial_state = {
            "file_names": query_form.file_names,
            "tags":query_form.tags,
            "file_paths": file_paths,
            "knowledge_base_type":query_form.knowledge_base_type,
            "kb_names": query_form.kb_names,
            "top_k": query_form.top_k or config.DEFAULT_TOP_K,
            "top_n": query_form.top_n or config.DEFAULT_TOP_N,
            "kb_token": query_form.kb_token,
            "key_weight": query_form.key_weight or config.DEFAULT_KEY_WEIGHT,
            "input_body": query_form.input_body,
            "system_prompt": query_form.system_prompt or config.DEFAULT_SYSTEM_PROMPT,
            "sys_query": query_form.sys_query,
            "session_id": session_id,
            "output_body": query_form.output_body,
            "task_type": query_form.task_type,
            "temperature": query_form.temperature,
            "model_name": query_form.model_name,  # 新增模型名称
            # 可以额外传入配置对象，让处理函数根据最新配置运行
            "config": config,
            # 添加用户信息
            "user": current_user.dict(),
            # 添加OCR控制参数
            "force_ocr": query_form.force_ocr
        }

        # 使用优化的两阶段处理
        return EventSourceResponse(two_phase_query_process(initial_state))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(message=f"处理请求时发生错误: {str(e)}")

