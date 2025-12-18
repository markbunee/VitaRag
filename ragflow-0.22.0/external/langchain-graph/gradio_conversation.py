import gradio as gr
import requests
import json
import time
import os
import uuid

from service.chat_api import logger


def get_available_models():
    """获取可用的模型列表"""
    try:
        response = requests.get("http://127.0.0.1:8116/api/v1/models")
        if response.status_code == 200:
            data = response.json()
            return data.get("llm_model_names", ["qwen-14b"])  # 默认返回qwen-14b
        else:
            logger.info(f"获取模型列表失败: {response.status_code}")
            return ["qwen-14b"]
    except Exception as e:
        logger.info(f"获取模型列表出错: {str(e)}")
        return ["qwen-14b"]

def query_api(session_id, conversation_history, sys_query, uploaded_files, file_names, kb_names, kb_token,
              top_k, top_n, key_weight, system_prompt, input_body, output_body,
              temperature, model_name, task_type, force_ocr=False,kb_type = "ufrag"):
    """向API发送请求并处理流式响应"""
    url = "http://127.0.0.1:8116/api/v1/chat-conversation"  # 注意使用新的端点
    headers = {"accept": "text/event-stream"}
    # 如果没有会话ID，创建一个新的
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"创建新会话: {session_id}")
    # 将kb_names和file_names转换为JSON字符串列表
    kb_names_list = [name.strip() for name in kb_names.split(",") if name.strip()]
    file_names_list = [name.strip() for name in file_names.split(",") if name.strip()]
    # 更新对话历史
    if not conversation_history:
        conversation_history = []
    # 添加当前用户消息到历史
    # conversation_history.append({
    #     "role": "user",
    #     "content": sys_query,
    #     "session_id": session_id
    # })
    # 准备表单数据
    data = {
        "sys_query": sys_query,
        "file_names": json.dumps(file_names_list),
        "knowledge_base_type":kb_type,
        "kb_names": json.dumps(kb_names_list),
        "top_k": top_k,
        "top_n": top_n,
        "key_weight": key_weight,
        "kb_token":kb_token,
        "system_prompt": system_prompt,
        "input_body": input_body,
        "output_body": output_body,
        "temperature": temperature,
        "model_name": model_name,
        "task_type": task_type,
        "session_id": session_id,
        "conversation_history": json.dumps(conversation_history),
        "force_ocr": str(force_ocr)
    }
    # 准备文件
    file_objects = []
    try:
        files = []
        if uploaded_files:
            for file_path in uploaded_files:
                file_name = os.path.basename(file_path.name)
                # 打开文件并保存文件对象以便之后关闭
                file_obj = open(file_path.name, "rb")
                file_objects.append(file_obj)
                files.append(("files", (file_name, file_obj, "application/octet-stream")))
        response = requests.post(url, headers=headers, data=data, files=files, stream=True)
        # 检查响应状态
        if response.status_code != 200:
            return session_id, conversation_history, f"Error: Server returned status code {response.status_code}"
        full_answer = ""
        current_file = None
        file_processing = False
        summary_generation = False
        final_answer_generation = False
        final_answer = ""
        json_conversion = False
        # 使用yield来实现流式输出
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data:'):
                    try:
                        event_data = json.loads(line[5:].strip())
                        event_type = event_data.get("events")
                        # 处理不同类型的事件
                        if event_type == "node_started":
                            node_name = event_data.get("node")
                            message = event_data.get("message", "")
                            # 添加事件起始标记和换行
                            if node_name == "query_enhancement":
                                full_answer += "\n\n🚀\n" + message  # 替换【查询优化开始】
                            elif node_name == "multi_file_processing":
                                full_answer += "\n\n📂\n" + message  # 替换【多文件处理开始】
                            elif node_name == "file_processing":
                                file_name = event_data.get("file", "未知文件")
                                current_file = file_name
                                file_processing = True
                                full_answer += f"\n\n📄 {file_name}\n" + message  # 替换【开始处理文件: {file_name}】
                            elif node_name == "summary_generation":
                                file_name = event_data.get("file", "未知文件")
                                current_file = file_name
                                summary_generation = True
                                full_answer += f"\n\n📝 {file_name}\n" + message  # 替换【开始生成摘要: {file_name}】
                            elif node_name == "final_answer":
                                final_answer_generation = True
                                full_answer += "\n\n✅\n" + message  # 替换【开始生成最终回答】
                            elif node_name == "convert_to_json":
                                json_conversion = True
                                full_answer += "\n\n🔄\n" + message  # 替换【开始转换为JSON】
                            yield session_id, conversation_history, full_answer, final_answer
                        elif event_type == "node_finished":
                            node_name = event_data.get("node")
                            message = event_data.get("message", "")
                            completed = event_data.get("completed", "")
                            # 添加事件结束标记和换行
                            if node_name == "query_enhancement":
                                full_answer += "\n🚀完成\n" + message  # 替换【查询优化完成】
                            elif node_name == "multi_file_processing":
                                full_answer += "\n📂完成\n" + message  # 替换【多文件处理完成】
                            elif node_name == "file_processing":
                                file_processing = False
                                full_answer += "\n📄处理完成\n" + message  # 替换【文件处理完成】
                            elif node_name == "summary_generation":
                                summary_generation = False
                                full_answer += "\n📝生成完成\n" + message  # 替换【摘要生成完成】
                            elif node_name == "final_answer":
                                final_answer_generation = False
                                full_answer += "\n✅生成完成\n" + message  # 替换【最终回答生成完成】
                                # 将完整的回答添加到对话历史
                                if completed:
                                    final_answer = completed
                                # yield session_id, conversation_history, full_answer
                            elif node_name == "convert_to_json":
                                json_conversion = False
                                full_answer += "\n🔄转换完成\n" + message  # 替换【JSON转换完成】
                            yield session_id, conversation_history, full_answer, final_answer
                        elif event_type == "node_progress":
                            node_name = event_data.get("node", "")
                            message = event_data.get("message", "")
                            progress = event_data.get("progress", 0.0)
                            full_answer += f"\n【进度更新 - {node_name}】: {message}（进度: {progress:.1f}%）"
                            yield session_id, conversation_history, full_answer, final_answer
                        elif event_type == "documents_retrieved":
                            file_name = event_data.get("file", "未知文件")
                            full_answer += f"\n【已检索文件: {file_name}】\n"
                            # 可以添加文档详情如果需要
                            docs = event_data.get("documents", [])
                            if docs:
                                full_answer += f"检索到 {len(docs)} 个文档片段\n"
                            yield session_id, conversation_history, full_answer, final_answer
                        elif event_type == "message":
                            if "answer" in event_data:
                                token = event_data["answer"]
                                file_name = event_data.get("file", "")
                                # 根据当前处理阶段添加标记
                                if file_name and file_name != current_file and summary_generation:
                                    current_file = file_name
                                    full_answer += f"\n【文件摘要: {file_name}】\n"
                                full_answer += token
                                yield session_id, conversation_history, full_answer, final_answer
                                time.sleep(0.01)  # 短暂暂停以允许UI更新
                        elif event_type == "error":
                            full_answer += f"\n\n【错误】\n{event_data.get('message', 'Unknown error')}"
                            yield session_id, conversation_history, full_answer, final_answer
                        elif event_type == "complete":
                            full_answer += "\n\n【处理完成】"
                            yield session_id, conversation_history, full_answer, final_answer
                    except json.JSONDecodeError:
                        full_answer += f"\n\n【错误】\nInvalid JSON response: {line[5:].strip()}"
                        yield session_id, conversation_history, full_answer, final_answer
    finally:
        # 确保所有文件都被关闭
        for file_obj in file_objects:
            try:
                file_obj.close()
            except:
                pass

# 格式化对话历史为可读文本
def format_conversation(conversation_history):
    if not conversation_history:
        return ""

    formatted_text = ""
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            formatted_text += f"🧑 用户: {content}\n\n"
        elif role == "assistant":
            formatted_text += f"🤖 助手: {content}\n\n"
        elif role == "system":
            formatted_text += f"🔧 系统: {content}\n\n"

    return formatted_text

# 全局状态变量，用于控制生成过程
stop_generation = gr.State(False)

# 重试功能 - 重新发送上一条用户消息
def retry_last_query(session_id, conversation_history, uploaded_files, file_names, kb_names, kb_token, top_k, top_n, key_weight, system_prompt, input_body, output_body, temperature, model_name, task_type, max_turns, force_ocr):
    # 重置停止标志
    stop_flag = False

    # 确保有对话历史
    if not conversation_history:
        return session_id, conversation_history, [], "", stop_flag

    # 找到最后一条用户消息
    last_user_msg = None
    for msg in reversed(conversation_history):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    if not last_user_msg:
        return session_id, conversation_history, [], "", stop_flag

    # 如果最后一条是助手消息，则移除它
    if conversation_history and conversation_history[-1]["role"] == "assistant":
        conversation_history = conversation_history[:-1]

    # 重新生成响应
    for result in submit_query(
            session_id, conversation_history, last_user_msg, uploaded_files,
            file_names, kb_names, kb_token, top_k, top_n, key_weight,
            system_prompt, input_body, output_body, temperature,
            model_name, task_type, max_turns, force_ocr,None
    ):
        yield result

# 停止生成
def stop_generation_fn():
    return True

# 重置停止标志
def reset_stop_flag():
    return False

css = """
#user_input {margin-right: 5px !important;}
.compact-btn {min-width: 20px !important; padding: 0 5px !important;}
"""
with gr.Blocks(theme=gr.themes.Base(),css=css) as demo:
    gr.Markdown("# deepseek代理 - 多轮对话版本")
    # 存储会话状态
    session_id = gr.State("")
    conversation_history = gr.State([])
    with gr.Row():
        with gr.Column(scale=3):
            # 统一的聊天界面 - 使用Chatbot组件替代分开的文本框
            chatbot = gr.Chatbot(
                label="对话界面",
                height=500,
                elem_id="chatbox"
            )
            # 用户输入区域
            with gr.Row(equal_height=True):
                sys_query = gr.Textbox(
                    label="用户输入",
                    placeholder="请输入您的问题...",
                    lines=2,
                    max_lines=5,
                    scale=5,
                    container=False,
                    elem_id="user_input"
                )
                with gr.Column(scale=1, min_width=150, elem_id="chat_controls"):
                    submit_btn = gr.Button("发送", variant="primary", size="sm")
                    with gr.Row():
                        retry_btn = gr.Button("↻", variant="secondary", size="sm",
                                              elem_classes="compact-btn")
                        stop_btn = gr.Button("■", variant="stop", size="sm",
                                             elem_classes="compact-btn")
        with gr.Column(scale=2):
            # 系统设置
            with gr.Accordion("系统设置", open=False):
                system_prompt = gr.Textbox(
                    label="系统提示词",
                    placeholder="可选系统提示词...",
                    lines=3,
                    value="从提供的内容总结后的文档中获取相应的知识来准确回答用户的问题或者完成用户的需求\n如果使用原文档输出，需要注意输出格式的规整和视觉的美观，优先整理为表格等形式使得输出的结果美观。\n如果未提供相应的文档，或者提供的文档内容为空，请回答未找到答案，并回答为什么。"
                )
                # 获取可用模型列表
                available_models = get_available_models()
                model_name = gr.Dropdown(
                    choices=available_models,
                    value=available_models[0] if available_models else "qwen-14b",
                    label="选择模型"
                )
                temperature = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.1,
                    step=0.1,
                    label="温度"
                )
                # 新增：对话轮数控制
                max_turns = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label="最大对话轮数"
                )
                task_type = gr.Dropdown(
                    choices=["default", "sql","oa_invoice_validate","oa_invoice_validate_raw","summary_extract","uav_weather_assistant"],
                    value="default",
                    label="任务类型"
                )
                # 会话管理按钮
                with gr.Row():
                    new_chat_btn = gr.Button("新对话", variant="secondary")
                    clear_history_btn = gr.Button("清空历史", variant="secondary")
            # 知识库配置
            with gr.Accordion("知识库配置", open=True):
                # 新增：知识库类型选择
                kb_type = gr.Radio(
                    choices=["ufrag", "ragflow"],
                    value="ragflow",
                    label="知识库类型"
                )
                kb_names = gr.Textbox(
                    label="知识库名称",
                    placeholder="输入知识库名称，多个用逗号分隔",
                    value="nianbaomix00,nianbaomix00_index"
                )
                kb_token = gr.Textbox(
                    label="知识库Token",
                    placeholder="输入知识库访问token（可选）",
                    value=""
                )
                file_names = gr.Textbox(
                    label="文件名称",
                    placeholder="输入文件名称，多个用逗号分隔",
                    value="创举科技：2024年半年度报告.PDF,长亮科技：2024年半年度报告.PDF"
                )
                uploaded_files = gr.File(
                    label="上传文件",
                    file_count="multiple"
                )
                force_ocr = gr.Checkbox(
                    label="强制OCR处理",
                    value=False,
                    info="启用OCR处理上传的文件"
                )
            # 检索参数
            with gr.Accordion("检索参数", open=False):
                top_k = gr.Slider(
                    minimum=1,
                    maximum=55,
                    value=45,
                    step=1,
                    label="Top K"
                )
                top_n = gr.Slider(
                    minimum=1,
                    maximum=7,
                    value=3,
                    step=1,
                    label="Top N"
                )
                key_weight = gr.Slider(
                    minimum=0,
                    maximum=1,
                    value=0.8,
                    step=0.1,
                    label="关键词权重"
                )
            # 额外数据配置
            with gr.Accordion("额外数据配置", open=False):
                input_body = gr.Textbox(
                    label="数据资产api接口数据",
                    value="default",
                    placeholder="输入体格式..."
                )
                output_format = gr.Textbox(
                    label="输出体格式 (JSON)",
                    placeholder='',
                    lines=2,
                    value=""
                )
    # 创建新对话
    def create_new_chat():
        return str(uuid.uuid4()), [], [], None
    # 清空历史但保留会话ID
    def clear_chat_history(session_id):
        return session_id, [], [], None
    # 处理用户查询并截断历史以保持在最大轮数内
    # 更新聊天界面
    def update_chatbot(conversation):
        # 转换conversation_history为chatbot格式 [(user, assistant), ...]
        chatbot_pairs = []
        i = 0
        while i < len(conversation):
            if conversation[i]['role'] == 'user':
                user_msg = conversation[i]['content']
                # 查找下一个助手消息
                j = i + 1
                while j < len(conversation) and conversation[j]['role'] != 'assistant':
                    j += 1
                # 如果找到助手消息，则添加对话对
                if j < len(conversation) and conversation[j]['role'] == 'assistant':
                    assistant_msg = conversation[j]['content']
                    chatbot_pairs.append([user_msg, assistant_msg])
                    i = j + 1  # 跳过已处理的助手消息
                else:
                    # 如果没有找到助手消息，添加只有用户消息的对话对
                    chatbot_pairs.append([user_msg, None])
                    i += 1
            else:
                # 跳过非用户消息
                i += 1
        return chatbot_pairs
    # 处理用户查询和构建响应
    def submit_query(session_id, conversation_history, query, uploaded_files, file_names, kb_names, kb_token, top_k, top_n, key_weight, system_prompt, input_body, output_body, temperature, model_name, task_type, max_turns, force_ocr, kb_type):
        # 将用户查询添加到对话历史
        updated_conversation = conversation_history.copy()
        if not updated_conversation or updated_conversation[-1]['role'] != 'user' or updated_conversation[-1]['content'] != query:
            updated_conversation.append({"role": "user", "content": query})
        # 更新Chatbot显示（只有用户消息）
        chatbot_display = update_chatbot(updated_conversation)
        # 调用API获取回复
        response = ""
        final_answer = ""  # 用于存储最终答案
        # 使用 try/finally 确保即使发生错误也能更新UI
        try:
            for session_id, updated_history, api_response, api_final_answer in query_api(
                    session_id, updated_conversation, query, uploaded_files,
                    file_names, kb_names, kb_token, top_k, top_n, key_weight,
                    system_prompt, input_body, output_body, temperature,
                    model_name, task_type, force_ocr, kb_type
            ):
                # 更新响应文本和最终答案
                response = api_response
                if api_final_answer:  # 如果有最终答案，更新它
                    final_answer = api_final_answer
                # 创建临时对话历史用于显示
                temp_history = updated_conversation.copy()
                # 添加或更新助手回复（用于显示）
                if temp_history and temp_history[-1]['role'] == 'user':
                    # 如果最后一条是用户消息，添加新的助手消息（显示完整流程）
                    temp_history.append({"role": "assistant", "content": response})
                elif temp_history and temp_history[-1]['role'] == 'assistant':
                    # 如果最后一条已经是助手消息，更新内容（显示完整流程）
                    temp_history[-1]['content'] = response
                # 更新UI
                chatbot_display = update_chatbot(temp_history)
                yield session_id, temp_history, chatbot_display, "",None
                time.sleep(0.05)  # 小延迟确保UI更新
            # 最终更新对话历史（保存最终答案）
            if final_answer:  # 如果有最终答案，使用它
                if updated_conversation and updated_conversation[-1]['role'] == 'user':
                    updated_conversation.append({"role": "assistant", "content": final_answer})
                elif updated_conversation and updated_conversation[-1]['role'] == 'assistant':
                    updated_conversation[-1]['content'] = final_answer
            else:  # 如果没有最终答案，使用完整响应
                if updated_conversation and updated_conversation[-1]['role'] == 'user':
                    updated_conversation.append({"role": "assistant", "content": response})
                elif updated_conversation and updated_conversation[-1]['role'] == 'assistant':
                    updated_conversation[-1]['content'] = response
            # 限制历史对话轮数
            max_messages = max_turns * 2  # 每轮包含用户和助手各一条消息
            if len(updated_conversation) > max_messages:
                # 保留系统消息（如果有）和最近的max_messages条消息
                system_messages = [msg for msg in updated_conversation if msg["role"] == "system"]
                recent_messages = updated_conversation[-max_messages:]
                updated_conversation = system_messages + recent_messages
        finally:
            # 最终UI更新（使用最终保存的对话历史）
            chatbot_display = update_chatbot(updated_conversation)
            yield session_id, updated_conversation, chatbot_display, "", None  # 添加None清空上传文件
    # 停止按钮事件
    stop_btn.click(
        fn=stop_generation_fn,
        inputs=[],
        outputs=[stop_generation]
    )
    # 提交查询事件
    submit_event = submit_btn.click(
        fn=submit_query,
        inputs=[
            session_id,
            conversation_history,
            sys_query,
            uploaded_files,
            file_names,
            kb_names,
            kb_token,
            top_k,
            top_n,
            key_weight,
            system_prompt,
            input_body,
            output_format,
            temperature,
            model_name,
            task_type,
            max_turns,
            force_ocr,
            kb_type  # 添加kb_type参数
        ],
        outputs=[session_id, conversation_history, chatbot, sys_query, uploaded_files]
    )
    # 创建新对话
    new_chat_btn.click(
        fn=create_new_chat,
        inputs=[],
        outputs=[session_id, conversation_history, chatbot, uploaded_files]
    )
    # 清空历史
    clear_history_btn.click(
        fn=clear_chat_history,
        inputs=[session_id],
        outputs=[session_id, conversation_history, chatbot, uploaded_files]
    )
    # Enter键提交
    sys_query.submit(
        fn=submit_query,
        inputs=[
            session_id,
            conversation_history,
            sys_query,
            uploaded_files,
            file_names,
            kb_names,
            kb_token,
            top_k,
            top_n,
            key_weight,
            system_prompt,
            input_body,
            output_format,
            temperature,
            model_name,
            task_type,
            max_turns,
            force_ocr,
            kb_type  # 添加kb_type参数
        ],
        outputs=[session_id, conversation_history, chatbot, sys_query,uploaded_files]
    )
# 启动Gradio应用
if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7862)
