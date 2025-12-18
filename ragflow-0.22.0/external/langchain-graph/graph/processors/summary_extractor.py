import json
import logging
import re
from typing import Dict, Any, AsyncGenerator, List, Optional

from config import get_config
from graph.event_emitter import EventEmitter
# 导入中央服务和新的 Prompt 模板
from graph.processors.response_generator import ResponseGenerator
from utils.prompts.prompt import (
    DOCUMENT_CLASSIFICATION_PROMPT,
    PAPER_SUMMARY_EXTRACTION_PROMPT,
    GENERAL_SUMMARY_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)

class ProcessingComponent:
    """处理流程的基础组件"""
    def __init__(self, state: Dict[str, Any], emitter: EventEmitter):
        self.state = state
        self.emitter = emitter
        self.config = get_config()

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行组件的处理逻辑"""
        raise NotImplementedError("子类必须实现此方法")

def extract_json_from_markdown(response):
    # 可能是 ```json ... ``` 或者 ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response)
    if match:
        return match.group(1)
    return response

class DocumentExtractorComponent(ProcessingComponent):
    """文档提取器组件"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理文档提取"""
        yield await self.emitter.emit_node_started("document_extractor", "正在提取文档内容...")

        try:
            file_paths = self.state.get("file_paths", [])

            # 处理文档提取
            extracted_texts = []
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        extracted_texts.append(content)
                except Exception as e:
                    logger.warning(f"读取文件 {file_path} 失败: {str(e)}")
                    continue

            if not extracted_texts:
                self.state["error_msg"] = "未能提取到任何文档内容"
                yield await self.emitter.emit_error("未能提取到任何文档内容")
                return

            self.state["extracted_texts"] = extracted_texts
            yield await self.emitter.emit_node_finished("document_extractor", f"成功提取 {len(file_paths)} 个文档")

        except Exception as e:
            logger.error(f"文档提取失败: {str(e)}")
            self.state["error_msg"] = f"文档提取失败: {str(e)}"
            yield await self.emitter.emit_error(f"文档提取失败: {str(e)}")


class DocumentValidationComponent(ProcessingComponent):
    """文档有效性验证组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """验证文档内容有效性"""
        yield await self.emitter.emit_node_started("document_validator", "正在验证文档内容...")

        extracted_texts = self.state.get("extracted_texts", "")

        # 检查文档有效性
        if len(extracted_texts) < 4 and (not extracted_texts or extracted_texts[0] == ""):
            self.state["is_valid"] = False
            self.state["error_msg"] = "文档内容无效或为空"
            yield await self.emitter.emit_error("文档内容无效或为空")
        elif not extracted_texts:
            self.state["is_valid"] = False
            self.state["error_msg"] = "文档内容无效或为空"
            yield await self.emitter.emit_error("文档内容无效或为空")
        else:
            self.state["is_valid"] = True
            yield await self.emitter.emit_node_finished("document_validator", "文档内容验证通过")


class TextLimitComponent(ProcessingComponent):
    """文本长度限制组件"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """限制文本长度"""
        yield await self.emitter.emit_node_started("text_limiter", "正在处理文本长度限制...")

        extracted_texts = self.state.get("extracted_texts", "")

        if not extracted_texts or extracted_texts.strip() == "":
            self.state["processed_text"] = ""
            yield await self.emitter.emit_node_finished("text_limiter", "文本为空，已设置空处理结果")
        else:
            # 合并所有文本并限制长度
            processed_text = "".join(extracted_texts)[:30000]
            self.state["processed_text"] = processed_text
            text_length = len(self.state["processed_text"])
            yield await self.emitter.emit_node_finished("text_limiter", f"文本长度处理完成，处理后长度: {text_length} 字符")


class DocumentClassifierComponent(ProcessingComponent):
    """文档分类器组件"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """分类文档类型"""
        yield await self.emitter.emit_node_started("classifier", "正在分析文档类型...")

        try:
            text_content = self.state.get("processed_text", "")

            if not text_content:
                self.state["classification"] = "其他类型"
                yield await self.emitter.emit_node_finished("classifier", "文档类型: 其他类型")
                return

            # 标准化调用
            response_generator = ResponseGenerator()
            final_system_prompt = DOCUMENT_CLASSIFICATION_PROMPT.format(text_content=text_content)
            response = await response_generator.generate_blocking_answer(
                sys_query="请对文本进行分类。",
                final_system_prompt=final_system_prompt,
                temperature=0.1,
                fallback_type='CLASSIFICATION'
            )

            try:
                result = json.loads(extract_json_from_markdown(response))
                classification = result.get("classification", "其他类型")
            except json.JSONDecodeError:
                classification = "论文类型" if "论文" in response else "其他类型"

            self.state["classification"] = classification
            self.state["classification_result"] = response

            yield await self.emitter.emit_node_finished("classifier", f"文档类型: {classification}")

        except Exception as e:
            logger.error(f"分类器处理失败: {str(e)}")
            self.state["classification"] = "其他类型"
            self.state["error_msg"] = f"分类失败: {str(e)}"
            yield await self.emitter.emit_error(f"分类失败: {str(e)}")


class SummaryExtractorComponent(ProcessingComponent):
    """摘要&标签提取组件（用于论文类型）"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """提取摘要和标签"""
        yield await self.emitter.emit_node_started("summary_extractor", "正在提取论文摘要和关键词...")

        try:
            text_content = self.state.get("processed_text", "")

            # 标准化调用
            response_generator = ResponseGenerator()
            final_system_prompt = PAPER_SUMMARY_EXTRACTION_PROMPT.format(text_content=text_content)
            response = await response_generator.generate_blocking_answer(
                sys_query="请提取摘要和关键词。",
                final_system_prompt=final_system_prompt,
                temperature=0.1,
                fallback_type='SUMMARY_EXTRACTION'
            )

            try:
                result = json.loads(extract_json_from_markdown(response))
                summary = result.get("summary", "")
                keywords = result.get("keywords", [])
            except json.JSONDecodeError:
                summary = ""
                keywords = []

            self.state["summary"] = summary
            self.state["keywords"] = keywords
            self.state["extraction_result"] = response

            yield await self.emitter.emit_node_finished("summary_extractor", "摘要和关键词提取完成")

        except Exception as e:
            logger.error(f"摘要标签提取失败: {str(e)}")
            self.state["summary"] = ""
            self.state["keywords"] = []
            self.state["error_msg"] = f"提取失败: {str(e)}"
            yield await self.emitter.emit_error(f"提取失败: {str(e)}")


class SummaryGeneratorComponent(ProcessingComponent):
    """摘要&标签生成组件（用于非论文类型）"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """生成摘要"""
        yield await self.emitter.emit_node_started("summary_generator", "正在生成摘要...")

        try:
            text_content = self.state.get("processed_text", "")

            # 标准化调用
            response_generator = ResponseGenerator()
            final_system_prompt = GENERAL_SUMMARY_GENERATION_PROMPT.format(text_content=text_content)
            response = await response_generator.generate_blocking_answer(
                sys_query="请生成摘要。",
                final_system_prompt=final_system_prompt,
                temperature=0.7,
                fallback_type='SUMMARY_GENERATION'
            )

            try:
                result = json.loads(extract_json_from_markdown(response))
                summary = result.get("summary", "")
            except json.JSONDecodeError:
                summary = response

            self.state["summary"] = summary
            self.state["generation_result"] = response

            yield await self.emitter.emit_node_finished("summary_generator", "摘要生成完成")

        except Exception as e:
            logger.error(f"摘要生成失败: {str(e)}")
            self.state["summary"] = ""
            self.state["error_msg"] = f"生成失败: {str(e)}"
            yield await self.emitter.emit_error(f"生成失败: {str(e)}")


class FinalResponseComponent(ProcessingComponent):
    """最终响应生成组件"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """生成最终响应"""
        classification = self.state.get("classification", "其他类型")
        summary = self.state.get("summary", "")

        if "论文" in classification:
            keywords = self.state.get("keywords", [])
            result = {
                "type": "论文类型",
                "summary": summary,
                "keywords": keywords
            }
        else:
            result = {
                "type": "其他类型",
                "summary": summary
            }

        yield await self.emitter.emit_final_message(json.dumps(result, ensure_ascii=False, indent=2))


class ErrorHandlingComponent(ProcessingComponent):
    """错误处理组件"""

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理错误情况"""
        error_msg = self.state.get("error_msg", "处理过程中出现未知错误")
        yield await self.emitter.emit_final_message(f"错误: {error_msg}")
