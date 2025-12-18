# graph/processors/event_emitter.py
import json
from typing import Dict, Any, Optional

class EventEmitter:
    """处理事件发送的工具类"""

    def __init__(self, conversion_id: str, session_id: str = ""):
        self.conversion_id = conversion_id
        self.session_id = session_id

    # 修改emit_event方法，添加session_id
    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送一个事件"""
        base_data = {
            "events": event_type,
            "conversion_id": self.conversion_id
        }

        # 如果有session_id，添加到事件数据中
        if self.session_id:
            base_data["session_id"] = self.session_id

        # 合并基础数据和传入的数据
        combined_data = {**base_data, **data}

        return {
            "event": "message",
            "data": json.dumps(combined_data)
        }
    async def emit_node_started(self, node: str, message: str, **kwargs) -> Dict[str, Any]:
        """发送节点开始事件"""
        return await self.emit_event("node_started", {"node": node, "message": message, **kwargs})

    async def emit_node_finished(self, node: str, message: str, **kwargs) -> Dict[str, Any]:
        """发送节点完成事件"""
        return await self.emit_event("node_finished", {"node": node, "message": message, **kwargs})

    async def emit_message(self, token: str, file: Optional[str] = None) -> Dict[str, Any]:
        """发送消息事件"""
        data = {"answer": token}
        if file:
            data["file"] = file
        return await self.emit_event("message", data)
    
    async def emit_final_message(self, content: str) -> Dict[str, Any]:
        """发送最终消息内容"""
        return await self.emit_event("final_message", {"content": content})

    async def emit_error(self, message: str, error_type: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """发送错误事件"""
        data = {"message": message, **kwargs}
        if error_type:
            data["error_type"] = error_type
        return await self.emit_event("error", data)

    async def emit_complete(self, message: str) -> Dict[str, Any]:
        """发送完成事件"""
        return await self.emit_event("complete", {"message": message})

    async def emit_documents_retrieved(self, file: str, documents: list) -> Dict[str, Any]:
        """发送文档检索完成事件"""
        return await self.emit_event("documents_retrieved", {
            "documents": documents
        })
    async def emit_origin_documents_retrieved(self, file: str, documents: list) -> Dict[str, Any]:
        """发送文档检索完成事件"""
        return await self.emit_event("origin_documents_retrieved", {
            "documents": documents
        })

    async def emit_node_progress(self, node: str, message: str, progress: float = 0.0, **kwargs) -> Dict[str, Any]:
        """发送节点进度更新事件"""
        return await self.emit_event("node_progress", {
            "node": node,
            "message": message,
            "progress": progress,
            **kwargs
        })
