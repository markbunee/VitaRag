# graph/workflow/node_functions.py

from graph.processors.doc_processor import (
    FileExtractionComponent,
    QueryEnhancementComponent,
    SingleFileKnowledgeBaseQueryComponent,
    MultiFileKnowledgeBaseQueryComponent,  # 导入新组件
    RetrievedConversionComponent, AnswerJsonConversionComponent,
)
from graph.processors.general_processor import (
    KnowledgeFinalAnswerComponent,
    ErrorHandlingComponent,
)
from graph.processors.oa_invoice_processor import (
    GetOAExpenseDataComponent,
    ExtractOAInvoiceDataComponent,
    InvoiceClassifierComponent,

    ComplianceCheckComponent
)
from graph.processors.summary_extractor import (
    DocumentValidationComponent,
    TextLimitComponent,
    DocumentClassifierComponent,
    SummaryExtractorComponent,
    SummaryGeneratorComponent,
    FinalResponseComponent,
)
from graph.processors.uav_weather_processors import (
    AddressStandardizationComponent,
    WeatherToolComponent,
    FlightAnalysisComponent,
)

async def run_component(component_class, state, emitter):
    """一个通用的组件执行器"""
    component = component_class(state, emitter)
    # 在 LangGraph 中，节点通常返回状态更新，但这里我们保持原有的原地更新模式
    # 为了保持生成器特性，我们依然需要迭代
    async for event in component.process():
        yield event

# --- 为每个组件创建节点函数 ---

async def file_extraction_node(state, emitter):
    async for event in run_component(FileExtractionComponent, state, emitter):
        yield event

async def query_enhancement_node(state, emitter):
    async for event in run_component(QueryEnhancementComponent, state, emitter):
        yield event

async def kb_query_node(state, emitter):
    async for event in run_component(SingleFileKnowledgeBaseQueryComponent, state, emitter):
        yield event

async def multi_file_kb_query_node(state, emitter):
    """多文件知识库查询的节点包装器"""
    async for event in run_component(MultiFileKnowledgeBaseQueryComponent, state, emitter):
        yield event

async def generate_answer_node(state, emitter):
    # 这个节点可以一次性运行成功路径的所有组件
    success_components = [
        KnowledgeFinalAnswerComponent,
        # AnswerJsonConversionComponent, # 暂时保持注释
        # RetrievedConversionComponent,
    ]
    for comp_class in success_components:
        async for event in run_component(comp_class, state, emitter):
            yield event
async def convert_json_node(state, emitter):
    async for event in run_component(AnswerJsonConversionComponent, state, emitter):
        yield event

async def handle_error_node(state, emitter):
    async for event in run_component(ErrorHandlingComponent, state, emitter):
        yield event

async def retrieved_conversion_node(state, emitter):
    """结果溯源处理节点的包装器"""
    async for event in run_component(RetrievedConversionComponent, state, emitter):
        yield event

# #####################################################################
# OA 发票校验工作流节点
# #####################################################################

async def get_oa_expense_data_node(state, emitter):
    """获取OA报销单据数据的节点"""
    async for event in run_component(GetOAExpenseDataComponent, state, emitter):
        yield event

async def extract_oa_invoice_data_node(state, emitter):
    """提取发票结构化数据的节点"""
    async for event in run_component(ExtractOAInvoiceDataComponent, state, emitter):
        yield event

async def invoice_classifier_node(state, emitter):
    """发票分类的节点"""
    async for event in run_component(InvoiceClassifierComponent, state, emitter):
        yield event

async def oa_kb_query_node(state, emitter):
    """OA场景下知识库查询的节点 - 复用SingleFileKnowledgeBaseQueryComponent"""
    # 参数映射：将OA场景的参数映射到SingleFileKnowledgeBaseQueryComponent的参数
    if "invoice_category" in state:
        state["sys_query"] = state["invoice_category"]
    
    # 清空文件相关参数，因为OA发票校验不需要文件过滤
    state["file_names"] = []
    state["tags"] = []
    
    # 使用SingleFileKnowledgeBaseQueryComponent进行查询
    async for event in run_component(SingleFileKnowledgeBaseQueryComponent, state, emitter):
        # 将节点名称从 "single_file_processing" 改为 "kb_query" 以适配OA工作流
        if isinstance(event, dict) and event.get("events") == "node_started" and event.get("node") == "single_file_processing":
            event["node"] = "kb_query"
            event["message"] = "正在检索OA报销制度知识库..."
        elif isinstance(event, dict) and event.get("events") == "node_finished" and event.get("node") == "single_file_processing":
            event["node"] = "kb_query"
            event["message"] = "OA报销制度知识库检索完成"
        yield event
    
    # 数据对齐：确保错误信息字段与原有组件一致
    if "last_error" in state and "error_msg" not in state:
        state["error_msg"] = state["last_error"]

async def compliance_check_node(state, emitter):
    """合规性检查的节点"""
    async for event in run_component(ComplianceCheckComponent, state, emitter):
        yield event

# --- For SummaryExtractorProcessor ---

async def document_preprocessing_node(state, emitter):
    """
    运行文件提取、验证和文本限制的聚合节点。
    """
    # 1. 文档提取
    async for event in run_component(FileExtractionComponent, state, emitter):
        yield event
    if state.get("error_msg"):
        state["preprocessing_failed"] = True
        return

    # 2. 文档验证
    async for event in run_component(DocumentValidationComponent, state, emitter):
        yield event
    if not state.get("is_valid", False):
        state["preprocessing_failed"] = True
        return

    # 3. 文本长度限制
    async for event in run_component(TextLimitComponent, state, emitter):
        yield event

async def document_classifier_node(state, emitter):
    """文档分类节点的包装器"""
    async for event in run_component(DocumentClassifierComponent, state, emitter):
        yield event

async def summary_extraction_node(state, emitter):
    """论文摘要提取节点的包装器"""
    async for event in run_component(SummaryExtractorComponent, state, emitter):
        yield event

async def summary_generator_node(state, emitter):
    """通用摘要生成节点的包装器"""
    async for event in run_component(SummaryGeneratorComponent, state, emitter):
        yield event

async def final_response_node(state, emitter):
    """最终响应生成节点的包装器"""
    async for event in run_component(FinalResponseComponent, state, emitter):
        yield event


# #####################################################################
# 无人机气象飞行智能助手工作流节点
# #####################################################################

async def uav_address_standardizer_node(state, emitter):
    """地址标准化节点的包装器"""
    async for event in run_component(AddressStandardizationComponent, state, emitter):
        yield event


async def uav_weather_tool_node(state, emitter):
    """天气查询工具节点的包装器"""
    async for event in run_component(WeatherToolComponent, state, emitter):
        yield event


async def uav_flight_analyzer_node(state, emitter):
    """飞行影响分析节点的包装器"""
    async for event in run_component(FlightAnalysisComponent, state, emitter):
        yield event
        
async def empty_invoice_data_node(state, emitter):
    """
    直接输出结构化数据节点
    """
    data = state.get("empty_invoice_data", {})
    # 使用 emit_event 发送自定义事件
    yield await emitter.emit_event("empty_invoice_data", {"data": data})
    yield await emitter.emit_complete("未提取到有效的OCR内容，已直接返回结构化数据")