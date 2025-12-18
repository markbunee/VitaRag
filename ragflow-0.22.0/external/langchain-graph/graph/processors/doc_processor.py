# graph/processors/components.py
import asyncio
import json
import re
from typing import Dict, Any, AsyncGenerator
from config import logger, get_config
from utils.client.ufrag import extract_document_content, query_knowledge_base
from graph.event_emitter import EventEmitter
from graph.processors.response_generator import ResponseGenerator
from utils.result_process.ufrag_process import analyze_result,get_origin_contents


class ProcessingComponent:
    """处理流程的基础组件"""
    def __init__(self, state: Dict[str, Any], emitter: EventEmitter):
        self.state = state
        self.emitter = emitter
        self.config = get_config()

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行组件的处理逻辑"""
        raise NotImplementedError("子类必须实现此方法")


class FileExtractionComponent(ProcessingComponent):
    """文件内容提取组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        file_paths = self.state.get("file_paths", [])
        file_paths = list(set(file_paths))
        if not file_paths:
            self.state["file_content"] = ""
            return

        yield await self.emitter.emit_node_started(
            "file_processing",
            f"开始提取 {len(file_paths)} 个上传文件的内容...",
            file=file_paths
        )

        try:
            force_ocr = self.state.get("force_ocr", None)
            kb_token = self.state.get("kb_token", None)
            file_content = await extract_document_content(
                file_paths,
                self.config.FILE_EXTRACTION_API,
                force_ocr,
                kb_token
            )
            self.state["file_content"] = file_content #之后节点可能使用到的变量
            self.state["extracted_texts"] = file_content
            yield await self.emitter.emit_node_finished(
                "file_processing",
                "文件内容提取完成"
            )
        except Exception as e:
            error_msg = f"文件提取失败: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            self.state["file_content"] = ""
            self.state["extracted_texts"] = ""
            yield await self.emitter.emit_error(error_msg)


class QueryEnhancementComponent(ProcessingComponent):
    """查询增强组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            sys_query = self.state.get("sys_query", "")
            yield await self.emitter.emit_node_started("query_enhancement", "正在优化查询...")
            response_generator = ResponseGenerator()
            conversation_history = self.state.get("conversation_history", None)
            final_answer = ""
            if conversation_history:
                # yield await self.emitter.emit_message('\n```问题增强中...\n\n')
                async for token in response_generator.generate_enhanced_query(sys_query, conversation_history):
                    final_answer += token
                    # yield await self.emitter.emit_message(token)
                    await asyncio.sleep(0.005)
                # yield await self.emitter.emit_message('\n\n```\n\n')
                self.state["enhanced_query"] = final_answer
            else:
                self.state["enhanced_query"] = ""
            yield await self.emitter.emit_node_finished(
                "query_enhancement",
                f"查询已优化为: {final_answer}"
            )
        except Exception as e:
            error_msg = f"生成回答时出错: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            yield await self.emitter.emit_error(error_msg)


class SingleFileKnowledgeBaseQueryComponent(ProcessingComponent):
    """单文件知识库查询组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        system_prompt = self.state.get("system_prompt", "") or self.config.DEFAULT_SYSTEM_PROMPT
        kb_names = self.state.get("kb_names", [])
        file_names = self.state.get("file_names", [])
        file_name = file_names[0] if file_names else ""
        tags = self.state.get("tags",[])
        tags = tags[0] if tags else ""
        sys_query = self.state.get("sys_query", "")
        enhanced_query = self.state.get("enhanced_query", "")
        top_k = self.state.get("top_k", 30)
        top_n = self.state.get("top_n", 3)
        key_weight = self.state.get("key_weight", 0.8)
        custom_filters = {}
        if file_names:
            custom_filters["file_name"] = file_names
        if tags:
            custom_filters["tags"] = tags


        yield await self.emitter.emit_node_started(
                "single_file_processing",
                f"正在处理文件: {file_name}"
            )

        try:
            multi_querys = [sys_query]
            if enhanced_query:
                multi_querys = [q for q in [sys_query, enhanced_query] if q and q.strip()]

            origin_results = await query_knowledge_base(
                kb_names, file_name,top_k, top_n, key_weight,
                multi_querys, self.config.KNOWLEDGE_BASE_API,
                self.state.get("kb_token", ""),custom_filters
            )
            results = get_origin_contents(origin_results,None)
            MAX_DOC_CONTENT_LENGTH = self.config.MAX_DOC_CONTENT_LENGTH
            content,retrieved_docs_metadata = analyze_result(results,file_names,MAX_DOC_CONTENT_LENGTH)
            # 保存到状态中
            self.state["kb_content"] = content #TODO: 注意workflow中使用当前参数判断分支走向
            if not content or content.strip() == "":
                self.state["last_error"] = "当前检索的向量库未返回任何内容，请尝试重新导入文件或联系管理员检后台"
            self.state["retrieved_docs_metadata"] = retrieved_docs_metadata

            # 向客户端发送检索到的文档信息
            display_file = retrieved_docs_metadata[0].get("source", "") if len(file_name) == 0 else file_name

            # 构造提示词
            yield await self.emitter.emit_origin_documents_retrieved(display_file, origin_results)

            yield await self.emitter.emit_node_finished(
                "single_file_processing",
                "文件处理完成"
            )

        except Exception as e:
            error_msg = f"查询知识库时出错: {str(e)}"
            logger.error(f"[ERROR] {error_msg}")
            self.state["last_error"] = error_msg
            self.state["last_error_type"] = "知识库查询节点"
            yield await self.emitter.emit_error(error_msg)


class MultiFileKnowledgeBaseQueryComponent(ProcessingComponent):
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        file_names = self.state.get("file_names", [])
        tags = self.state.get("tags", [])
        kb_names = self.state.get("kb_names", [])
        sys_query = self.state.get("sys_query", "")
        enhanced_query = self.state.get("enhanced_query", "")
        top_k = self.state.get("top_k", 35)
        top_n = self.state.get("top_n", 3)
        key_weight = self.state.get("key_weight", 0.8)
        kb_token = self.state.get("kb_token", "")
        MAX_DOC_CONTENT_LENGTH = self.config.MAX_DOC_CONTENT_LENGTH

        response_generator = ResponseGenerator()
        items, item_type, item_label = [], '', ''
        if file_names:
            items, item_type, item_label = file_names, "file_name", "文件"
        elif tags:
            items, item_type, item_label = tags, "tags", "标签"

        display_name = file_names if file_names else tags
        yield await self.emitter.emit_node_started(
            "multi_file_processing",
            f"开始处理 {display_name}..."
        )

        # 如果没有要处理的项目，则直接结束
        if not items:
            self.state["error_msg"] = "没有指定文件或标签，当前输入的文件名和标签为空，处理结束。检查是否错误的调用的多文件/标签方法"
            yield await self.emitter.emit_node_finished(
                "multi_file_processing",
                "没有指定文件或标签，处理结束。"
            )

        # 初始化用于聚合结果的局部变量
        file_summaries = {}
        combined_content = ""
        all_file_docs = []
        errors = []
        aggregated_metadata = []
        multi_querys = [sys_query]
        if enhanced_query:
            multi_querys = [q for q in [sys_query, enhanced_query] if q and q.strip()]

        for i, item in enumerate(items):
            progress = (i / len(items)) * 100

            # 1. 开始处理项目
            yield await self.emitter.emit_node_started(
                "item_processing",
                f"[{i+1}/{len(items)}] 正在查询{item_label} '{item}'...\n",
                **{item_type: item, "progress": progress, "index": i + 1, "total": len(items)}
            )

            try:
                # 根据项目类型准备查询参数
                custom_filters = {item_type: item}
                # 如果是按标签查询，则 file_name 参数为空列表
                query_file_name = item if item_type == "file_name" else []

                # 调用知识库查询
                origin_results = await query_knowledge_base(
                    kb_names, query_file_name, top_k, top_n, key_weight,
                    multi_querys, self.config.KNOWLEDGE_BASE_API,
                    kb_token, custom_filters
                )

                results = get_origin_contents(origin_results, None)
                content, retrieved_docs_metadata = analyze_result(results, [item], MAX_DOC_CONTENT_LENGTH)

                all_file_docs.extend(results)
                aggregated_metadata.extend(retrieved_docs_metadata)

                # 2. 生成总结
                yield await self.emitter.emit_node_started(
                    "summary_generation",
                    f"[{i+1}/{len(items)}] 正在为{item_label} '{item}'生成总结...\n",
                    **{item_type: item, "progress": progress + 30}
                )

                summary_full = ""
                yield await self.emitter.emit_message(f"\n```正在对 {item} 归纳...\n", item)
                async for token in response_generator.generate_document_summary(content, sys_query):
                    summary_full += token
                    yield await self.emitter.emit_message(token, item)
                    await asyncio.sleep(0.005)
                yield await self.emitter.emit_message(f"\n```\n", item)

                # 3. 聚合结果
                file_summaries[item] = summary_full
                combined_content += f"\n\n{item_label} '{item}' 内容总结:\n{summary_full}"

                yield await self.emitter.emit_node_finished(
                    "summary_generation",
                    f"[{i+1}/{len(items)}] {item_label} '{item}' 总结生成完成",
                    **{item_type: item, "completed": combined_content}
                )

            except Exception as e:
                error_msg = f"查询知识库内的指定{item_label} {item} 时出错: {str(e)}"
                logger.error(f"[ERROR] {error_msg}")
                errors.append(error_msg)
                yield await self.emitter.emit_error(error_msg, **{item_type: item})

        yield await self.emitter.emit_origin_documents_retrieved(str(items), all_file_docs)
        # 更新 state
        logger.info("所有文件/标签总结生成完成")
        self.state["contrastive_content"] = combined_content.replace("<origin>", "").replace("</origin>", "")
        self.state["file_summaries"] = file_summaries
        self.state["all_file_docs"] = all_file_docs
        self.state["retrieved_docs_metadata"] = aggregated_metadata
        self.state["error_msg"] = "\n".join(errors)

        # 多文件/标签处理完成
        yield await self.emitter.emit_node_finished(
            "multi_file_processing",
            "所有项目处理完成"
        )


class MultiFileParallelQueryComponent(ProcessingComponent):
    """多文件并行查询组件"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        # TODO:后续重构
        1



class AnswerJsonConversionComponent(ProcessingComponent):
    """将final_answer组建输出的回复进行JSON转换"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        output_body = self.state.get("output_body", "")
        final_answer = self.state.get("final_answer", "")

        if not output_body or output_body == "{}" or not final_answer:
            return

        yield await self.emitter.emit_node_started("convert_to_json", "正在将结果转换为json...\n")

        try:
            json_converter = ResponseGenerator()
            json_result = ""

            async for token in json_converter.convert_to_json(final_answer, output_body):
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
            yield await self.emitter.emit_error(error_msg)


class RetrievedConversionComponent(ProcessingComponent):
    """智能筛选最相关的页面"""
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        retrieved_docs_metadata = self.state.get("retrieved_docs_metadata", [])
        if retrieved_docs_metadata is None:
            retrieved_docs_metadata = []
        if not isinstance(retrieved_docs_metadata, list):
            retrieved_docs_metadata = []

        if retrieved_docs_metadata:
            retrieved_docs_metadata_str = str(retrieved_docs_metadata)
            final_answer = self.state.get("final_answer", "")
            query = self.state.get("sys_query", "")

            yield await self.emitter.emit_node_started("convert_to_retrieved", "正在智能筛选答案来源...\n")
            try:
                d_converter = ResponseGenerator()
                llm_results = await d_converter.retrieved_to_results(query, final_answer, retrieved_docs_metadata_str)

                def extract_ids_from_llm_output(llm_output):
                    logger.info(f"LLM 原始输出: {repr(llm_output)}")
                    cleaned_output = re.sub(r'```(?:json)?\s*|\s*```', '', llm_output)
                    try:
                        result = json.loads(cleaned_output.strip())
                        logger.info(f"解析后JSON对象: {result}")
                        if "ids" in result:
                            return result["ids"]
                    except json.JSONDecodeError as e:
                        logger.warning(f"标准方式解析异常: {e}; llm_output={repr(cleaned_output)}")

                    # ...后续 fallback 逻辑，类似每个 return 位置前加 logging
                    json_pattern = r'\{[^{]*"ids"[^}]*\}'
                    json_match = re.search(json_pattern, cleaned_output)
                    if json_match:
                        try:
                            result = json.loads(json_match.group(0))
                            logger.info(f"正则提取JSON对象: {result}")
                            if "ids" in result:
                                return result["ids"]
                        except json.JSONDecodeError as e:
                            logger.warning(f"正则解析异常: {e}; json部分={json_match.group(0)}")

                    null_pattern = r'"ids"\s*:\s*null'
                    if re.search(null_pattern, cleaned_output):
                        logger.info(f"检测到 ids:null，返回 None")
                        return None

                    array_pattern = r'"ids"\s*:\s*\[(.*?)\]'
                    array_match = re.search(array_pattern, cleaned_output, re.DOTALL)
                    if array_match:
                        array_content = array_match.group(1).strip()
                        logger.info(f"数组部分内容: {array_content}")
                        if not array_content:
                            logger.info("空数组，返回 []")
                            return []
                        quoted_strings = re.findall(r'"([^"]*)"', array_content)
                        if quoted_strings:
                            logger.info(f"提取到 ids 列表: {quoted_strings}")
                            return quoted_strings

                    id_pattern = r'\b(?:ID|id)\d+\b'
                    potential_ids = re.findall(id_pattern, cleaned_output)
                    if potential_ids:
                        logger.info(f"正则找到 ids: {potential_ids}")
                        return potential_ids

                    logger.warning("未找到 id，返回 None")
                    return None

                ids_raw = extract_ids_from_llm_output(llm_results)
                ids = set(ids_raw) if ids_raw is not None else set()
                filtered_metadata = [doc for doc in retrieved_docs_metadata if doc.get('id') in ids] if ids else []
                yield await self.emitter.emit_node_finished(
                    "convert_to_retrieved",
                    "智能筛选答案来源完成",
                    completed=llm_results
                )

                if filtered_metadata:
                    yield await self.emitter.emit_documents_retrieved("", filtered_metadata)
            except Exception as e:
                error_msg = f"智能筛选最相关的页面时出错: {str(e)}"
                logger.error(f"[ERROR] {error_msg}")
                yield await self.emitter.emit_error(error_msg)
        else:
            logger.warning("retrieved_docs_metadata 出现异常为空")
            yield await self.emitter.emit_node_finished(
                "convert_to_retrieved",
                "智能筛选答案来源未完成",
                completed="来源异常为空"
            )
            yield await self.emitter.emit_documents_retrieved("", [])


