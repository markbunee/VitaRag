"""
文件管理工具，支持多进程安全的文件操作
"""
import os
import hashlib
import logging
import filelock
import shutil
import tempfile
from typing import List, Optional
from fastapi import UploadFile
import sys
# if sys.platform != "win32":
#     import fcntl
# else:
#     fcntl = None
logger = logging.getLogger(__name__)

def get_file_storage_path(session_id: str, filename: str) -> str:
    """
    获取文件存储路径，使用散列目录减少单目录文件数量

    Args:
        session_id: 会话ID
        filename: 文件名

    Returns:
        str: 完整的文件存储路径
    """
    # 使用会话ID的哈希值创建子目录，减少单目录文件数量
    h = hashlib.md5(session_id.encode()).hexdigest()
    subdirs = f"{h[:2]}/{h[2:4]}"  # 使用哈希前4位创建子目录

    # 构建目录路径
    from config import get_config
    config = get_config()
    TEMP_DIR_PATH = config.TEMP_DIR_PATH

    path = os.path.join(TEMP_DIR_PATH, subdirs, session_id)
    os.makedirs(path, exist_ok=True)

    # 替换文件名中的非法字符
    safe_filename = "".join([c if c.isalnum() or c in "._- " else "_" for c in filename])

    return os.path.join(path, safe_filename)

async def save_uploaded_files_safely(files: List[UploadFile], session_id: str) -> List[str]:
    if not files:
        return []
    file_paths = []
    for file in files:
        if not file.filename:
            continue
        file_path = get_file_storage_path(session_id, file.filename)
        temp_file_path = file_path + ".tmp"
        lock_path = temp_file_path + ".lock"

        try:
            lock = filelock.FileLock(lock_path)
            with lock:
                with open(temp_file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                    buffer.flush()
                    os.fsync(buffer.fileno())
            shutil.move(temp_file_path, file_path)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                file_paths.append(file_path)
                logger.info(f"Successfully saved file to {file_path}")
            else:
                logger.error(f"Failed to save file {file.filename}: File not found or empty")
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}")
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
    return file_paths

def cleanup_old_sessions(max_age_days: int = 7) -> int:
    """
    清理指定天数前的会话及其文件

    Args:
        max_age_days: 最大保留天数

    Returns:
        int: 清理的会话数量
    """
    from utils.db_manager import get_db_manager
    import time

    # 计算截止时间戳
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    cutoff_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(cutoff_time))

    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        try:
            cursor = conn.cursor()

            # 获取要删除的会话列表
            cursor.execute(
                "SELECT session_id FROM sessions WHERE datetime(last_updated) < datetime(?)",
                (cutoff_date,)
            )

            old_sessions = [row['session_id'] for row in cursor.fetchall()]
            deleted_count = 0

            # 逐个删除会话
            for session_id in old_sessions:
                from utils.db_manager import delete_session_from_db
                if delete_session_from_db(session_id, delete_files=True):
                    deleted_count += 1

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {str(e)}")
            return 0
