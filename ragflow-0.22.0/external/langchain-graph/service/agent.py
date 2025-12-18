"""
摘要标签提取生成智能体接口
基于DSL工作流实现的智能体，用于文档的摘要和标签提取/生成
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from sse_starlette import EventSourceResponse

from api_process.input import SummaryExtractorForm, Convert2Json
from api_process.input import OAInvoiceValidateRawForm, OAInvoiceValidateForm
from config import get_config
from graph.llm_processor import two_phase_query_process
from service.auth_to import User, get_current_active_user
from utils.file_manager import save_uploaded_files_safely
from utils.stream_result_collector import StreamResultCollector
from utils.validators import validate_inputs
from api_process.output import ErrorResponse
from graph.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["其他智能体"])


class SummaryTagsExtractorAgent:
    """摘要标签提取生成智能体 - 使用graph节点流配置"""

    def __init__(self, config):
        self.config = config

    async def process_workflow(self, file_paths: List[str],kb_token:str = None, session_id: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """执行完整的工作流程 - 使用graph配置"""
        try:
            # 构建初始状态
            initial_state = {
                "file_paths": file_paths,
                "session_id": session_id or str(uuid.uuid4()),
                "kb_token":kb_token,
                "task_type": "summary_extract"  # 指定为摘要提取任务
            }

            # 创建处理器
            processor = BaseProcessor.create_processor(initial_state)

            # 执行处理流程
            async for event in processor.process():
                yield event

        except Exception as e:
            logger.error(f"工作流处理出错: {str(e)}")
            yield {
                "event": "error",
                "message": f"处理过程中出现错误: {str(e)}"
            }


@router.post("/summary-tags-extract")
async def extract_summary_tags(
    form: SummaryExtractorForm = Depends(),
    # current_user: User = Depends(get_current_active_user)
):
    """
    摘要标签提取生成接口
    支持上传文档文件，自动判断文档类型并提取或生成摘要和标签
    支持流式和非流式返回
    """
    config = get_config()

    # 验证文件
    if not form.files:
        return ErrorResponse(message="请上传至少一个文件")

    # 验证文件类型
    allowed_extensions = config.allowed_extensions
    for file in form.files:
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            return ErrorResponse(message=f"不支持的文件类型: {file.filename}")

    try:
        # 保存上传的文件
        file_paths = await save_uploaded_files_safely(form.files, form.session_id)

        if not file_paths:
            return ErrorResponse(message="文件保存失败")

        # 创建智能体实例
        agent = SummaryTagsExtractorAgent(config)

        if form.stream:
            # 流式返回
            return EventSourceResponse(agent.process_workflow(file_paths,form.kb_token, form.session_id))
        else:
            # 非流式返回，收集最终结果
            final_content = ""
            task_id = str(uuid.uuid4())
            message_id = str(uuid.uuid4())
            conversation_id = form.session_id

            async for event in agent.process_workflow(file_paths,form.kb_token, form.session_id):
                if event.get("event") == "message":
                    data_str = event.get("data", "{}")
                    try:
                        data = json.loads(data_str)
                        # 查找 final_message 事件
                        if data.get("events") == "final_message":
                            final_content = data.get("content", "")
                            break
                    except json.JSONDecodeError:
                        continue
                elif event.get("event") == "error":
                    return JSONResponse(
                        status_code=500,
                        content={"error": event.get("message", "处理失败")}
                    )
            logger.info(f"摘要结果：{final_content}")
            # 返回指定格式的响应
            return JSONResponse(content={
                "event": "message",
                "task_id": task_id,
                "id": message_id,
                "message_id": message_id,
                "conversation_id": conversation_id,
                "mode": "chat",
                "answer": final_content
            })

    except Exception as e:
        logger.error(f"处理摘要标签提取请求失败: {str(e)}")
        return ErrorResponse(message=f"处理请求失败: {str(e)}")

# 为了方便测试，添加一个简单的健康检查接口
@router.get("/health")
async def health_check():
    """健康检查接口"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "摘要标签提取生成智能体",
        "version": "2.0.0"  # 更新版本号表示使用graph配置
    })
@router.post("/oa-invoice-validate", response_model=None)
async def oa_invoice_validate(
    form: OAInvoiceValidateForm = Depends()
):
    """
    OA发票报销+知识库自动校验接口（支持流式和非流式返回）
    """
    try:
        config = get_config()
        detail_code = form.detail_code
        force_ocr = form.force_ocr
        stream = form.stream if hasattr(form, "stream") else True

        initial_state = {
            "detail_code": detail_code,
            "force_ocr": force_ocr,
            "config": config,
            "user": "admin",
            "task_type": "oa_invoice_validate",
            # 知识库检索参数
            "kb_names": form.kb_names if hasattr(form, "kb_names") else ["smartkb_76"],
            "kb_token": form.kb_token if hasattr(form, "kb_token") else config.TOKEN,
            "top_k": form.top_k if hasattr(form, "top_k") else config.DEFAULT_TOP_K,
            "top_n": form.top_n if hasattr(form, "top_n") else config.DEFAULT_TOP_N,
            "key_weight": form.key_weight if hasattr(form, "key_weight") else config.DEFAULT_KEY_WEIGHT,
            # 模型参数
            "model_name": form.model_name if hasattr(form, "model_name") else None,
            "temperature": form.temperature if hasattr(form, "temperature") else 0.1,
        }

        process = two_phase_query_process(initial_state)

        if stream:
            return EventSourceResponse(process)
        else:
            collector = StreamResultCollector()
            return await collector.collect(process)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(message=f"处理请求时发生错误: {str(e)}")

@router.post("/oa-invoice-validate-raw", response_model=None)
async def oa_invoice_validate_raw(
    form: OAInvoiceValidateRawForm = Depends()
):
    """
    从oa_data原始数据开始的OA发票校验接口（支持流式和非流式返回）
    """
    try:
        config = get_config()
        # 解析oa_data
        import json
        try:
            oa_data = form.oa_data
            if isinstance(oa_data, str):
                oa_data = json.loads(oa_data)
        except Exception as e:
            return ErrorResponse(message=f"oa_data参数不是合法的JSON字符串: {str(e)}")
        if not isinstance(oa_data, dict):
            return ErrorResponse(message="oa_data参数必须是字典或可转为字典的JSON字符串")

        initial_state = {
            "oa_data": oa_data,
            "config": config,
            "user": form.user,
            "task_type": "oa_invoice_validate_raw",
            "kb_names": form.kb_names if hasattr(form, "kb_names") else ["smartkb_76"],
            "kb_token": form.kb_token if hasattr(form, "kb_token") else config.TOKEN,
            "top_k": form.top_k if hasattr(form, "top_k") else config.DEFAULT_TOP_K,
            "top_n": form.top_n if hasattr(form, "top_n") else config.DEFAULT_TOP_N,
            "key_weight": form.key_weight if hasattr(form, "key_weight") else config.DEFAULT_KEY_WEIGHT,
            # 模型参数
            "model_name": form.model_name if hasattr(form, "model_name") else None,
            "temperature": form.temperature if hasattr(form, "temperature") else 0.1,
        }
        process = two_phase_query_process(initial_state)
        if form.stream:
            return EventSourceResponse(process)
        else:
            collector = StreamResultCollector()
            return await collector.collect(process)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ErrorResponse(message=f"处理请求时发生错误: {str(e)}")
