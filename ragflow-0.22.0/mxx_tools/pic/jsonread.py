import json
import sys

def visualize_unicode_json(json_str):
    """将包含Unicode转义序列的JSON字符串转换为可读的中文格式"""
    try:
        # 解析JSON
        data = json.loads(json_str)
        
        # 使用ensure_ascii=False确保中文字符正常显示
        formatted_json = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
        
        print("转换后的中文JSON:")
        print("=" * 40)
        print(formatted_json)
        print("=" * 40)
        
        # 提取并显示各个字段
        print("\n字段详情:")
        print("-" * 30)
        if "code" in data:
            print(f"code: {data['code']}")
        
        if "data" in data and isinstance(data["data"], dict):
            for key, value in data["data"].items():
                print(f"{key}: {value}")
        
        return data
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return None
    except Exception as e:
        print(f"转换过程中发生错误: {e}")
        return None

# 要转换的JSON字符串
json_str = r'{"code":0,"data":{"summary":"\u672c\u6587\u6863\u8be6\u7ec6\u63cf\u8ff0\u4e86\u4e00\u4e2a\u57fa\u4e8e\u591a\u667a\u80fd\u4f53\u67b6\u6784\u7684\u8bbe\u8ba1\u65b9\u6848\uff0c\u5305\u62ec\u6838\u5fc3\u67b6\u6784\u548c\u6280\u672f\u9009\u578b\uff0c\u5176\u4e2d\u6838\u5fc3\u67b6\u6784\u5206\u4e3a\u591a\u667a\u80fd\u4f53\u5e95\u5ea7\u3001MCP\u63a5\u53e3\u5c42\u3001\u5de5\u4f5c\u6d41\u5f15\u64ce\u548c\u76d1\u63a7\u8bc4\u4f30\u56db\u4e2a\u90e8\u5206\uff1b\u6280\u672f\u9009\u578b\u65b9\u9762\u9009\u62e9\u4e86FastAPI\u4f5c\u4e3a\u540e\u7aef\u6846\u67b6\uff0c\u4f7f\u7528REST API\u548cWebSocket\u4f5c\u4e3a\u901a\u4fe1\u534f\u8bae\uff0c\u5e76\u91c7\u7528\u4e86RabbitMQ/Redis\u4f5c\u4e3a\u6d88\u606f\u961f\u5217\u3002\u6b64\u5916\uff0c\u6587\u6863\u8fd8\u89c4\u5b9a\u4e86\u57fa\u7840\u529f\u80fd\u548c\u573a\u666f\u9a8c\u6536\u6807\u51c6\uff0c\u660e\u786e\u4e86\u667a\u80fd\u4f53/\u5de5\u5177\u63a5\u5165\u7684\u5177\u4f53\u89c4\u8303\uff0c\u63d0\u4f9b\u4e86\u6587\u6863\u5206\u6790\u667a\u80fd\u4f53\u7684\u4f8b\u5b50\uff0c\u5e76\u8be6\u8ff0\u4e86\u9879\u76ee\u4ea4\u63a5\u573a\u666f\u7684\u5de5\u4f5c\u6d41\u7a0b\u53ca\u5176\u89e6\u53d1\u673a\u5236\u3001\u4ea4\u63a5\u5185\u5bb9\u3001\u8f93\u51fa\u89c4\u8303\u4ee5\u53ca\u4ea4\u63a5\u6210\u529f\u8bc4\u4f30\u7684\u6807\u51c6\u3002","type":"\u5176\u4ed6\u7c7b\u578b"}}'

if __name__ == "__main__":
    result = visualize_unicode_json(json_str)
    
    # if result:
    #     # 如果需要保存到文件
    #     with open("converted_result.json", "w", encoding="utf-8") as f:
    #         json.dump(result, f, ensure_ascii=False, indent=2)
    #     print(f"\n结果已保存到: converted_result.json")