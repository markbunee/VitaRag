"""
数据库管理工具，使用SQLite存储会话信息和文件路径
支持多进程并发访问
"""
import os
import json
import sqlite3
import time
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
import contextlib
from functools import lru_cache

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sessions.db")

class DBManager:
    def __init__(self, max_connections=5):
        """初始化数据库管理器"""
        # 确保data目录存在
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.max_connections = max_connections
        self.connections = []

    @contextlib.contextmanager
    def get_connection(self):
        """获取数据库连接，使用上下文管理器模式"""
        conn = None
        new_conn = False

        try:
            # 尝试获取现有连接或创建新连接
            if self.connections:
                conn = self.connections.pop()
            else:
                # 创建新连接并启用WAL模式以提高并发性能
                conn = sqlite3.connect(
                    f"file:{DB_PATH}?mode=rwc",
                    uri=True,
                    timeout=30.0,  # 增加超时时间，减少锁等待错误
                    isolation_level=None  # 启用自动提交模式，使得PRAGMA生效
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")  # 写前日志模式，提高并发性能
                conn.execute("PRAGMA synchronous=NORMAL")  # 降低同步级别，提高性能
                conn.execute("PRAGMA busy_timeout=10000")  # 设置忙等待超时（10秒）
                conn.isolation_level = "IMMEDIATE"  # 恢复事务控制，默认使用立即事务

                # 确保表已创建
                self._create_tables(conn)
                new_conn = True

            yield conn

            # 检查连接是否仍然可用
            try:
                conn.execute("SELECT 1")  # 简单测试连接是否有效
                # 将连接放回池中（如果池未满）
                if len(self.connections) < self.max_connections:
                    self.connections.append(conn)
                    conn = None  # 防止连接被关闭
                else:
                    # 池已满，关闭连接
                    conn.close()
                    conn = None
            except sqlite3.Error:
                # 连接出现问题，关闭它
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                conn = None
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            # 确保不返回池的连接被关闭
            if conn is not None:
                try:
                    conn.close()
                except:
                    pass

    def _create_tables(self, conn):
        """创建必要的数据库表"""
        cursor = conn.cursor()

        # 会话表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            version INTEGER DEFAULT 1
        )
        ''')

        # 会话文件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            file_path TEXT,
            file_name TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')

        # 会话历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_order INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
        ''')

        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_files_session_id ON session_files (session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_history_session_id ON conversation_history (session_id)')

        conn.commit()

@lru_cache(maxsize=1)
def get_db_manager():
    """获取数据库管理器（每个进程缓存一个实例）"""
    return DBManager(max_connections=5)  # 每个进程最多5个连接

def save_session_files_to_db(session_id: str, file_paths: List[str], file_names: List[str]) -> bool:
    """
    保存会话关联的文件信息到数据库

    Args:
        session_id: 会话ID
        file_paths: 文件物理路径列表
        file_names: 文件名列表（用于文件索引或显示）

    Returns:
        bool: 操作是否成功
    """
    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        try:
            cursor = conn.cursor()

            # 多进程安全：使用事务
            conn.execute("BEGIN IMMEDIATE")

            # 确保会话存在
            cursor.execute(
                "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
                (session_id,)
            )

            # 添加文件记录
            for i, file_path in enumerate(file_paths):
                # 如果有对应的file_name则使用，否则使用文件路径的文件名部分
                file_name = file_names[i] if i < len(file_names) else os.path.basename(file_path)

                cursor.execute(
                    "INSERT INTO session_files (session_id, file_path, file_name) VALUES (?, ?, ?)",
                    (session_id, file_path, file_name)
                )

            # 更新会话最后活动时间和版本号（乐观锁）
            cursor.execute(
                "UPDATE sessions SET last_updated = CURRENT_TIMESTAMP, version = version + 1 WHERE session_id = ?",
                (session_id,)
            )

            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to save session files: {str(e)}")
            return False

def get_session_files_from_db(session_id: str) -> List[str]:
    """
    从数据库获取会话关联的所有文件路径

    Args:
        session_id: 会话ID

    Returns:
        List[str]: 文件路径列表
    """
    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # 使用只读事务提高性能
        conn.execute("BEGIN")

        try:
            cursor.execute(
                "SELECT file_path FROM session_files WHERE session_id = ?",
                (session_id,)
            )

            results = cursor.fetchall()
            file_paths = [row['file_path'] for row in results]

            conn.commit()
            return file_paths
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to get session files: {str(e)}")
            return []

def save_conversation_history_to_db(session_id: str, conversation_history: List[Dict[str, Any]]) -> bool:
    """
    保存会话历史到数据库

    Args:
        session_id: 会话ID
        conversation_history: 会话历史列表

    Returns:
        bool: 操作是否成功
    """
    if not conversation_history:
        return True

    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        try:
            cursor = conn.cursor()

            # 获取事务锁
            conn.execute("BEGIN IMMEDIATE")

            # 确保会话存在
            cursor.execute(
                "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
                (session_id,)
            )

            # 获取当前消息数量（用于排序）
            cursor.execute(
                "SELECT COUNT(*) as count FROM conversation_history WHERE session_id = ?",
                (session_id,)
            )
            count = cursor.fetchone()['count']

            # 添加历史记录
            for i, message in enumerate(conversation_history):
                if isinstance(message, dict) and 'role' in message and 'content' in message:
                    # 跳过可能的重复消息（通过查询相似消息）
                    cursor.execute(
                        """SELECT id FROM conversation_history 
                           WHERE session_id = ? AND role = ? AND content = ? 
                           LIMIT 1""",
                        (session_id, message['role'], message['content'])
                    )
                    if cursor.fetchone() is None:  # 只有不存在时才插入
                        cursor.execute(
                            """INSERT INTO conversation_history 
                               (session_id, role, content, message_order) 
                               VALUES (?, ?, ?, ?)""",
                            (session_id, message['role'], message['content'], count + i)
                        )

            # 更新会话最后活动时间和版本号
            cursor.execute(
                "UPDATE sessions SET last_updated = CURRENT_TIMESTAMP, version = version + 1 WHERE session_id = ?",
                (session_id,)
            )

            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to save conversation history: {str(e)}")
            return False

def get_conversation_history_from_db(session_id: str) -> List[Dict[str, Any]]:
    """
    从数据库获取会话历史

    Args:
        session_id: 会话ID

    Returns:
        List[Dict]: 会话历史列表
    """
    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # 使用只读事务提高性能
        conn.execute("BEGIN")

        try:
            cursor.execute(
                """SELECT role, content FROM conversation_history 
                   WHERE session_id = ? ORDER BY message_order, timestamp""",
                (session_id,)
            )

            results = cursor.fetchall()
            history = [{'role': row['role'], 'content': row['content']} for row in results]

            conn.commit()
            return history
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []

def delete_session_from_db(session_id: str, delete_files: bool = False) -> bool:
    """
    从数据库删除会话及相关信息

    Args:
        session_id: 会话ID
        delete_files: 是否删除物理文件

    Returns:
        bool: 操作是否成功
    """
    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        try:
            cursor = conn.cursor()

            # 获取独占锁
            conn.execute("BEGIN IMMEDIATE")

            # 如果需要删除物理文件
            if delete_files:
                cursor.execute(
                    "SELECT file_path FROM session_files WHERE session_id = ?",
                    (session_id,)
                )
                file_paths = [row['file_path'] for row in cursor.fetchall()]

                # 删除物理文件
                for file_path in file_paths:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"Deleted file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {file_path}: {str(e)}")

            # 删除数据库记录
            cursor.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM session_files WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to delete session: {str(e)}")
            return False

def get_session_info(session_id: str) -> Dict[str, Any]:
    """
    获取会话基本信息

    Args:
        session_id: 会话ID

    Returns:
        Dict: 会话信息，包含文件列表和会话历史条数
    """
    db_manager = get_db_manager()
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # 使用只读事务
        conn.execute("BEGIN")

        try:
            # 获取会话信息
            cursor.execute(
                "SELECT created_at, last_updated, version FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            session = cursor.fetchone()
            if not session:
                conn.rollback()
                return {"exists": False}

            # 获取文件信息
            cursor.execute(
                "SELECT COUNT(*) as file_count FROM session_files WHERE session_id = ?",
                (session_id,)
            )
            file_count = cursor.fetchone()['file_count']

            # 获取最新的文件名列表
            cursor.execute(
                "SELECT file_name FROM session_files WHERE session_id = ? ORDER BY uploaded_at DESC LIMIT 10",
                (session_id,)
            )
            file_names = [row['file_name'] for row in cursor.fetchall()]

            # 获取会话历史条数
            cursor.execute(
                "SELECT COUNT(*) as history_count FROM conversation_history WHERE session_id = ?",
                (session_id,)
            )
            history_count = cursor.fetchone()['history_count']

            conn.commit()

            return {
                "exists": True,
                "session_id": session_id,
                "created_at": session['created_at'],
                "last_updated": session['last_updated'],
                "version": session['version'],
                "file_count": file_count,
                "recent_files": file_names,
                "history_count": history_count
            }
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to get session info: {str(e)}")
            return {"exists": False, "error": str(e)}
