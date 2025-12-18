"""
三列式架构图生成器使用示例
展示如何使用所有功能：左中右三列布局、侧面板、连接线等
"""

import sys
import os
from pathlib import Path

# 添加three_column包到路径
sys.path.append(str(Path(__file__).parent))

from three_column import ThreeColumnArchitectureGenerator, generate_from_config

def create_basic_example():
    """创建基础示例 - 只有中间层级"""
    config = {
        "title": "基础架构图示例",
        "layers": [
            {
                "title": "用户接入层",
                "order": 1,
                "theme": "blue",
                "services": [
                    "Web前端界面",
                    "移动端App",
                    "API网关"
                ]
            },
            {
                "title": "业务逻辑层",
                "order": 2,
                "theme": "green",
                "services": [
                    "用户服务",
                    "订单服务",
                    "支付服务"
                ]
            },
            {
                "title": "数据层",
                "order": 3,
                "theme": "purple",
                "services": [
                    "MySQL数据库",
                    "Redis缓存",
                    "MongoDB文档库"
                ]
            }
        ],
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": False
        }
    }

    return config

def create_full_example():
    """创建完整示例 - 包含左右侧面板"""
    config = {
        "title": "企业级电商系统架构",
        "layers": [
            {
                "title": "用户接入层",
                "order": 1,
                "theme": "blue",
                "services": [
                    "Web商城", "移动App", "小程序",
                    "管理后台", "API网关", "CDN加速"
                ]
            },
            {
                "title": "业务服务层",
                "order": 2,
                "theme": "green",
                "service_groups": [
                    {
                        "type": "default",
                        "services": ["用户中心", "商品服务", "订单服务", "支付服务"]
                    },
                    {
                        "type": "default",
                        "services": ["库存服务", "物流服务", "营销服务", "客服系统"]
                    }
                ]
            },
            {
                "title": "中间件层",
                "order": 3,
                "theme": "yellow",
                "services": [
                    "消息队列", "服务网格", "配置中心",
                    "服务注册", "API限流", "熔断器"
                ]
            },
            {
                "title": "数据存储层",
                "order": 4,
                "theme": "purple",
                "service_groups": [
                    {
                        "type": "database",
                        "services": ["MySQL主库", "MySQL从库", "Redis集群"]
                    },
                    {
                        "type": "database",
                        "services": ["MongoDB", "Elasticsearch", "ClickHouse"]
                    }
                ]
            }
        ],
        "left_panel": {
            "title": "外部系统",
            "enabled": True,
            "width_percentage": 30,
            "theme": "cyan",
            "blocks": [
                {
                    "title": "第三方支付",
                    "content": ["支付宝", "微信支付", "银联支付", "PayPal"],
                    "theme": "cyan"
                },
                {
                    "title": "物流系统",
                    "content": ["顺丰API", "圆通API", "中通API", "京东物流"],
                    "theme": "orange"
                },
                {
                    "title": "外部数据",
                    "content": ["商品数据", "价格监控", "用户画像", "风控系统"],
                    "theme": "pink"
                }
            ]
        },
        "right_panel": {
            "title": "运维监控",
            "enabled": True,
            "width_percentage": 25,
            "theme": "red",
            "blocks": [
                {
                    "title": "监控告警",
                    "content": ["Prometheus", "Grafana", "AlertManager", "钉钉告警"],
                    "theme": "red"
                },
                {
                    "title": "日志收集",
                    "content": ["ELK Stack", "Fluentd", "Filebeat", "日志分析"],
                    "theme": "indigo"
                },
                {
                    "title": "运维工具",
                    "content": ["Jenkins", "Docker", "Kubernetes", "Ansible"],
                    "theme": "gray"
                },
                {
                    "title": "安全防护",
                    "content": ["WAF防火墙", "DDoS防护", "SSL证书", "安全扫描"],
                    "theme": "red"
                }
            ]
        },
        "connections": [
            {
                "from": "left-panel",
                "to": "layer_1",
                "type": "arrow_right",
                "label": "API调用"
            },
            {
                "from": "layer_4",
                "to": "right-panel",
                "type": "arrow_right",
                "label": "监控数据"
            }
        ],
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": True,
            "show_connections": True,
            "center_width_percentage": 55
        }
    }

    return config

def create_ai_system_example():
    """创建AI智能系统架构示例"""
    config = {
        "title": "AI智能客服系统架构",
        "layers": [
            {
                "title": "用户交互层",
                "order": 1,
                "theme": "blue",
                "services": [
                    "Web客服界面", "移动端SDK", "微信机器人",
                    "企业微信", "钉钉机器人", "API接口"
                ]
            },
            {
                "title": "AI服务层",
                "order": 2,
                "theme": "green",
                "services": [
                    "对话管理", "意图识别", "实体抽取",
                    "情感分析", "智能路由", "人工接入"
                ]
            },
            {
                "title": "算法引擎层",
                "order": 3,
                "theme": "purple",
                "service_groups": [
                    {
                        "type": "default",
                        "services": ["BERT模型", "GPT模型", "知识图谱", "向量检索"]
                    }
                ]
            },
            {
                "title": "数据平台层",
                "order": 4,
                "theme": "yellow",
                "service_groups": [
                    {
                        "type": "database",
                        "services": ["对话数据库", "知识库", "用户画像", "训练数据"]
                    }
                ]
            }
        ],
        "left_panel": {
            "title": "数据源",
            "enabled": True,
            "theme": "cyan",
            "blocks": [
                {
                    "title": "业务系统",
                    "content": ["CRM系统", "工单系统", "订单系统", "用户中心"],
                    "theme": "cyan"
                },
                {
                    "title": "外部数据",
                    "content": ["百度百科", "维基百科", "行业知识库", "FAQ文档"],
                    "theme": "orange"
                }
            ]
        },
        "right_panel": {
            "title": "运营支撑",
            "enabled": True,
            "theme": "purple",
            "blocks": [
                {
                    "title": "模型训练",
                    "content": ["模型训练平台", "样本标注", "模型评估", "A/B测试"],
                    "theme": "red"
                },
                {
                    "title": "运营分析",
                    "content": ["对话分析", "满意度统计", "效果评估", "运营报表"],
                    "theme": "indigo"
                },
                {
                    "title": "系统监控",
                    "content": ["服务监控", "性能监控", "异常告警", "日志分析"],
                    "theme": "gray"
                }
            ]
        },
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": True,
            "show_connections": True
        }
    }

    return config

def create_theme_showcase_example():
    """创建主题展示示例 - 专门演示侧面板颜色自定义"""
    config = {
        "title": "三列架构图主题展示",
        "layers": [
            {
                "title": "应用层",
                "order": 1,
                "theme": "blue",
                "services": [
                    "Web应用", "移动应用", "API接口"
                ]
            },
            {
                "title": "服务层",
                "order": 2,
                "theme": "green",
                "services": [
                    "用户服务", "订单服务", "支付服务"
                ]
            },
            {
                "title": "数据层",
                "order": 3,
                "theme": "purple",
                "services": [
                    "关系数据库", "缓存系统", "消息队列"
                ]
            }
        ],
        "left_panel": {
            "title": "外部系统集成",
            "enabled": True,
            "width_percentage": 25,
            "theme": "orange",  # 橙色主题
            "blocks": [
                {
                    "title": "第三方服务",
                    "content": ["支付网关", "短信服务", "邮件服务"],
                    "theme": "orange"
                },
                {
                    "title": "数据源",
                    "content": ["外部API", "文件系统", "云存储"],
                    "theme": "cyan"
                }
            ]
        },
        "right_panel": {
            "title": "运维监控体系",
            "enabled": True,
            "width_percentage": 25,
            "theme": "pink",  # 粉色主题
            "blocks": [
                {
                    "title": "监控指标",
                    "content": ["CPU使用率", "内存占用", "网络流量"],
                    "theme": "red"
                },
                {
                    "title": "日志分析",
                    "content": ["错误日志", "访问日志", "性能日志"],
                    "theme": "indigo"
                },
                {
                    "title": "告警通知",
                    "content": ["邮件告警", "短信告警", "钉钉通知"],
                    "theme": "yellow"
                }
            ]
        },
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": True,
            "show_connections": True,
            "center_width_percentage": 50
        }
    }

    return config

def main():
    """主函数 - 生成所有示例"""
    generator = ThreeColumnArchitectureGenerator()

    # 示例1：基础架构图
    print("生成基础架构图示例...")
    basic_config = create_basic_example()
    basic_html = generator.generate_and_save(
        basic_config,
        "output/basic_architecture.html"
    )
    print("✅ 基础架构图已生成: output/basic_architecture.html")

    # 示例2：完整电商系统架构
    print("\n生成完整电商系统架构...")
    full_config = create_full_example()
    full_html = generator.generate_and_save(
        full_config,
        "output/full_ecommerce_architecture.html"
    )
    print("✅ 电商系统架构已生成: output/full_ecommerce_architecture.html")

    # 示例3：AI智能系统架构
    print("\n生成AI智能系统架构...")
    ai_config = create_ai_system_example()
    ai_html = generator.generate_and_save(
        ai_config,
        "output/ai_system_architecture.html"
    )
    print("✅ AI系统架构已生成: ai_system_architecture.html")

    # 使用便捷函数的示例
    print("\n使用便捷函数生成示例...")
    simple_html = generate_from_config(
        basic_config,
        "output/simple_architecture.html"
    )
    print("✅ 简单架构图已生成: output/simple_architecture.html")

    print(f"\n🎉 所有示例生成完成！")
    print(f"📁 输出目录: output/")
    print(f"🌐 可以在浏览器中打开任意HTML文件查看效果")

if __name__ == "__main__":
    main()
