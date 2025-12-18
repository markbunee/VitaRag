import asyncio
import threading
import queue
import time
import json

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse # 需安装：pip install sse-starlette

app = FastAPI()

# --- 模拟搜索函数 ---
def search_source_one(query_part: str, output_queue: queue.Queue):
    """模拟数据源1的搜索过程"""
    output_queue.put({"source": "数据源1", "status": "启动", "query_part": query_part})
    for i in range(5):
        time.sleep(0.5) # 模拟耗时操作
        result = f"数据源1关于'{query_part}'的第{i+1}条结果"
        output_queue.put({"source": "数据源1", "data": result})
    output_queue.put({"source": "数据源1", "status": "完成"})
    output_queue.put(None) # 发送终止信号

def search_source_two(query_part: str, output_queue: queue.Queue):
    """模拟数据源2的搜索过程"""
    output_queue.put({"source": "数据源2", "status": "启动", "query_part": query_part})
    for i in range(3):
        time.sleep(0.8) # 模拟耗时操作
        result = f"数据源2关于'{query_part}'的第{i+1}条结果"
        output_queue.put({"source": "数据源2", "data": result})
    output_queue.put({"source": "数据源2", "status": "完成"})
    output_queue.put(None)

def search_source_three(query_part: str, output_queue: queue.Queue):
    """模拟快速数据源3"""
    output_queue.put({"source": "数据源3", "status": "启动", "query_part": query_part})
    time.sleep(0.3)
    output_queue.put({"source": "数据源3", "data": f"数据源3快速响应：'{query_part}'"})
    output_queue.put({"source": "数据源3", "status": "完成"})
    output_queue.put(None)

@app.post("/ask_streaming")
async def ask_streaming(request: Request):
    # 实际应用中应从请求获取用户问题
    user_query = "请讲解Python并发和Web框架"

    # 1. 问题拆解（示例）
    decomposed_queries = {
        "concurrency": "Python并发模型",
        "frameworks": "Python Web框架对比",
        "fast_check": "Python快速问答"
    }

    # 2. 为每个数据源创建队列
    queues = {
        "source_one": queue.Queue(),
        "source_two": queue.Queue(),
        "source_three": queue.Queue(),
    }

    # 3. 定义搜索任务
    search_tasks = [
        (search_source_one, decomposed_queries["concurrency"], queues["source_one"]),
        (search_source_two, decomposed_queries["frameworks"], queues["source_two"]),
        (search_source_three, decomposed_queries["fast_check"], queues["source_three"]),
    ]

    # 启动所有线程
    threads = []
    for func, query_part, q in search_tasks:
        thread = threading.Thread(target=func, args=(query_part, q))
        threads.append(thread)
        thread.start()

    async def event_generator():
        active_queues = list(queues.values())
        completed_count = 0
        try:
            while completed_count < len(active_queues):
                for q in list(active_queues):
                    try:
                        item = q.get_nowait()
                        if item is None: # 收到终止信号
                            completed_count += 1
                            active_queues.remove(q)
                            continue
                        # 生成SSE事件
                        yield {
                            "event": "message",
                            "id": f"msg_{time.time()}",
                            "retry": 3000,
                            "data": json.dumps(item)
                        }
                    except queue.Empty:
                        continue
                await asyncio.sleep(0.1) # 避免CPU空转

            # 所有数据源处理完成
            yield {
                "event": "close",
                "data": json.dumps({"message": "所有数据源处理完毕"})
            }
        except asyncio.CancelledError:
            print("客户端断开连接")
            raise
        finally:
            for t in threads:
                if t.is_alive():
                    print(f"线程{t.name}仍在运行")

    return EventSourceResponse(event_generator())

# 运行方式：
# 1. pip install fastapi uvicorn sse-starlette
# 2. uvicorn 文件名:app --reload
# 测试接口：POST http://127.0.0.1:9000/ask_streaming
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
