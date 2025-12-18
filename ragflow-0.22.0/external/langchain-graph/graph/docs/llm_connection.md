### **`ResponseGenerator` 重构计划 (最终版 v3.0)**

#### **1. 简介**
*   **目标:** 统一 `graph/processors/response_generator.py` 文件中的大模型调用逻辑，将所有响应生成功能重构为基于 `generate_stream_answer` 和 `generate_blocking_answer` 两个核心组件。
*   **核心原则:** 
    *   **架构统一:** 将原 `JsonConverter` 的功能完全整合进 `ResponseGenerator` 类，实现代码的集中管理。
    *   **Prompt统一:** **(新)** 废弃 `PromptManager`，所有方法的系统提示词（`final_system_prompt`）均通过从 `utils.prompts.prompt` 导入的常量模板，并使用 `.format()` 方法直接构建。
    *   **错误回退:** **(新)** 所有高阶方法在调用核心组件时，必须传入明确的 `fallback_type`，用于在API调用失败时提供符合上下文的默认响应。

#### **2. 架构理解**
*   项目采用高度组件化的流水线架构，`ResponseGenerator` 在其中扮演被各个组件调用的**核心模型服务**角色。

#### **3. 重构步骤**

**步骤一：清理与准备**
*   **操作：** 彻底移除 `graph/processors/response_generator.py` 文件底部被注释掉的、现已多余的 `JsonConverter` 类定义及其所有相关代码。

**步骤二：重构 `ResponseGenerator` 内的方法**
*   我将依次添加或重构文件中的所有API方法，并确保其接口与实现均符合最新要求。

*   **2.1 `generate_document_summary` (流式/非流式)**
    *   **架构上下文:** 由 `MultiFileKnowledgeBaseQueryComponent` 调用。
    *   **接口签名:** 
        *   `async def generate_document_summary(self, document_content: str, query: str) -> AsyncGenerator[str, None]:`
        *   `async def generate_document_summary_bulk(self, document_content: str, query: str) -> str:`
    *   **新实现:** 
        *   `final_system_prompt`: 使用 `DOCUMENT_SUMMARY_PROMPT.format(query=query, document=document_content)` 构建。
        *   `sys_query`: 固定为 `f"请根据我的问题 '{query}' 总结这篇文档的内容。"`。
        *   `fallback_type`: `'DOCUMENT_SUMMARY'`
        *   分别调用 `generate_stream_answer` 和 `generate_blocking_answer`。

*   **2.2 `generate_error_explanation` (流式)**
    *   **架构上下文:** 由 `ErrorHandlingComponent` 调用。
    *   **接口签名:** `async def generate_error_explanation(self, error_message: str, error_type: str, model_name: str = None) -> AsyncGenerator[str, None]:`
    *   **新实现:**
        *   `final_system_prompt`: 使用 `ERROR_EXPLANATION_PROMPT.format(error_message=error_message)` 构建。
        *   `sys_query`: 固定为 `f"请解释这个错误：{error_message}"`。
        *   `fallback_type`: `'ERROR_EXPLANATION'`
        *   调用 `generate_stream_answer`。

*   **2.3 `generate_enhanced_query` (流式)**
    *   **架构上下文:** 由 `QueryEnhancementComponent` 调用。
    *   **接口签名:** `async def generate_enhanced_query(self, query: str, conversation_history: list = None, model_name: str = None) -> AsyncGenerator[str, None]:`
    *   **新实现:** 
        *   **Prompt 策略:** 遵循 `RETRIEVAL_ENHANCEMENT_PROMPT` 的格式要求，将 `conversation_history` 整理为字符串，连同 `current_date` 等信息一同传入。
        *   `final_system_prompt`: **(新)** 设置为一个空字符串或通用指令，因为主要的指令和格式已在 `sys_query` 中定义。
        *   `sys_query`: 完整地填入由 `RETRIEVAL_ENHANCEMENT_PROMPT.format(...)` 构建好的字符串。
        *   `fallback_type`: `'ENHANCED_QUERY'`
        *   调用 `generate_stream_answer`。

*   **2.4 `convert_to_json` (流式, 新增至 `ResponseGenerator`)**
    *   **架构上下文:** 由 `...JsonConversionComponent` 调用。
    *   **接口签名:** `async def convert_to_json(self, content: str, output_body: str) -> AsyncGenerator[str, None]:`
    *   **新实现:**
        *   `final_system_prompt`: 直接使用 `CONVERT_TO_JSON_PROMPT` 常量。
        *   `sys_query`: 构建一个包含 `output_body`（示例）和 `content`（待转换内容）的结构化字符串。
        *   `fallback_type`: `'JSON_CONVERT'`
        *   调用 `generate_stream_answer`。

*   **2.5 `retrieved_to_results` (非流式, 新增至 `ResponseGenerator`)**
    *   **架构上下文:** 由 `RetrievedConversionComponent` 调用。
    *   **接口签名:** `async def retrieved_to_results(self, sys_query: str, final_answer: str, retriever_content: str) -> str:`
    *   **新实现:**
        *   `final_system_prompt`: 设置为空字符串，因为所有指令都在用户查询中。
        *   `sys_query`: 使用 `relevant_metadata.format(QUESTION=sys_query, ANSWER=final_answer, METADATA_LIST=retriever_content, qwords="")` 构建。
        *   `fallback_type`: `'RETRIEVAL_RESULTS'`
        *   调用 `generate_blocking_answer`。

#### **4. 预期收益**
*   **统一性:** 所有模型调用和Prompt构建都遵循统一、明确的规范。
*   **清晰度:** 代码逻辑更清晰，易于维护和扩展。
---
这版计划已完全同步您最新的指令，确保了重构的绝对正确性。 