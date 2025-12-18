from config import logger


def decide_next_step(state: dict) -> str:
    """
    路由函数：检查状态并决定下一个节点的名称。
    """
    print("--- 决策节点 ---")
    if state.get("kb_content"):
        logger.info("状态: 发现'kb_content', 路由到 'generate_answer'")
        return "generate_answer"
    else:
        logger.info("状态: 未发现'kb_content', 路由到 'handle_error'")
        return "handle_error"

def make_next_router(choice: str):
    """
    路由函数：检查状态并决定下一个节点的名称。更灵活的使用
    """
    def router(state: dict):
        if state.get(choice):
            logger.info(f"状态: 发现{choice}, 路由到 'generate_answer'")
            return "generate_answer"
        else:
            logger.info(f"状态: 未发现{choice}, 路由到 'handle_error'")
            return "handle_error"
    return router

def should_run_retrieved_conversion(state: dict) -> str:
    """
    路由函数：判断是否需要执行 RetrievedConversionComponent。
    """
    # 假设 KnowledgeFinalAnswerComponent 出错会在 state['error_msg'] 或 state['final_answer'] 标记
    if not state.get("error_msg"):
        logger.info("答案生成无错误，进入 retrieved_conversion")
        return "retrieved_conversion"
    else:
        logger.info("答案生成有错误，流程结束")
        return "__end__"

def route_after_preprocessing(state: dict) -> str:
    """
    预处理后进行路由：检查预处理是否成功。
    """
    if state.get("preprocessing_failed"):
        return "handle_error"
    else:
        return "document_classifier"

def route_after_classification(state: dict) -> str:
    """根据文档分类结果决定下一步"""
    if "论文" in state.get("classification", "其他类型"):
        return "summary_extraction"
    else:
        return "summary_generator"

def route_after_invoice_classification(state: dict) -> str:
    """根据发票分类结果决定下一步"""
    invoice_category = state.get("invoice_category", "其他")
    # 如果是需要校验的类型，则进入知识库查询，否则直接进行合规检查
    if "差旅" in invoice_category or "交通" in invoice_category or "补助" in invoice_category:
        return "kb_query"
    else:
        return "compliance_check"


def uav_weather_router(state: dict) -> str:
    """
    无人机工作流路由：检查天气API调用是否成功。
    """
    weather_data = state.get("weather_data", {})
    if weather_data:
        logger.info("天气数据获取成功，路由到 'flight_analyzer'")
        return "flight_analyzer"
    else:
        logger.warning("天气数据获取失败，流程结束")
        state["final_answer"] = f"未能查询到 '{state.get('standardized_address', '未知地点')}' 的天气信息，请更换地点或稍后重试。"
        return "__end__"

def route_after_invoice_extraction(state: dict) -> str:
    """
    发票结构化提取后的分支路由：
    - 如果存在 empty_invoice_data，则直接输出
    - 否则，进入 classify_invoice 正常流程
    """
    if state.get("empty_invoice_data"):
        return "empty_invoice_data"
    return "classify_invoice"
