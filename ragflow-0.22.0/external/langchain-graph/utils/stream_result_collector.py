"""
流式结果收集器
用于将流式处理的结果收集起来，返回非流式响应
"""

import json
import uuid
import logging
from typing import Dict, Any, AsyncGenerator
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class StreamResultCollector:
    """流式结果收集器，用于非流式返回"""
    
    def __init__(self):
        self.final_content = ""
        self.task_id = str(uuid.uuid4())
        self.message_id = str(uuid.uuid4())
        self.conversation_id = None
        self.error_message = None
        
    async def collect(self, process_generator: AsyncGenerator[Dict[str, Any], None]) -> JSONResponse:
        """
        收集流式处理的结果
        
        Args:
            process_generator: 流式处理生成器
            
        Returns:
            JSONResponse: 包含最终结果的JSON响应
        """
        try:
            async for event in process_generator:
                if event.get("event") == "message":
                    data_str = event.get("data", "{}")
                    try:
                        data = json.loads(data_str)
                        # 查找 final_message 事件
                        if data.get("events") == "final_message":
                            self.final_content = data.get("content", "")
                            break
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，直接使用原始数据
                        if isinstance(data_str, str) and data_str.strip():
                            self.final_content = data_str
                            break
                        continue
                elif event.get("event") == "error":
                    self.error_message = event.get("message", "处理失败")
                    return JSONResponse(
                        status_code=500,
                        content={"error": self.error_message}
                    )
                elif event.get("event") == "complete":
                    # 处理完成事件
                    break
                    
            logger.info(f"收集到的最终结果：{self.final_content}")
            
            # 返回指定格式的响应
            return JSONResponse(content={
                "event": "message",
                "task_id": self.task_id,
                "id": self.message_id,
                "message_id": self.message_id,
                "conversation_id": self.conversation_id or str(uuid.uuid4()),
                "mode": "chat",
                "answer": self.final_content
            })
            
        except Exception as e:
            logger.error(f"收集流式结果时出错: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"处理过程中出现错误: {str(e)}"}
            )
