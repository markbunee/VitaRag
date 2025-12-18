"""
输入验证工具
"""
from typing import List, Optional, Tuple, Dict, Any
from fastapi import UploadFile
from config import get_config, logger
import os

def validate_inputs(
        file_names: List[str],
        tags: List[str],
        files: List[UploadFile],
        kb_names: List[str],
        sys_query: str
) -> Tuple[bool, Optional[str]]:
    """
    验证输入参数的有效性
    Args:
        file_names: 文件名列表
        files: 上传的文件列表
        kb_names: 知识库名称列表
        sys_query: 用户查询
    """
    config = get_config()
    allowed_extensions = config.allowed_extensions
    max_size = config.max_size
    # 验证查询不能为空
    if not sys_query or sys_query.strip() == "":
        return False, "用户查询不能为空"
    # 验证知识库名称不能为空（如果使用知识库查询）
    if file_names and not kb_names:
        return False, "使用知识库查询时，知识库名称不能为空"

    if file_names and tags:
        return False, f"file_names 和 tags 不能同时传入，必须二选一。当前传入的是file_names:{file_names}，tags:{tags}"

    # 验证文件类型
    if files:
        # 检查总文件大小
        total_size = 0

        for file in files:
            if file.filename:
                # 检查文件类型
                file_ext = os.path.splitext(file.filename)[1][1:].lower()
                if file_ext not in allowed_extensions:
                    return False, f"不支持的文件类型: {file_ext}，支持的类型有: {', '.join(allowed_extensions)}"

                # 计算总大小
                try:
                    # 获取文件大小
                    content = file.file.read()
                    total_size += len(content)
                    # 重置文件指针，以便后续操作可以重新读取文件
                    file.file.seek(0)
                except Exception as e:
                    return False, f"读取文件失败: {str(e)}"

        if total_size > max_size:
            return False, f"文件总大小超过15MB限制，当前大小: {total_size / 1024 / 1024:.2f}MB"

    return True, None

def validate_conversation_history(history: List[dict]) -> Tuple[bool, str]:
    """验证对话历史格式"""
    if not isinstance(history, list):
        return False, "对话历史必须是列表"

    valid_roles = {'user', 'assistant', 'system'}
    for i, msg in enumerate(history):
        if not isinstance(msg, dict):
            return False, f"第{i}条消息必须是字典"
        if msg.get('role') not in valid_roles:
            return False, f"第{i}条消息包含无效角色"
        if not isinstance(msg.get('content'), str):
            return False, f"第{i}条消息内容必须是字符串"

    return True, ""
