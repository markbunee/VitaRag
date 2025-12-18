import asyncio
import datetime
import json
import re
import uuid
from typing import Dict, Any, List, AsyncGenerator, Optional
from config import logger, get_config
from utils.api_client import extract_document_content, query_knowledge_base
from graph.event_emitter import EventEmitter
from graph.processors.response_generator import ResponseGenerator
# from utils.tools import get_origin_contents


class ProcessingComponent:
    """处理流程的基础组件"""
    def __init__(self, state: Dict[str, Any], emitter: EventEmitter):
        self.state = state
        self.emitter = emitter
        self.config = get_config()

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行组件的处理逻辑"""
        raise NotImplementedError("子类必须实现此方法")

class FileExtractionComponent(ProcessingComponent):
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            sys_query = self.state.get("sys_query", "")
            yield await self.emitter.emit_node_started("query_enhancement", "正在优化查询...")
            response_generator = ResponseGenerator()
            conversation_history = self.state.get("conversation_history", None)
            final_answer = ""
            yield await self.emitter.emit_message('\n```问题增强中...\n\n')
            async for token in response_generator.generate_enhanced_query(sys_query, conversation_history):
                final_answer += token
                yield await self.emitter.emit_message(token)
                await asyncio.sleep(0.005)
            yield await self.emitter.emit_message('\n\n```\n\n')
            self.state["enhanced_query"] = final_answer

            yield await self.emitter.emit_node_finished(
                "query_enhancement",
                f"查询已优化为: {final_answer}"
            )
        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            yield await self.emitter.emit_error(error_msg)
