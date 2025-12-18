import datetime
import os
import tempfile
from typing import List

from config import logger, get_config
from utils.prompts.prompt import FINAL_RAG_PROMPT, FINAL_ANSWER_PROMPT
from fastapi import UploadFile


def system_prompt_to_parse(system_prompt):
    config = get_config()
    DEFAULT_SYSTEM_PROMPT = config.DEFAULT_SYSTEM_PROMPT
    if system_prompt == "" or system_prompt is None:
        system_prompt_to_use = DEFAULT_SYSTEM_PROMPT
    else:
        system_prompt_to_use = system_prompt
    if FINAL_RAG_PROMPT.strip() != "" and not None:
        system_prompt_to_use = FINAL_RAG_PROMPT
    return system_prompt_to_use

async def save_uploaded_files(files: List[UploadFile]) -> List[str]:
    """保存上传的文件到临时目录"""
    config = get_config()
    TEMP_DIR_PATH = config.TEMP_DIR_PATH

    # 创建指定目录或临时目录
    if TEMP_DIR_PATH:
        temp_dir = TEMP_DIR_PATH
        os.makedirs(temp_dir, exist_ok=True)
    else:
        temp_dir = tempfile.mkdtemp()

    file_paths = []

    for file in files:
        if not file.filename:  # 跳过空文件
            continue

        file_path = os.path.join(temp_dir, file.filename)

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 读取文件内容 - 使用缓冲区逐块读取避免占用过多内存
            with open(file_path, "wb") as buffer:
                # 重要修改：不要使用 file.file，而是直接使用 file 对象
                content = await file.read()
                buffer.write(content)

            # 验证文件是否成功写入
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_paths.append(file_path)
            else:
                logger.error(f"Failed to save file {file.filename}: File not found or empty")

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")

    return file_paths
