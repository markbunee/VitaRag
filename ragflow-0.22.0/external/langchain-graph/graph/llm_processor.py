"""
处理文档查询的工具函数，支持多文件流式处理
"""

from typing import Dict, Any, AsyncGenerator
from .base_processor import BaseProcessor
import uuid
async def two_phase_query_process(initial_state: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    使用事件流格式:
    - events: node_started/node_finished/message/error/complete
    - 流式输出统一使用 message 事件
    """
    if "session_id" not in initial_state or not initial_state["session_id"]:

        initial_state["session_id"] = str(uuid.uuid4())

    processor = BaseProcessor.create_processor(initial_state)

    # 执行处理流程
    async for event in processor.process():
        yield event
