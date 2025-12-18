# graph/processors/base_processor.py
import uuid
import asyncio
from typing import Dict, Any, AsyncGenerator, List, Optional

from .event_emitter import EventEmitter



# from graph.workflow import components  # 导入新组件基类

class BaseProcessor:
    """所有处理器的基类"""
    def __init__(self, initial_state: Dict[str, Any], emitter: EventEmitter = None):
        import copy
        self.state = copy.deepcopy(initial_state)
        self.conversion_id = str(uuid.uuid4())
        # 确保session_id存在
        self.session_id = initial_state.get("session_id", str(uuid.uuid4()))
        self.emitter = emitter or EventEmitter(self.conversion_id, self.session_id)
        # 保存组件列表
        self._components = []

    def add_component(self, component_class):
        """添加处理组件到流程中"""
        component = component_class(self.state, self.emitter)
        self._components.append(component)
        return self

    def setup_components(self):
        """设置处理组件，子类需要实现此方法"""
        pass

    # 在create_processor方法中修改
    @staticmethod
    def create_processor(initial_state: Dict[str, Any]):
        """根据状态创建合适的处理器"""
        from graph.workflow.components import (
            SingleFileProcessor, MultiFileProcessor, UploadedFileProcessor,
            MultiFileParallelProcessor,GeneralResponseProcessor, SummaryExtractorProcessor,
            JsonConvertProcessor, OAInvoiceValidateProcessor, UAVWeatherGraphProcessor
        )
        from graph.workflow.components import SingleFileProcessor, MultiFileProcessor, UploadedFileProcessor, MultiFileParallelProcessor,GeneralResponseProcessor, SummaryExtractorProcessor,JsonConvertProcessor

        from graph.workflow.components import OAInvoiceValidateProcessor, OAInvoiceValidateFromOADataProcessor

        # 使用传入的session_id创建emitter
        session_id = initial_state.get("session_id", str(uuid.uuid4()))
        emitter = EventEmitter(str(uuid.uuid4()), session_id)

        # 检查文件路径而不是文件对象
        file_paths = initial_state.get("file_paths", [])
        file_names = initial_state.get("file_names", [])
        tags = initial_state.get("tags", [])
        kb_names = initial_state.get("kb_names",[])
        has_tags_files = bool(file_paths)
        has_kb_names = bool(kb_names)
        has_file_names = bool(file_names)
        has_uploaded_files = bool(tags)
        task_type = initial_state.get("task_type", "default")
        parallel_mode = initial_state.get("parallel_mode", False)

        if task_type == "summary_extract":
            # 摘要标签提取任务
            processor = SummaryExtractorProcessor(initial_state, emitter)
            processor.setup_components()
            return processor
        elif task_type == "oa_invoice_validate":
            # OA发票报销+知识库自动校验
            processor = OAInvoiceValidateProcessor(initial_state, emitter)
            processor = OAInvoiceValidateProcessor(initial_state)
            processor.emitter = emitter
            processor.setup_components()
            return processor
        elif task_type == "oa_invoice_validate_raw":
            # 从oa_data原始数据开始的OA发票校验
            processor = OAInvoiceValidateFromOADataProcessor(initial_state)
            processor.emitter = emitter
            processor.setup_components()
            return processor
        elif task_type == "uav_weather_assistant":
            # 无人机气象飞行智能助手
            processor = UAVWeatherGraphProcessor(initial_state, emitter)
            return processor
        elif task_type == "default":
            if has_uploaded_files and not has_kb_names:
                processor = UploadedFileProcessor(initial_state, emitter)
            elif not has_kb_names and not has_file_names and not has_uploaded_files and not has_tags_files:
                processor = GeneralResponseProcessor(initial_state, emitter)
            else:
                if len(file_names) > 1 or len(tags) > 1:
                    if parallel_mode:
                        processor = MultiFileParallelProcessor(initial_state, emitter)
                    else:
                        processor = MultiFileProcessor(initial_state, emitter)
                else:
                    processor = SingleFileProcessor(initial_state, emitter)

            # 初始化组件
            processor.setup_components()
            return processor
        elif task_type == "sql":
            pass  # SQL处理逻辑
        elif task_type == "convert_to_json":
            processor = JsonConvertProcessor(initial_state, emitter)
            processor.setup_components()
            return processor
    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """处理主流程"""
        try:
            # 连接确认
            yield await self.emitter.emit_node_started("connection", "连接已建立，正在处理数据...")

            # 执行每个组件
            for component in self._components:
                async for event in component.process():
                    yield event

            # 完成通知
            yield await self.emitter.emit_complete("数据处理完成")

        except Exception as e:
            import traceback
            from config import logger
            logger.error(f"[ERROR] 处理错误: {type(e).__name__}")
            traceback.print_exc()
            yield await self.emitter.emit_error(f"处理过程中出现系统错误: {str(e)}", error_type=type(e).__name__)
