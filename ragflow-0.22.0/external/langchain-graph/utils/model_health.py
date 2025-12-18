import asyncio
import hashlib
import os
import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path

import httpx

ROOT_PATH = Path(__file__).parent
DATA_DIR = os.path.join(ROOT_PATH, "data")
# 检查并创建 data 目录
os.makedirs(DATA_DIR, exist_ok=True)

CACHE_DB = os.path.join(DATA_DIR,"model_health_cache.db")
CACHE_EXPIRE_SECONDS = 300  # 5分钟

def _get_cache_conn():
    conn = sqlite3.connect(CACHE_DB)
    return conn

def _ensure_cache_table():
    with closing(_get_cache_conn()) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS model_health_cache (
            model_hash TEXT PRIMARY KEY,
            status INTEGER,
            ts INTEGER
        )
        """)
        conn.commit()

def _make_model_hash(model_config):
    s = f"{model_config['api_base_url'].rstrip('/')}_{model_config.get('api_key','')}"
    return hashlib.sha256(s.encode()).hexdigest()

def get_cached_health(model_config):
    _ensure_cache_table()
    model_hash = _make_model_hash(model_config)
    now = int(time.time())
    with closing(_get_cache_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT status, ts FROM model_health_cache WHERE model_hash=?", (model_hash,))
        row = c.fetchone()
        if row and now - row[1] < CACHE_EXPIRE_SECONDS:
            return bool(row[0])
        return None

def set_cached_health(model_config, status):
    _ensure_cache_table()
    model_hash = _make_model_hash(model_config)
    now = int(time.time())
    with closing(_get_cache_conn()) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO model_health_cache (model_hash,status,ts) VALUES (?,?,?)",
            (model_hash, int(status), now),
        )
        conn.commit()

async def check_model_health(model_config):
    """
    检查模型API健康状况，返回 bool。
    增加5分钟sqlite缓存
    """
    # 先查缓存
    cached = get_cached_health(model_config)
    if cached is not None:
        return cached

    url = model_config["api_base_url"].rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {model_config.get('api_key','')}"}
    timeout = httpx.Timeout(3.0)
    attempts = 2  # 尝试次数，1次原始+1次重试
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    set_cached_health(model_config, True)
                    return True
        except Exception:
            if attempt < attempts - 1:
                await asyncio.sleep(0.2)  # 可选: 重试等待时间
            continue
    set_cached_health(model_config, False)
    return False
