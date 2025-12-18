"""
外部API调用封装
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from config import logger


def parse_weather_data(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    从BeautifulSoup对象中解析天气数据，并附带3小时未来预报。
    """
    script_tag = soup.find('script', text=re.compile(r'window.tplData'))
    if not script_tag:
        logger.error("在HTML中未找到包含天气数据的 'window.tplData' script 标签。")
        return {}
    json_data_match = re.search(r'window.tplData = ({.*?});', script_tag.string, re.DOTALL)
    if not json_data_match:
        logger.error("在script标签中未通过正则表达式匹配到天气JSON数据。")
        return {}
    try:
        json_data = json.loads(json_data_match.group(1))
        weather = json_data.get('weather')
        if not weather:
            logger.error("解析出的JSON数据中缺少 'weather' 键。")
            return {}

        # ------- 处理24小时预报 -------
        forecasts = []
        forecast_data = json_data.get('24_hour_forecast', {})
        info_list = forecast_data.get('info', [])
        # 当前时间转换成"YYYYMMDDHH"便于比较
        now = datetime.now()
        now_key = now.strftime("%Y%m%d%H")
        # 选取当前时刻之后的3个小时预报
        # 先找到当前小时在列表里的位置
        target_indexes = []
        for idx, entry in enumerate(info_list):
            hour_str = entry.get('hour', '')
            if hour_str >= now_key:
                # 找到第1个及之后
                target_indexes = list(range(idx, min(idx+3, len(info_list))))
                break
        # 如果没找到（可能数据源时间比当前旧），取第一个及其后两个
        if not target_indexes:
            target_indexes = list(range(0, min(3, len(info_list))))

        for i in target_indexes:
            entry = info_list[i]
            hour_str = entry.get('hour')
            # 格式化时间（如“2025071412”->“2025-07-14 12:00”）
            try:
                date_fmt = datetime.strptime(hour_str, "%Y%m%d%H")
                hour_fmt = date_fmt.strftime("%Y-%m-%d %H:00")
            except Exception:
                hour_fmt = hour_str
            forecasts.append({
                "hour": hour_fmt,
                "weather": entry.get('weather', 'N/A'),
                "temperature": entry.get('temperature', 'N/A'),
                "wind_direction": entry.get('wind_direction', 'N/A'),
                "wind_power": entry.get('wind_power', 'N/A')
            })

        result = {
            "current_time": weather.get("update_time", datetime.now().strftime("%Y-%m-%d %H:%M")),
            "wind_power": weather.get('wind_power', 'N/A'),
            "wind_direction": weather.get('wind_direction', 'N/A'),
            "temperature": weather.get('temperature', 'N/A'),
            "humidity": weather.get('humidity', 'N/A'),
            "weather_condition": weather.get('weather', 'N/A'),
            "hourly_forecast_3h": forecasts
        }
        logger.info(f"成功从页面解析出天气数据: {result}")
        return result
    except json.JSONDecodeError:
        logger.error("解析天气数据时发生JSON解码错误。")
        return {}

def _fetch_weather_data_sync(location: str) -> Dict[str, Any]:
    """
    通过网页抓取同步获取天气数据。
    这是一个内部同步函数，应通过 get_weather 中的异步包装器调用。
    """
    base_url = "https://weathernew.pae.baidu.com/weathernew/pc"
    params = {"query": f"{location} 天气", "srcid": "4982"}
    try:
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Referer": "https://www.baidu.com/",
            "accept-language": "zh-CN,zh;q=0.9,or;q=0.8,zh-TW;q=0.7",
        }
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 如果状态码不是 200, 则引发HTTPError

        soup = BeautifulSoup(response.text, 'html.parser')
        return parse_weather_data(soup)

    except requests.Timeout:
        logger.error(f"连接天气服务超时: {location}")
        return {}
    except requests.RequestException as e:
        logger.error(f"获取天气数据时发生网络请求错误 for {location}: {e}")
        return {}
    except Exception as e:
        logger.exception(f"获取 {location} 天气数据时发生未知错误")
        return {}


async def get_weather(location: str) -> Dict[str, Any]:
    """
    通过网页抓取异步获取天气信息。
    它在单独的线程中运行同步的抓取函数以避免阻塞asyncio事件循环。

    Args:
        location: 标准化后的地理位置名称
    Returns:
        Dict: 包含天气信息的字典，失败则返回空字典
    """
    if not location:
        logger.warning("get_weather收到了空的location参数。")
        return {}

    logger.info(f"开始为 '{location}' 异步获取天气数据...")
    loop = asyncio.get_running_loop()
    weather_data = await loop.run_in_executor(
        None, _fetch_weather_data_sync, location
    )
    if weather_data:
        logger.info(f"成功获取到 '{location}' 的天气数据。")
    else:
        logger.warning(f"未能获取到 '{location}' 的天气数据。")
    return weather_data


if __name__ == "__main__":
    async def main():
        location = "广州"
        weather_info = await get_weather(location.strip())
        if weather_info:
            print(f"{location} 当前天气：")
            for k, v in weather_info.items():
                print(f"{k}: {v}")
        else:
            print(f"未能获取到 {location} 的天气数据。")

    # 运行异步主程序
    asyncio.run(main())
