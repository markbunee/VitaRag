import os
import re
import threading
import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional, Union
import json
from pathlib import Path
import httpx
import datetime

from openai import AsyncOpenAI, AuthenticationError, NotFoundError, RateLimitError
from openai import BadRequestError, LengthFinishReasonError, ContentFilterFinishReasonError

from httpx import ConnectError, TimeoutException, HTTPStatusError

from config import get_config, logger
from graph import EventEmitter
from utils.prompts.prompt import DOCUMENT_SUMMARY_PROMPT, FINAL_ANSWER_PROMPT, NORMAL_ANSWER_PROMPT, relevant_metadata, \
    CONVERT_TO_JSON_PROMPT, ERROR_EXPLANATION_PROMPT, RETRIEVAL_ENHANCEMENT_PROMPT, FINAL_RAG_PROMPT
from utils.utils import system_prompt_to_parse


def remove_thinking_blocks(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"```thinking\s*([\s\S]*?)```", "", text).strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()

class ModelClient:
    @classmethod
    def create_new_client(cls, model_config):
        """每次创建一个全新客户端实例（不缓存）"""
        return AsyncOpenAI(
            api_key=model_config.get("api_key"),
            base_url=model_config.get("api_base_url"),
            timeout=httpx.Timeout(30.0, connect=10.0)
        )


class ResponseGenerator:
    """响应生成器，用于生成文档摘要和最终回答"""

    # 默认错误响应文本
    DEFAULT_RESPONSES = {
        'DOCUMENT_SUMMARY': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'FINAL_ANSWER': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'NORMAL_ANSWER': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'ERROR_EXPLANATION': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'ENHANCED_QUERY': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'JSON_CONVERT': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'RETRIEVAL_RESULTS': "抱歉，当前模型服务不可用。请稍后重试或联系系统管理员。",
        'CLASSIFICATION': '抱歉，文档分类服务暂时出现问题，请稍后重试。',
        'SUMMARY_EXTRACTION': '抱歉，论文摘要提取服务暂时出现问题，请稍后重试。',
        'SUMMARY_GENERATION': '抱歉，通用摘要生成服务暂时出现问题，请稍后重试。'
    }

    def __init__(self):
        # 获取模型配置
        config = get_config()
        LLM_MODEL_API = config.LLM_MODEL_API
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS[0]
        COT_LLM_MODELS = config.COT_LLM_MODELS[0]
        self.agent_model_config = LLM_MODEL_API.get(AGENT_LLM_MODELS)
        self.cot_model_config = LLM_MODEL_API.get(COT_LLM_MODELS)

    async def _safe_api_call_streaming(
        self,
        api_call_func,
        fallback_type: str,
        context_info: str = ""
    ) -> AsyncGenerator[str, None]:
        """统一的流式API调用错误处理包装器（带错误类型告知）"""
        try:
            has_content = False
            async for chunk in api_call_func():
                has_content = True
                yield chunk

            # 检查是否有内容返回
            if not has_content:
                logger.warning(f"API调用返回空内容 - {context_info}")
                yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（API调用结果为空）</error>"
        except (ConnectError, TimeoutException) as e:
            logger.error(f"网络连接错误 - {context_info}: {str(e)}")
            yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（网络连接错误）</error>"
        except (AuthenticationError, NotFoundError, RateLimitError) as e:
            logger.error(f"API服务错误 - {context_info}: {str(e)}")
            yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（API服务错误）</error>"
        except HTTPStatusError as e:
            logger.error(f"HTTP状态错误 - {context_info}: {str(e)}")
            yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（HTTP状态错误）</error>"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误 - {context_info}: {str(e)}")
            yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（JSON解析错误）</error>"
        except LengthFinishReasonError as e:
            # 专门响应超长异常（流式completion情况下）
            yield self.DEFAULT_RESPONSES['CONTEXT_OVERFLOW'] + "<error>（响应内容超限）</error>"
        except BadRequestError as e:
            msg = str(e)
            # 针对超上下文
            if "maximum context length" in msg or "too many tokens" in msg:
                yield self.DEFAULT_RESPONSES['CONTEXT_OVERFLOW'] + "<error>（输入内容超出最大上下文，请缩短）</error>"
            else:
                yield self.DEFAULT_RESPONSES['ERROR_EXPLANATION'] + "<error>（请求参数有误）</error>"
        except ContentFilterFinishReasonError:
            yield "抱歉，您的请求内容未通过审核。"
        except Exception as e:
            logger.error(f"未知错误 - {context_info}: {str(e)}")
            yield self.DEFAULT_RESPONSES[fallback_type] + "<error>（未知错误）</error>"

    async def _safe_api_call_bulk(
        self,
        api_call_func,
        fallback_type: str,
        context_info: str = "",
        return_type: str = "str"
    ) -> Union[str, List[Union[str, Dict]]]:
        """统一的非流式API调用错误处理包装器"""
        try:
            result = await api_call_func()

            # 检查结果是否为空
            if not result or (isinstance(result, str) and not result.strip()):
                logger.warning(f"API调用返回空结果 - {context_info}")
                if return_type == "list":
                    return []
                return self.DEFAULT_RESPONSES[fallback_type] + "（API调用结果为空）"
            return result

        except (ConnectError, TimeoutException) as e:
            logger.error(f"网络连接错误 - {context_info}: {str(e)}")
            suffix = "（网络连接错误）"
        except (AuthenticationError, NotFoundError, RateLimitError) as e:
            logger.error(f"API服务错误 - {context_info}: {str(e)}")
            suffix = "（API服务错误）"
        except HTTPStatusError as e:
            logger.error(f"HTTP状态错误 - {context_info}: {str(e)}")
            suffix = "（HTTP状态错误）"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误 - {context_info}: {str(e)}")
            suffix = "（JSON解析错误）"
        except Exception as e:
            logger.error(f"未知错误 - {context_info}: {str(e)}")
            suffix = "（未知错误）"
        # 注意：发生异常就会走这里
        if return_type == "list":
            return []
        return self.DEFAULT_RESPONSES[fallback_type] + f"<error>{suffix}</error>"

    def _get_model_config(self, model_name: str = None, use_cot: bool = False) -> Dict[str, Any]:
        """获取模型配置"""
        config = get_config()

        if model_name and model_name in config.LLM_MODEL_API:
            return config.LLM_MODEL_API[model_name]
        return self.cot_model_config if use_cot else self.agent_model_config

    def _build_messages(
        self,
        system_prompt: str,
        user_query: str,
        conversation_history: list = None,
        model_name:str = None,
        model_config: dict = None
    ) -> List[Dict[str, str]]:

        """构建消息列表"""
        special_names = ["qwq"]
        model_name_str = model_name or ""
        use_special = any(name in model_name_str.lower() for name in special_names)
        messages = []

        # 处理历史
        if conversation_history and isinstance(conversation_history, list):
            last_role = "system"
            for msg in conversation_history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "assistant":
                    content = remove_thinking_blocks(content)
                if role in ["user", "assistant"] and role != last_role and content.strip():
                    messages.append({"role": role, "content": content})
                    last_role = role

        # 拼接qwords
        qwords = model_config.get("qwords", "") if model_config else ""

        # 确保user_query不为空
        if not user_query or not user_query.strip():
            user_query = "请根据提供的信息进行处理"
            
        # 拼接用户内容
        human_content = f"{user_query}{qwords}".strip()

        if use_special:
            # 合并system_prompt到当前这轮user消息
            # 正确分支应分清最后一条消息是谁
            if messages:
                if messages[-1]["role"] == "user":
                    if len(messages) == 1 and all(m["role"] == "user" for m in messages):
                        messages.append({"role":"assistant","content":""})
                        messages.append({"role": "user",
                                         "content": f"{system_prompt}\n<user_inputs>\n{human_content}\n</user_inputs>"})
                    else:
                        messages.append({"role": "user",
                                         "content": f"{system_prompt}\n<user_inputs>\n{human_content}\n</user_inputs>"})
                else:
                    messages.append({"role": "user",
                                     "content": f"{system_prompt}\n<user_inputs>\n{human_content}\n</user_inputs>"})
            else:
                messages.append({"role": "user",
                                 "content": f"{system_prompt}\n<user_inputs>\n{human_content}\n</user_inputs>"})
        else:
            # 正常流程，先加system再加历史
            if system_prompt and system_prompt.strip():
                messages = [{"role": "system", "content": system_prompt}] + messages
            # 这里messages可能为空，务必加判断
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] += human_content
            else:
                messages.append({"role": "user", "content": human_content})

        return messages

    async def _handle_streaming_response(
        self,
        response,
        model_name: str,
        model_config: dict
    ) -> AsyncGenerator[str, None]:
        """处理流式响应，统一处理思维链逻辑"""
        in_thinking_block = False
        thinking_buffer = ""
        block_marker = "```thinking\n\n"
        end_marker = "\n\n```\n\n"
        end_flag = "</think>"
        thinking_ended = False
        is_deepseek_r1 = (
                "deepseek-r" in model_name.lower() or
                "deepseek_r" in model_name.lower() or
                model_config.get("reasoning", "") == "nonstandard"
        )

        async for chunk in response:
            if not chunk.choices or not chunk.choices[0].delta:
                continue

            delta = chunk.choices[0].delta
            reasoning_content_chunk = getattr(delta, 'reasoning_content', None)
            content_chunk = getattr(delta, 'content', '')

            use_deepseek_think_compat = is_deepseek_r1 and not reasoning_content_chunk

            # 标准分支：处理 reasoning_content
            if reasoning_content_chunk:
                if not in_thinking_block:
                    yield block_marker
                    in_thinking_block = True
                yield reasoning_content_chunk
                continue

            # 兼容分支：处理 deepseek-r1 的思维链
            if use_deepseek_think_compat and content_chunk:
                if thinking_ended:
                    yield content_chunk
                    continue

                thinking_buffer += content_chunk
                idx = thinking_buffer.find(end_flag)

                if idx == -1:
                    # 未发现结束标记，输出缓冲区内容（保留末尾以防分割）
                    min_buf = len(end_flag) - 1
                    if len(thinking_buffer) > min_buf:
                        emit_text = thinking_buffer[:-min_buf]
                        if emit_text:
                            if not in_thinking_block:
                                yield block_marker
                                in_thinking_block = True
                            yield emit_text
                        thinking_buffer = thinking_buffer[-min_buf:]
                else:
                    # 找到结束标记
                    thinking_text = thinking_buffer[:idx]
                    rest_text = thinking_buffer[idx+len(end_flag):]

                    if not in_thinking_block:
                        yield block_marker
                        in_thinking_block = True
                    if thinking_text:
                        yield thinking_text
                    yield end_marker
                    in_thinking_block = False
                    thinking_ended = True

                    if rest_text:
                        yield rest_text
                    thinking_buffer = ""
                continue

            # 普通内容
            if content_chunk:
                if in_thinking_block:
                    yield end_marker
                    in_thinking_block = False
                yield content_chunk

        # 清理工作
        if thinking_buffer and not thinking_ended:
            if not in_thinking_block:
                yield block_marker
            yield thinking_buffer
        if in_thinking_block:
            yield end_marker

    async def generate_stream_answer(
        self,
        sys_query: str,
        final_system_prompt: str,
        temperature=0.1,
        model_name: str = None,
        conversation_history: list = None,
        fallback_type: str = 'NORMAL_ANSWER',
    ) -> AsyncGenerator[str, None]:
        """
        生成流式回答的核心方法。
        """
        async def _api_call():
            model_config = self._get_model_config(model_name, use_cot=True)
            messages = self._build_messages(final_system_prompt, sys_query, conversation_history, model_name, model_config)

            # 创建流式请求
            client = ModelClient.create_new_client(model_config)
            actual_model_name = model_config.get("model_name")
            max_tokens = model_config.get("max_tokens")

            response = await client.chat.completions.create(
                model=actual_model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            async for chunk in self._handle_streaming_response(response, actual_model_name, model_config):
                yield chunk

        context_info = f"generate_stream_answer - model: {model_name}, query: {sys_query[:50]}..."
        async for chunk in self._safe_api_call_streaming(_api_call, fallback_type, context_info):
            yield chunk

    async def generate_blocking_answer(
        self,
        sys_query: str,
        final_system_prompt: str,
        temperature: float = 0.1,
        model_name: str = None,
        conversation_history: list = None,
        fallback_type: str = 'NORMAL_ANSWER'
    ) -> str:
        """
        生成阻塞式回答，一次性返回完整结果。
        """
        model_config = self._get_model_config(model_name)
        model_name = model_name or model_config.get("model_name")
        client = ModelClient.create_new_client(model_config)

        messages = self._build_messages(
            system_prompt=final_system_prompt,
            user_query=sys_query,
            conversation_history=conversation_history,
            model_name=model_name,
            model_config=model_config
        )

        async def _api_call():
            response = await client.chat.completions.create(
                model=model_name or model_config.get("model"),
                messages=messages,
                temperature=temperature,
                stream=False
            )
            return remove_thinking_blocks(response.choices[0].message.content)

        return await self._safe_api_call_bulk(
            _api_call,
            fallback_type=fallback_type,
            context_info=f"Model: {model_name}, Query: {sys_query[:80]}"
        )

    # --------------------------------------------------------------------------
    # Refactored High-Level API Methods
    # --------------------------------------------------------------------------

    async def generate_document_summary_bulk(self, document_content: str, query: str) -> str:
        """
        【新】一次性生成单个文档的摘要。
        由 SummaryGeneratorComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        final_system_prompt = DOCUMENT_SUMMARY_PROMPT.format(query=query, document=document_content)
        sys_query = f"请根据我的问题 '{query}' 总结这篇文档的内容。"

        return await self.generate_blocking_answer(
            sys_query=sys_query,
            final_system_prompt=final_system_prompt,
            model_name=AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None,
            fallback_type='DOCUMENT_SUMMARY'
        )

    async def generate_document_summary(self, document_content: str, query: str) -> AsyncGenerator[str, None]:
        """
        【新】流式生成单个文档的摘要。
        由 SummaryGeneratorComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        final_system_prompt = DOCUMENT_SUMMARY_PROMPT.format(query=query, document=document_content)
        sys_query = f"请根据我的问题 '{query}' 总结这篇文档的内容。"

        async for chunk in self.generate_stream_answer(
            sys_query=sys_query,
            final_system_prompt=final_system_prompt,
            model_name=AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None,
            fallback_type='DOCUMENT_SUMMARY'
        ):
            yield chunk

    async def generate_error_explanation(self, error_message: str, error_type: str, model_name: str = None) -> AsyncGenerator[str, None]:
        """
        【新】流式生成错误的解释。
        由 ErrorHandlingComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        final_system_prompt = ERROR_EXPLANATION_PROMPT.format(error_message=error_message)
        sys_query = f"请解释这个错误：{error_message}"

        async for chunk in self.generate_stream_answer(
            sys_query=sys_query,
            final_system_prompt=final_system_prompt,
            model_name=model_name or (AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None),
            fallback_type='ERROR_EXPLANATION'
        ):
            yield chunk

    async def generate_enhanced_query(self, query: str, conversation_history: list = None, model_name: str = None) -> AsyncGenerator[str, None]:
        """
        【新】流式生成增强后的查询。
        由 QueryEnhancementComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        # 遵循 RETRIEVAL_ENHANCEMENT_PROMPT 的格式要求
        conversation_context = ""
        if conversation_history and isinstance(conversation_history, list):
            for msg in conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role in ["user", "assistant"]:
                    conversation_context += f'{role}: {content}\n'

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # 主要指令和格式已在 sys_query 中定义
        final_system_prompt = ""
        sys_query = RETRIEVAL_ENHANCEMENT_PROMPT.format(
            sys_query=query,
            conversation=conversation_context,
            current_date=current_date
        )

        async for chunk in self.generate_stream_answer(
            sys_query=sys_query,
            final_system_prompt=final_system_prompt,
            model_name=model_name or (AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None),
            fallback_type='ENHANCED_QUERY'
        ):
            yield chunk

    async def convert_to_json(self, content: str, output_body: str) -> AsyncGenerator[str, None]:
        """
        【新】流式将文本内容转换为JSON格式。
        由 ...JsonConversionComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        final_system_prompt = CONVERT_TO_JSON_PROMPT
        sys_query = f"# json输出示例:\n{output_body}\n\n# 输入的文本内容:\n{content}"

        async for chunk in self.generate_stream_answer(
            sys_query=sys_query,
            final_system_prompt=final_system_prompt,
            model_name=AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None,
            fallback_type='JSON_CONVERT'
        ):
            yield chunk

    async def retrieved_to_results(self, sys_query: str, final_answer: str, retriever_content: str) -> str:
        """

        【新】从引用中筛选与答案最相关的部分。
        由 RetrievedConversionComponent 调用。
        """
        config = get_config()
        AGENT_LLM_MODELS = config.AGENT_LLM_MODELS

        query_prompt = relevant_metadata.format(
            QUESTION=sys_query,
            ANSWER=final_answer,
            METADATA_LIST=retriever_content,
            qwords=""
        )

        return await self.generate_blocking_answer(
            sys_query=query_prompt,
            final_system_prompt="",
            model_name=AGENT_LLM_MODELS[0] if AGENT_LLM_MODELS else None,
            fallback_type='RETRIEVAL_RESULTS'
        )

    # async def generate_final_knowledge_answer(self, sys_query,kb_content: str, contrastive_content,file_content,system_prompt,input_body,model_name):
    #     """
    #     【新】流式生成最终知识回复结果
    #     构建知识问答通用回复，可用于文件上传/单文件问答/多文件问答/多知识库多文件问答等多个组件最后的
    #     """
    #     current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    #     system_prompt_to_use = system_prompt_to_parse(system_prompt)
    #     logger.info(f"Knowledge System Prompt task")
    #     final_system_prompt = FINAL_ANSWER_PROMPT.format(
    #         system_prompt=system_prompt_to_use,
    #         upload_content=f"# 上传的文档内容:\n{file_content}" if file_content else "",
    #         content=f"# 从知识库检索到的文档原始内容:\n{kb_content}\n" if kb_content else "",
    #         contrastive_content = f"# 对多个文件根据问题总结后的内容，包含了文件名、问题分析总结、页码标记:\n{contrastive_content}\n" if contrastive_content else "",
    #         input_body=f"# 额外接口返回数据:\n{input_body}" if input_body else "",
    #         current_date=current_date
    #     )
    #     async for chunk in self.generate_stream_answer(
    #             sys_query=sys_query,
    #             final_system_prompt=final_system_prompt,
    #             model_name=model_name
    #     ):
    #         yield chunk

