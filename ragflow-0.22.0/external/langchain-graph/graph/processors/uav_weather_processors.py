"""
无人机气象飞行智能助手的原子业务处理器
"""
import json
from typing import Any, Dict, AsyncGenerator

from graph import EventEmitter
from graph.processors.response_generator import ResponseGenerator
from utils.client.weather import get_weather
from utils.prompts.uav_weather_prompts import ADDRESS_STANDARDIZATION_PROMPT, FLIGHT_STABILITY_ANALYSIS_PROMPT
from config import get_config


class ProcessingComponent:
    """处理流程的基础组件"""
    def __init__(self, state: Dict[str, Any], emitter: EventEmitter):
        self.state = state
        self.emitter = emitter
        self.config = get_config()

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行组件的处理逻辑"""
        raise NotImplementedError("子类必须实现此方法")
class AddressStandardizationComponent(ProcessingComponent):
    """
    地址标准化处理器
    使用LLM将用户输入的地址进行格式化。
    """
    def __init__(self, state, emitter):
        super().__init__(state, emitter)
        self.node_name = "address_standardization"

    async def process(self):

        model_name = self.state.get("model_name",None)
        yield await self.emitter.emit_node_started(self.node_name, "正在进行地址标准化...")

        user_query = self.state.get("sys_query", "")
        if not user_query:
            yield await self.emitter.emit_error("用户输入为空，无法进行地址标准化。")
            self.state["standardized_address"] = ""
            return

        # 使用ResponseGenerator来调用LLM
        response_generator = ResponseGenerator()
        llm_response = ""
        yield await self.emitter.emit_message("正在提取并标准化地址:")
        async for token in response_generator.generate_stream_answer(
            sys_query=user_query,
            final_system_prompt=ADDRESS_STANDARDIZATION_PROMPT,
            temperature=0.1,
            fallback_type='NORMAL_ANSWER',
            model_name = model_name
        ):
            llm_response +=  token
            yield await self.emitter.emit_message(token)
        yield await self.emitter.emit_message("\n")
        self.state["standardized_address"] = llm_response.strip()

        yield await self.emitter.emit_node_finished(self.node_name, "地址标准化完成")


class WeatherToolComponent(ProcessingComponent):
    """
    天气查询工具处理器
    调用外部API获取指定地点的天气信息。
    """
    def __init__(self, state, emitter):
        super().__init__(state, emitter)
        self.node_name = "weather_tool"

    async def process(self):
        yield await self.emitter.emit_node_started(self.node_name, "正在查询天气信息...")

        location = self.state.get("standardized_address", "")
        if not location:
            yield await self.emitter.emit_error("地址信息为空，无法查询天气。", "location")
            self.state["weather_data"] = {}
            return

        weather_data = await get_weather(location)
        self.state["weather_data"] = weather_data

        if not weather_data:
            yield await self.emitter.emit_message(f"未能查询到 '{location}' 的天气信息。\n")
        # else:
        #     yield await self.emitter.emit_message(f"成功获取 '{location}' 的天气信息。")

        yield await self.emitter.emit_node_finished(self.node_name, "天气查询完成")


class FlightAnalysisComponent(ProcessingComponent):
    """
    飞行影响分析处理器
    根据天气情况，使用LLM分析对无人机飞行的影响并生成报告。
    """
    def __init__(self, state, emitter):
        super().__init__(state, emitter)
        self.node_name = "flight_analysis"

    async def process(self):
        model_name = self.state.get("model_name",None)
        yield await self.emitter.emit_node_started(self.node_name, "正在分析天气对飞行的影响...")

        location = self.state.get("standardized_address", "")
        weather_data = self.state.get("weather_data", {})

        if not weather_data:
            yield await self.emitter.emit_error("天气数据为空，无法进行分析。", "无人机")
            self.state["final_answer"] = "由于未能获取天气信息，无法生成飞行建议。"
            return

        # 将天气数据格式化为字符串，以便LLM理解
        weather_data_str = json.dumps(weather_data, ensure_ascii=False, indent=4)

        # 准备带填充的prompt
        prompt = FLIGHT_STABILITY_ANALYSIS_PROMPT.format(
            location=location,
            weather_data=weather_data_str
        )

        # 使用ResponseGenerator来调用LLM
        response_generator = ResponseGenerator()
        final_answer = ""
        async for token in response_generator.generate_stream_answer(
            sys_query="请分析如下天气对无人机飞行的影响：" + weather_data_str,
            final_system_prompt=prompt,
            temperature=0.1,
            model_name = model_name,
            fallback_type='NORMAL_ANSWER'
        ):
            final_answer += token
            yield await self.emitter.emit_message(token)

        self.state["final_answer"] = final_answer
        # yield await self.emitter.emit_message("飞行影响分析报告已生成。")
        yield await self.emitter.emit_node_finished(self.node_name, "飞行影响分析报告已生成", result=final_answer)
