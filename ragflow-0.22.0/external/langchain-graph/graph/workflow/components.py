# graph/workflow/components.py
from typing import Dict, Any, AsyncGenerator, Callable
from graph.base_processor import BaseProcessor
from graph.processors import (
    FileExtractionComponent,
    QueryEnhancementComponent,
    MultiFileParallelQueryComponent,
    KnowledgeFinalAnswerComponent,
    RetrievedConversionComponent, AnswerJsonConversionComponent, GeneralFinalAnswerComponent, JsonConversionComponent
)
# 导入我们新创建的节点和路由函数
from .node_functions import (
    empty_invoice_data_node,
    file_extraction_node,
    query_enhancement_node,
    kb_query_node,
    generate_answer_node,
    handle_error_node,
    retrieved_conversion_node,
    multi_file_kb_query_node,
    # for SummaryExtractorProcessor
    document_preprocessing_node,
    document_classifier_node,
    summary_extraction_node,
    summary_generator_node,
    final_response_node,  # 导入OA工作流的新节点
    get_oa_expense_data_node,
    extract_oa_invoice_data_node,
    invoice_classifier_node,
    oa_kb_query_node,
    compliance_check_node,
    convert_json_node,  # 确保错误处理节点也被导入
    # for UAV Weather Assistant
    uav_address_standardizer_node,
    uav_weather_tool_node,
    uav_flight_analyzer_node
)
from .router import (
    route_after_invoice_extraction,
    should_run_retrieved_conversion,
    # for SummaryExtractorProcessor
    route_after_preprocessing,
    route_after_classification, make_next_router,
    # 导入OA工作流的新路由
    # for UAV Weather Assistant
    uav_weather_router
)
from abc import ABC, abstractmethod

class BaseGraphProcessor(BaseProcessor, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = {}  # type: Dict[str, Any]
        self.nodes = {}  # type: Dict[str, Callable]

    @abstractmethod
    def setup_graph(self):
        """子类必须实现，声明节点和流程结构"""
        pass
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        self.setup_graph()
        current_node_name = self.graph["__start__"]
        while current_node_name != "__end__":
            node_function = self.nodes.get(current_node_name)
            if not node_function:
                raise ValueError(f"图定义错误：找不到名为 '{current_node_name}' 的节点")
            async for event in node_function(self.state, self.emitter):
                yield event
            next_step_or_router = self.graph.get(current_node_name)
            if callable(next_step_or_router):
                current_node_name = next_step_or_router(self.state)
            else:
                current_node_name = next_step_or_router
        yield await self.emitter.emit_complete("数据处理完成")

class SingleFileProcessor(BaseGraphProcessor):
    """
    单文件处理器 (采用类 LangGraph 的图结构)
    """

    def setup_graph(self):
        """
        声明式地定义工作流图。
        这替代了原有的 setup_components。
        """
        # 1. 定义所有可能的节点（注册）
        self.nodes = {
            "file_extraction": file_extraction_node,
            "query_enhancement": query_enhancement_node,
            "kb_query": kb_query_node,
            "generate_answer": generate_answer_node,
            "retrieved_conversion": retrieved_conversion_node,
            "handle_error": handle_error_node,
        }

        # 2. 定义图的结构（边）
        self.graph = {
            "__start__": "file_extraction", # 定义入口节点
            "file_extraction": "query_enhancement",
            "query_enhancement": "kb_query",
            "kb_query": make_next_router("kb_content"),  # 这是一个条件边，指向一个决策函数
            "generate_answer": should_run_retrieved_conversion,  # 新增条件边
            "retrieved_conversion": "__end__",  # 新节点
            "handle_error": "__end__",  # 失败路径的终点
        }


class MultiFileProcessor(BaseGraphProcessor):
    """多文件处理器 (采用类 LangGraph 的图结构)"""

    def setup_graph(self):
        """多文件工作流图"""
        self.nodes = {
            "file_extraction": file_extraction_node,
            "query_enhancement": query_enhancement_node,
            "multi_file_kb_query": multi_file_kb_query_node,
            "generate_answer": generate_answer_node,
            "retrieved_conversion": retrieved_conversion_node,
            "handle_error": handle_error_node,
        }

        self.graph = {
            "__start__": "file_extraction",
            "file_extraction": "query_enhancement",
            "query_enhancement": "multi_file_kb_query",
            "multi_file_kb_query": make_next_router("contrastive_content"),
            "generate_answer": should_run_retrieved_conversion,
            "retrieved_conversion": "__end__",
            "handle_error": "__end__",
        }

class MultiFileParallelProcessor(BaseProcessor):
    """多文件并行处理器"""
    def setup_components(self):
        self.add_component(FileExtractionComponent)
        self.add_component(QueryEnhancementComponent)
        self.add_component(MultiFileParallelQueryComponent)
        self.add_component(KnowledgeFinalAnswerComponent)
        self.add_component(AnswerJsonConversionComponent)
        self.add_component(RetrievedConversionComponent)

class UploadedFileProcessor(BaseProcessor):
    """上传文件处理器,如果当前任务只需要线性处理，则简单串联各组件即可"""
    def setup_components(self):
        self.add_component(FileExtractionComponent)
        self.add_component(KnowledgeFinalAnswerComponent)
        self.add_component(AnswerJsonConversionComponent)

class GeneralResponseProcessor(BaseProcessor):
    """通用问答节点"""
    def setup_components(self):
        self.add_component(GeneralFinalAnswerComponent)

class JsonConvertProcessor(BaseProcessor):
    """摘要标签提取处理器"""
    def setup_components(self):
        self.add_component(JsonConversionComponent)


class SummaryExtractorProcessor(BaseGraphProcessor):
    """摘要标签提取处理器 - 采用声明式图工作流"""
    def setup_graph(self):
        """声明式地定义摘要提取工作流图"""
        # 1. 注册所有需要的节点
        self.nodes = {
            "document_preprocessing": document_preprocessing_node,
            "document_classifier": document_classifier_node,
            "summary_extraction": summary_extraction_node,
            "summary_generator": summary_generator_node,
            "final_response": final_response_node,
            "handle_error": handle_error_node,
        }

        # 2. 定义图的结构和流程
        self.graph = {
            "__start__": "document_preprocessing",
            "document_preprocessing": route_after_preprocessing,
            "document_classifier": route_after_classification,
            "summary_extraction": "final_response",
            "summary_generator": "final_response",
            "final_response": "__end__",
            "handle_error": "__end__",
        }


# #####################################################################
# OA 发票校验工作流 (Graph Workflow)
# #####################################################################

class OAInvoiceValidateProcessor(BaseGraphProcessor):
    """
    OA发票报销+知识库自动校验工作流 (图模式版本)。
    该工作流通过定义一个图来编排任务，支持根据发票类型进行条件判断。
    """
    def setup_graph(self):
        """定义OA发票校验的图结构"""
        # 1. 注册所有节点
        self.nodes = {
            "get_oa_data": get_oa_expense_data_node,
            "extract_invoice": extract_oa_invoice_data_node,
            "empty_invoice_data": empty_invoice_data_node,  # 新增分支节点
            "classify_invoice": invoice_classifier_node,
            "kb_query": oa_kb_query_node,
            "compliance_check": compliance_check_node,
            "handle_error": handle_error_node,
            "convert_to_json": convert_json_node
        }

        # 2. 声明图的边和路由
        self.graph = {
            "__start__": "get_oa_data",
            "get_oa_data": "extract_invoice",
            "extract_invoice": route_after_invoice_extraction,  # 这里用路由函数
            "empty_invoice_data": "__end__",  # 直接终止或自定义后续
            # classify_invoice后无条件进入kb_query
            "classify_invoice": "kb_query",
            # 知识库查询后，必然进入合规检查
            "kb_query": "compliance_check",
            # 合规检查后的convert_to_json是流程的终点
            "compliance_check": "convert_to_json",
            "convert_to_json": "__end__",
            # 错误处理也是终点
            "handle_error": "__end__",
        }

class OAInvoiceValidateFromOADataProcessor(BaseGraphProcessor):
    """
    从oa_data原始数据开始的OA发票校验工作流
    """
    def setup_graph(self):
        self.nodes = {
            "extract_invoice": extract_oa_invoice_data_node,
            "empty_invoice_data": empty_invoice_data_node,  # 新增分支节点
            "classify_invoice": invoice_classifier_node,
            "kb_query": oa_kb_query_node,
            "compliance_check": compliance_check_node,
            "handle_error": handle_error_node,
            "convert_to_json": convert_json_node
        }
        self.graph = {
            "__start__": "extract_invoice",
            "extract_invoice": route_after_invoice_extraction,  # 这里用路由函数
            "empty_invoice_data": "__end__",  # 直接终止或自定义后续
            "classify_invoice": "kb_query",
            "kb_query": "compliance_check",
            "compliance_check": "convert_to_json",
            "convert_to_json": "__end__",
            "handle_error": "__end__",
        }

# #####################################################################
# 无人机气象飞行智能助手工作流 (Graph Workflow)
# #####################################################################

class UAVWeatherGraphProcessor(BaseGraphProcessor):
    """
    无人机气象飞行智能助手工作流。
    该工作流实现了地址标准化、天气查询、条件判断和飞行影响分析的完整流程。
    """
    def setup_graph(self):
        """定义无人机助手的图结构"""
        # 1. 注册所有节点
        self.nodes = {
            "address_standardizer": uav_address_standardizer_node,
            "weather_tool": uav_weather_tool_node,
            "flight_analyzer": uav_flight_analyzer_node,
            "handle_error": handle_error_node,  # 复用通用的错误处理节点
        }

        # 2. 声明图的边和路由
        self.graph = {
            "__start__": "address_standardizer",
            "address_standardizer": "weather_tool",
            "weather_tool": uav_weather_router,  # 条件路由
            "flight_analyzer": "__end__",
            "handle_error": "__end__",
        }

# #####################################################################
# 原子组件 (Atomic Components)
# #####################################################################
