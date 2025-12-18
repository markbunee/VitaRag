# graph/processors/document_processor.py
import asyncio
from datetime import datetime
from typing import Dict, Any, AsyncGenerator

from config import logger
from config import get_config

from utils.prompts.prompt import FINAL_ANSWER_PROMPT
from utils.utils import system_prompt_to_parse

from .response_generator import ResponseGenerator
from .. import EventEmitter


class ProcessingComponent:
    """处理流程的基础组件"""
    def __init__(self, state: Dict[str, Any], emitter: EventEmitter):
        self.state = state
        self.emitter = emitter
        self.config = get_config()

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行组件的处理逻辑"""
        raise NotImplementedError("子类必须实现此方法")

class KnowledgeFinalAnswerComponent(ProcessingComponent):
    """最终答案生成组件"""
    # TODO: 知识问答通用节点，可作为文件上传/单文件知识问答/多文件知识问答等节点的最终回复节点
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        sys_query = self.state.get("sys_query", "")
        temperature = self.state.get("temperature", 0.1)
        model_name = self.state.get("model_name")
        conversation_history = self.state.get("conversation_history",None)
        kb_content = self.state.get("kb_content", "")
        contrastive_content = self.state.get("contrastive_content", "")
        file_content = self.state.get("file_content", "")
        system_prompt = self.state.get("system_prompt", "") or self.config.DEFAULT_SYSTEM_PROMPT
        input_body = self.state.get("input_body", "")
        current_date = datetime.now().strftime("%Y-%m-%d")
        system_prompt_to_use = system_prompt_to_parse(system_prompt)
        logger.info(f"Knowledge System Prompt task")
        final_system_prompt = FINAL_ANSWER_PROMPT.format(
            system_prompt=system_prompt_to_use,
            upload_content=f"# 上传的文档内容:\n{file_content}" if file_content else "",
            content=f"# 从知识库检索到的文档原始内容:\n{kb_content}\n" if kb_content else "",
            contrastive_content = f"# 对多个文件根据问题总结后的内容，包含了文件名、问题分析总结、页码标记:\n{contrastive_content}\n" if contrastive_content else "",
            input_body=f"# 额外接口返回数据:\n{input_body}" if input_body else "",
            current_date=current_date
        )
        yield await self.emitter.emit_node_started("final_answer", "正在生成最终回答...\n")

        try:
            # 初始化生成器
            response_generator = ResponseGenerator()

            # 流式生成最终回答
            final_answer = ""
            async for token in response_generator.generate_stream_answer(
                    sys_query=sys_query,
                    final_system_prompt=final_system_prompt,
                    temperature=temperature,
                    model_name=model_name,
                    conversation_history=conversation_history
            ):
                final_answer += token
                yield await self.emitter.emit_message(token)
                await asyncio.sleep(0.005)

            # 保存到状态中
            self.state["final_answer"] = final_answer

            # 回答完成
            yield await self.emitter.emit_node_finished(
                "final_answer",
                "最终回答生成完成",
                completed=final_answer
            )

        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            self.state["last_error"] = self.state.get("last_error", "") + error_msg
            yield await self.emitter.emit_error(error_msg)

class GeneralFinalAnswerComponent(ProcessingComponent):
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:

        sys_query = self.state.get("sys_query", "")
        final_system_prompt = self.state.get("system_prompt", "")
        temperature = self.state.get("temperature", 0.1)
        model_name = self.state.get("model_name")
        conversation_history = self.state.get("conversation_history",None)
        yield await self.emitter.emit_node_started("final_answer", "正在生成最终回答...\n")
        response_generator = ResponseGenerator()
        final_answer = ""
        async for token in response_generator.generate_stream_answer(
                sys_query=sys_query,
                final_system_prompt=final_system_prompt,
                temperature=temperature,
                model_name=model_name,
                conversation_history=conversation_history
        ):
            final_answer += token
            yield await self.emitter.emit_message(token)
            await asyncio.sleep(0.005)
            self.state["final_answer"] = final_answer

        # 回答完成
        yield await self.emitter.emit_node_finished(
            "final_answer",
            "最终回答生成完成",
            completed=final_answer
        )

class ErrorHandlingComponent(ProcessingComponent):
    """错误处理组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        error_msg = self.state.get("error_msg","")+ self.state.get("last_error","")
        if not error_msg:
            error_msg = "未知错误"
        model_name = self.state.get("model_name",None)
        # error_type = self.state.get("last_error_type", "Exception")

        yield await self.emitter.emit_node_started(
            "final_answer",
            f"调用错误"
        )

        final_answer = ""
        # 生成错误说明
        response_generator = ResponseGenerator()
        async for token in response_generator.generate_error_explanation(error_msg,"error_type",model_name=model_name):
            final_answer += token
            yield await self.emitter.emit_message(token)
            await asyncio.sleep(0.01)
        self.state["final_answer"] = final_answer

        # 回答完成
        yield await self.emitter.emit_node_finished(
            "final_answer",
            "最终回答生成完成",
            completed=final_answer
        )


class RetryComponent(ProcessingComponent):
    """重试组件"""
    def __init__(self, state: Dict[str, Any], emitter, retry_component_class, max_retries: int = 2):
        super().__init__(state, emitter)
        self.retry_component_class = retry_component_class
        self.max_retries = max_retries

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        retry_count = self.state.get("retry_count", 0)

        if retry_count >= self.max_retries:
            yield await self.emitter.emit_node_started(
                "retry_exhausted",
                f"已达到最大重试次数 {self.max_retries}"
            )
            return

        self.state["retry_count"] = retry_count + 1

        yield await self.emitter.emit_node_started(
            "retry_attempt",
            f"第 {retry_count + 1} 次重试"
        )

        # 执行重试组件
        retry_component = self.retry_component_class(self.state, self.emitter)
        async for event in retry_component.process():
            yield event


class JsonConversionComponent(ProcessingComponent):
    """JSON转换组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        output_body = self.state.get("output_body", "")
        content = self.state.get("sys_query", "")

        if not output_body or output_body == "{}" or not content:
            return

        yield await self.emitter.emit_node_started("convert_to_json", "正在将结果转换为json...\n")

        try:
            json_converter = ResponseGenerator()
            json_result = ""

            async for token in json_converter.convert_to_json(content, output_body):
                json_result += token
                yield await self.emitter.emit_message(token)
                await asyncio.sleep(0.005)

            # 保存到状态中
            self.state["json_result"] = json_result

            yield await self.emitter.emit_node_finished(
                "convert_to_json",
                "转换json完成",
                completed=json_result
            )
        except Exception as e:
            error_msg = f"转换JSON时出错: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            self.state["last_error"] = error_msg
            yield await self.emitter.emit_error(error_msg)

