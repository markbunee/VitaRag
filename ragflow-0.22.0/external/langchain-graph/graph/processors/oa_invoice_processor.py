import httpx
import json
import asyncio
from datetime import datetime

from utils.prompts.oa_invoice_validate import INVOICE_CLASSIFY_PROMPT, COMPLIANCE_CHECK_PROMPT
from config import get_config, logger
from graph.processors.response_generator import ResponseGenerator



class GetOAExpenseDataComponent:
    def __init__(self, state, emitter):
        self.state = state
        self.emitter = emitter

    async def process(self):
        config = get_config()
        detail_code = self.state.get("detail_code")
        force_ocr = self.state.get("force_ocr", False)
        if isinstance(force_ocr, str):
            force_ocr = force_ocr.lower() == "true"
        api_url = getattr(config, "OA_EXPENSE_API_URL", "http://localhost:8000/api/expense/ai-records")
        if api_url.endswith("/api/expense/ai-records"):
            base_url = api_url[:api_url.index("/api/expense/ai-records")]
        else:
            base_url = api_url
        endpoint = base_url + "/api/expense/ai-records"
        params = {"detail_code": detail_code}
        json_body = {
            "pageNum": config.OA_EXPENSE_API_DEFAULTS.get("pageNum", 1),
            "pageSize": config.OA_EXPENSE_API_DEFAULTS.get("pageSize", 10),
            "force_ocr": force_ocr
        }

        yield await self.emitter.emit_node_started("get_oa_expense_data", "正在获取OA报销单数据...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(endpoint, params=params, json=json_body, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                self.state["oa_data"] = data

                yield await self.emitter.emit_node_finished(
                    "get_oa_expense_data",
                    "OA报销单数据获取完成"
                )
        except Exception as e:
            error_msg = f"获取OA报销单数据失败: {str(e)}"
            self.state["error_msg"] = error_msg
            yield await self.emitter.emit_error(error_msg)

class ExtractOAInvoiceDataComponent:
    def __init__(self, state, emitter):
        self.state = state
        self.emitter = emitter
    async def process(self):
        data = self.state.get("oa_data", {})
        # 适配：如果是字符串，尝试转为dict
        import json
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception as e:
                error_msg = f"oa_data参数不是合法的JSON字符串: {str(e)}"
                self.state["error_msg"] = error_msg
                yield await self.emitter.emit_error(error_msg)

        if not isinstance(data, dict):
            error_msg = "oa_data参数必须是字典或可转为字典的JSON字符串"
            self.state["error_msg"] = error_msg
            yield await self.emitter.emit_error(error_msg)

        infos, ocr_results, minio_files, explains, tp_ocrs = [], [], [], "", []

        yield await self.emitter.emit_node_started("extract_invoice_data", "正在提取发票数据...")

        try:
            for item in data.get("data", []):
                item_data = json.dumps({k: v for k, v in item.items() if k != "ai_extract_content"}, ensure_ascii=False)
                infos.append(item_data)
                if item.get("minio_file_list"):
                    try:
                        file_list = json.loads(item.get("minio_file_list"))
                        minio_files.extend(file_list)
                    except Exception:
                        pass
                ocr_content_list = []
                if item.get("ai_extract_content"):
                    try:
                        ai_content = json.loads(item.get("ai_extract_content"))
                        for content_item in ai_content:
                            if "ocr_result" in content_item and "raw_content" in content_item["ocr_result"]:
                                ocr_content_list.append(content_item["ocr_result"]["raw_content"])
                    except Exception:
                        ocr_content_list.append("Error parsing AI content")
                ocr_content = "\n".join(ocr_content_list)
                name = item.get("name", "")
                explain = item.get("explain", "")
                explains += explain + "\n"
                formatted_ocr = f"\n{name} - \n{ocr_content}"
                ocr_results.append(formatted_ocr)
                tp_ocrs.append(ocr_content)
            self.state["infos"] = "\n".join(infos)
            self.state["ocr_result"] = "\n".join(ocr_results)
            self.state["minio_file_list"] = "\n".join(minio_files)
            self.state["explains"] = explains
            self.state["tp_ocrs"] = "".join(tp_ocrs)

            # 新增：tp_ocrs为空的分支处理
            if not tp_ocrs or (isinstance(tp_ocrs, list) and len(tp_ocrs) == 0):
                self.state["empty_invoice_data"] = {
                    "infos": self.state.get("infos", ""),
                    "ocr_result": self.state.get("ocr_result", ""),
                    "minio_file_list": self.state.get("minio_file_list", ""),
                    "explains": self.state.get("explains", ""),
                    "tp_ocrs": "".join(tp_ocrs) if tp_ocrs else ""
                }
                # 不设置error_msg，直接设置empty_invoice_data标志，让路由函数处理

            yield await self.emitter.emit_node_finished(
                "extract_invoice_data",
                "发票数据提取完成"
            )
        except Exception as e:
            error_msg = f"提取接口数据失败: {str(e)}"
            self.state["error_msg"] = error_msg
            yield await self.emitter.emit_error(error_msg)

class InvoiceClassifierComponent:
    def __init__(self, state, emitter):
        self.state = state
        self.emitter = emitter
    async def process(self):
        # 获取数据并确保不为空
        ocr_result = self.state.get("ocr_result", "")
        explains = self.state.get("explains", "")

        # 如果关键数据为空，提供默认值
        if not ocr_result.strip():
            ocr_result = "暂无OCR识别结果"
        if not explains.strip():
            explains = "暂无发票说明"

        prompt = __import__('jinja2').Template(INVOICE_CLASSIFY_PROMPT).render(
            ocr_result=ocr_result,
            explains=explains
        )
        model_name = self.state.get("model_name", "qwen-14b")
        temperature = self.state.get("temperature", 0.1)
        conversation_history = self.state.get("conversation_history", None)
        response_generator = ResponseGenerator()

        yield await self.emitter.emit_node_started("invoice_classify", "正在进行发票分类...")

        try:
            # 流式生成发票分类结果
            result = ""
            async for token in response_generator.generate_stream_answer(
                sys_query="请根据提供的发票信息进行分类",
                final_system_prompt=prompt,
                temperature=temperature,
                model_name=model_name,
                conversation_history=None
            ):
                result += token
                yield await self.emitter.emit_message(token)
                await asyncio.sleep(0.005)

            self.state["invoice_category"] = result

            yield await self.emitter.emit_node_finished(
                "invoice_classify",
                "发票分类完成",
                completed=result
            )
        except Exception as e:
            error_msg = f"发票分类失败: {str(e)}"
            self.state["error_msg"] = error_msg
            yield await self.emitter.emit_error(error_msg)

class ComplianceCheckComponent:
    def __init__(self, state, emitter):
        self.state = state
        self.emitter = emitter
    async def process(self):
        # 获取数据并确保不为空
        current_date = datetime.now().strftime('%Y-%m-%d')
        user = self.state.get("user", "")
        infos = self.state.get("infos", "")
        ocr_result = self.state.get("ocr_result", "")
        kb_content = self.state.get("kb_content", "")

        # 如果关键数据为空，提供默认值
        if not user.strip():
            user = "未知用户"
        if not infos.strip():
            infos = "暂无报销信息"
        if not ocr_result.strip():
            ocr_result = "暂无OCR识别结果"
        if not kb_content.strip():
            kb_content = "暂无知识库内容"

        prompt = __import__('jinja2').Template(COMPLIANCE_CHECK_PROMPT).render(
            current_date=current_date,
            user=user,
            infos=infos,
            ocr_result=ocr_result,
            kb_content=kb_content
        )
        model_name = self.state.get("model_name", "qwen-14b")
        temperature = self.state.get("temperature", 0.1)
        conversation_history = self.state.get("conversation_history", None)
        response_generator = ResponseGenerator()

        yield await self.emitter.emit_node_started("compliance_check", "正在进行合规校验...")

        try:
            # 流式生成合规校验结果
            result = ""
            async for token in response_generator.generate_stream_answer(
                sys_query="请根据提供的发票信息和知识库内容进行合规校验",
                final_system_prompt=prompt,
                temperature=temperature,
                model_name=model_name,
                conversation_history=None
            ):
                result += token
                yield await self.emitter.emit_message(token)
                await asyncio.sleep(0.005)

            self.state["compliance_result"] = result

            yield await self.emitter.emit_node_finished(
                "compliance_check",
                "合规校验完成",
                completed=result
            )

            # 生成最终响应
            yield await self.emitter.emit_final_message(result)
        except Exception as e:
            error_msg = f"合规校验失败: {str(e)}"
            self.state["error_msg"] = error_msg
            yield await self.emitter.emit_error(error_msg)
