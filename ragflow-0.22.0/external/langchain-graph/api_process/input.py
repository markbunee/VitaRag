"""
输入数据模型定义，用于FastAPI请求验证
"""
import json
import uuid
from typing import List, Optional, Union

from fastapi import Form, UploadFile, File
from pydantic import BaseModel, Field

from config import get_config
def filter_empty_string_list(lst):
    # 针对只含空字符串、中文引号和单双引号等特殊情况
    return [] if isinstance(lst, list) and len(lst) == 1 and lst[0].strip("“”‘’'\" ") == "" else lst

# 此类用于Form表单提交时的验证
class DocumentQueryForm:
    def __init__(
            self,
            sys_query: str = Form(..., description="用户的问题"),
            system_prompt: Optional[str] = Form(None, description="可选的系统提示词"),
            files: List[UploadFile] = File([], description="用户上传的文件列表"),
            file_names: str = Form("[]", description="知识库的文件名称列表（非上传文件），JSON格式"),
            tags: str = Form("[]", description="知识库的标签列表，JSON格式"),
            knowledge_base_type: str = Form("ufrag", description="输入ufrag / ragflow 可切换知识库类型，默认ufrag"),
            kb_names: str = Form("[]", description="知识库名称列表，JSON格式"),
            temperature:float = Form(0.1,description="大模型温度设置，控制最终回复的随机性", ge=0.0, le=1.0),
            top_k: int = Form(30, description="检索分片数量", ge=1, le=100),
            top_n: int = Form(3, description="重排后保留的文档分片数量", ge=1, le=20),
            key_weight: float = Form(0.8, description="关键词权重", ge=0.0, le=1.0),
            input_body: str = Form("", description="数据资产接口返回的数据"),
            output_body: str = Form("", description="限定json转换示例结构，当且仅当启用文件上传、知识库检索时可用"),
            task_type: str = Form("default", description="任务类型（default、sql暂时无用）"),
            model_name: str = Form("", description="模型名称（用于模型切换）"),
            force_ocr: Optional[bool] = Form(None, description="对于上传的文件是否使用OCR，None表示使用全局配置"),
            kb_token: str = Form("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MjQ2MjM3NDcwOH0.CsnK7wAQPZrTDsgmu-Ls5fYqKUDC-_e8k65FXG2PvDc", description="小智文档的token"),
            session_id:str = Form("", description="对话id"),
            conversation_history: str = Form("[]", description="对话历史，JSON格式，包含多个消息，每个消息有role和content"),

    ):
        config = get_config()
        self.sys_query = sys_query
        self.file_names = filter_empty_string_list(json.loads(file_names))
        self.tags = filter_empty_string_list(json.loads(tags))
        self.knowledge_base_type = knowledge_base_type
        self.kb_names = json.loads(kb_names)
        self.top_k = top_k
        self.top_n = top_n
        self.key_weight = key_weight
        self.input_body = input_body
        self.system_prompt = system_prompt
        self.files = files
        self.output_body = output_body
        self.task_type = task_type
        self.temperature = temperature
        self.model_name = model_name or config.COT_LLM_MODELS[0]
        self.conversation_history = json.loads(conversation_history)
        self.force_ocr = force_ocr
        self.kb_token = kb_token
        self.session_id = session_id



# 此类用于JSON请求提交时的验证
class DocumentQueryInput(BaseModel):
    """
    文档查询输入模型 (用于JSON格式请求)
    """
    file_names: List[str] = Field(default=[], description="输入的文件名称列表")
    kb_names: List[str] = Field(default=[], description="知识库名称列表")
    top_k: int = Field(default=30, description="检索分片数量", ge=1, le=100)
    top_n: int = Field(default=3, description="重排后保留的文档分片数量", ge=1, le=20)
    key_weight: float = Field(default=0.8, description="关键词权重", ge=0.0, le=1.0)
    input_body: str = Field(default="", description="数据资产接口返回的数据")
    system_prompt: Optional[str] = Field(default=None, description="可选的系统提示词")
    sys_query: str = Field(..., description="用户的问题")
    model_name: Optional[str] = Field(default="qwen-14b", description="模型名称（用于模型切换）")
    kb_token: str = Form("", description="小智文档的token"),
    conversation_history: Optional[List[dict]] = Field(
        default=None,
        description="对话历史，包含多个消息，每个消息有role和content"
    )
    force_ocr: Optional[bool] = Field(
        default=None,
        description="是否强制使用OCR，None表示使用全局配置"
    )


# API接口定义
class SummaryExtractorForm:
    """摘要标签提取生成表单"""
    def __init__(
            self,
            files: List[UploadFile] = File(..., description="需要处理的文档文件"),
            session_id: str = Form("", description="会话ID，用于文件管理"),
            kb_token: str = Form("",description="解析器的token"),
            stream: bool = Form(True, description="是否流式返回，true=流式，false=一次性返回")
    ):
        self.files = files
        self.session_id = session_id or str(uuid.uuid4())
        self.kb_token = kb_token
        self.stream = stream


class Convert2Json:
    """
    json转换
    """
    def __init__(
            self,
            sys_query: str = Field(..., description="输入的文本"),
            example_json: str = Field(..., description="AI学习的json示例"),
            model_name: Optional[str] = Field(default="qwen-14b", description="模型名称（用于模型切换）"),
            stream: bool = Form(False, description="是否流式返回，true=流式，false=一次性返回"),
            session_id: str = Form("", description="会话ID"),
    ):
        config = get_config()
        self.sys_query = sys_query
        self.example_json = example_json
        self.model_name = model_name or config.COT_LLM_MODELS[0]
        self.stream = stream
        self.session_id = session_id or str(uuid.uuid4())

class OAInvoiceValidateForm:
    def __init__(
        self,
        detail_code: str = Form(..., description="报销单号"),
        force_ocr: str = Form("false", description="是否强制OCR，true/false字符串"),
        stream: Optional[bool] = Form(True, description="是否流式返回，默认True"),
        # 知识库检索参数
        kb_names: str = Form("[\"smartkb_76\"]", description="知识库名称列表，JSON格式"),
        kb_token: str = Form("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MjQ2MjM3NDcwOH0.CsnK7wAQPZrTDsgmu-Ls5fYqKUDC-_e8k65FXG2PvDc", description="知识库token"),
        top_k: int = Form(40, description="检索分片数量", ge=1, le=100),
        top_n: int = Form(3, description="重排后保留的文档分片数量", ge=1, le=20),
        key_weight: float = Form(0.8, description="关键词权重", ge=0.0, le=1.0),
        # 模型参数
        model_name: str = Form(None, description="模型名称"),
        temperature: float = Form(0.1, description="模型温度", ge=0.0, le=1.0)
    ):
        config = get_config()
        self.detail_code = detail_code
        self.force_ocr = force_ocr
        self.stream = stream
        self.kb_names = json.loads(kb_names)
        self.kb_token = kb_token
        self.top_k = top_k
        self.top_n = top_n
        self.key_weight = key_weight
        self.model_name = model_name
        self.temperature = temperature

class OAInvoiceValidateInput(BaseModel):
    detail_code: str = Field(..., description="报销单号")
    force_ocr: str = Field("false", description="是否强制OCR，true/false字符串")
    stream: Optional[bool] = Field(True, description="是否流式返回，默认True")
    # 知识库检索参数
    kb_names: List[str] = Field(default=["smartkb_76"], description="知识库名称列表")
    kb_token: str = Field("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MjQ2MjM3NDcwOH0.CsnK7wAQPZrTDsgmu-Ls5fYqKUDC-_e8k65FXG2PvDc", description="知识库token")
    top_k: int = Field(default=40, description="检索分片数量", ge=1, le=100)
    top_n: int = Field(default=3, description="重排后保留的文档分片数量", ge=1, le=20)
    key_weight: float = Field(default=0.8, description="关键词权重", ge=0.0, le=1.0)
    # 模型参数
    model_name: str = Field(default="qwen-14b", description="模型名称")
    temperature: float = Field(default=0.1, description="模型温度", ge=0.0, le=1.0)
    

class OAInvoiceValidateRawForm:
    def __init__(
        self,
        oa_data: str = Form(..., description="OA接口返回的原始数据，支持JSON字符串"),
        stream: Optional[bool] = Form(True, description="是否流式返回，默认True"),
        # 知识库检索参数
        kb_names: str = Form("[\"smartkb_76\"]", description="知识库名称列表，JSON格式"),
        kb_token: str = Form("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MjQ2MjM3NDcwOH0.CsnK7wAQPZrTDsgmu-Ls5fYqKUDC-_e8k65FXG2PvDc", description="知识库token"),
        top_k: int = Form(40, description="检索分片数量", ge=1, le=100),
        top_n: int = Form(3, description="重排后保留的文档分片数量", ge=1, le=20),
        key_weight: float = Form(0.8, description="关键词权重", ge=0.0, le=1.0),
        # 模型参数
        model_name: str = Form(None, description="模型名称"),
        temperature: float = Form(0.1, description="模型温度", ge=0.0, le=1.0),
        user: str = Form("admin", description="报销人")
    ):

        self.oa_data = oa_data
        self.stream = stream
        self.kb_names = json.loads(kb_names)
        self.kb_token = kb_token
        self.top_k = top_k
        self.top_n = top_n
        self.key_weight = key_weight
        self.model_name = model_name
        self.temperature = temperature
        self.user = user