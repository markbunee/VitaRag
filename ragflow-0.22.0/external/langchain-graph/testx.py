import requests
import sseclient
import uuid
from concurrent.futures import ThreadPoolExecutor

def stream_sse_request(idx, url, form_data):
    # 给每个线程分配唯一 session_id
    session_id = str(uuid.uuid4())
    local_data = form_data.copy()
    local_data['session_id'] = session_id

    print(f"[Thread-{idx}] Start, session_id: {session_id}")

    # 用requests发POST请求获得SSE流
    resp = requests.post(url, data=local_data, stream=True)
    client = sseclient.SSEClient(resp)

    full_answer = ""
    final_answer_generation = False

    for event in client.events():
        if not event.data:
            continue
        try:
            data = event.data
            obj = None
            # 有些接口返回单独字符串，可以try-except
            try:
                obj = json.loads(data)
            except Exception:
                # 不是json就略过
                continue
            node = obj.get("node")
            message = obj.get("message", "")

            if node == "final_answer":
                final_answer_generation = True
                full_answer += f"\n\n✅Final_Answer Start (session_id={session_id})\n" + message
                print(f"[Thread-{idx}][{session_id}] FINAL_ANSWER: {message}")
            elif final_answer_generation:
                full_answer += message
            # 也可根据需要记录其它节点
        except Exception as e:
            print(f"[Thread-{idx}] Error parsing SSE: {e}, raw event: {event.data}")

    print(f"\n[Thread-{idx}] Done, session_id: {session_id}\nFull Output:\n{full_answer}\n{'='*60}")

if __name__ == "__main__":
    import json

    url = 'http://192.168.30.207:8116/api/v1/chat-conversation'
    # 注意：字符串需json序列化！
    form_data = {
        'sys_query': "董事长？",
        'kb_names': json.dumps(["smartkb_65", "smartkb_65_index"]),
        'top_k': "45",
        'top_n': "3",
        'key_weight': "0.8",
        'session_id': "",  # 该值执行时会自动填充
        'model_name': "qwen-14b",
    }

    work_num = 3  # 并发多少路

    with ThreadPoolExecutor(max_workers=work_num) as executor:
        futures = []
        for idx in range(work_num):
            fut = executor.submit(stream_sse_request, idx, url, form_data)
            futures.append(fut)
        for fut in futures:
            fut.result()  # 等待所有线程完成

    print("All done!")
