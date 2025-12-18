"""
独立HTML包生成示例
展示如何使用 generate_standalone_html_package 函数生成包含所有静态资源的完整HTML包
"""

import sys
import os
from pathlib import Path

# 添加three_column包到路径
sys.path.append(str(Path(__file__).parent))

from three_column import generate_standalone_html_package


def create_simple_config():
    """创建简单配置示例"""
    return {
        "title": "简单架构图",
        "layers": [
            {
                "title": "前端层",
                "order": 1,
                "theme": "blue",
                "services": ["Web界面", "移动App", "API网关"]
            },
            {
                "title": "服务层",
                "order": 2,
                "theme": "green",
                "services": ["用户服务", "订单服务", "支付服务"]
            },
            {
                "title": "数据层",
                "order": 3,
                "theme": "purple",
                "services": ["MySQL", "Redis", "MongoDB"]
            }
        ],
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": False
        }
    }


def create_full_config():
    """创建完整配置示例，包含侧面板"""
    return {
        "title": "企业级系统架构",
        "layers": [
            {
                "title": "用户接入层",
                "order": 1,
                "theme": "blue",
                "services": ["Web前端", "移动App", "小程序", "API网关"]
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
                "title": "数据存储层",
                "order": 3,
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
            "width_percentage": 25,
            "theme": "cyan",
            "blocks": [
                {
                    "title": "第三方支付",
                    "content": ["支付宝", "微信支付", "银联支付"],
                    "theme": "cyan"
                },
                {
                    "title": "物流系统",
                    "content": ["顺丰API", "圆通API", "中通API"],
                    "theme": "orange"
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
                    "content": ["Prometheus", "Grafana", "AlertManager"],
                    "theme": "red"
                },
                {
                    "title": "日志分析",
                    "content": ["ELK Stack", "Fluentd", "Filebeat"],
                    "theme": "indigo"
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
                "from": "layer_3",
                "to": "right-panel",
                "type": "arrow_right",
                "label": "监控数据"
            }
        ],
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": True,
            "show_connections": True,
            "center_width_percentage": 50
        }
    }


def demo_generate_html_string():
    """演示生成HTML字符串（不保存到文件）"""
    print("🚀 演示：生成HTML字符串")

    config = create_simple_config()

    # 生成HTML字符串
    html_content = generate_standalone_html_package(config)

    print(f"✅ 成功生成HTML内容，长度: {len(html_content)} 字符")
    print(f"📄 HTML包含了所有必要的CSS和JavaScript")
    print(f"🎯 可以直接保存为.html文件或通过HTTP响应返回")

    return html_content


def demo_save_to_file():
    """演示直接保存到文件"""
    print("\n📁 演示：直接保存到文件")

    # 确保输出目录存在
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # 示例1：简单配置
    simple_config = create_simple_config()
    html_content = generate_standalone_html_package(
        simple_config,
        "output/simple_standalone.html"
    )
    print("✅ 简单架构图已生成: output/simple_standalone.html")

    # 示例2：完整配置
    full_config = create_full_config()
    html_content = generate_standalone_html_package(
        full_config,
        "output/full_standalone.html"
    )
    print("✅ 完整架构图已生成: output/full_standalone.html")


def demo_api_response_simulation():
    """演示API响应场景的使用"""
    print("\n🌐 演示：模拟API响应场景")

    def mock_api_handler(request_config):
        """模拟API处理函数"""
        try:
            # 生成独立HTML包
            html_content = generate_standalone_html_package(request_config)

            # 模拟HTTP响应
            response = {
                "status": "success",
                "content_type": "text/html",
                "html": html_content,
                "size": len(html_content)
            }
            return response

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    # 测试API调用
    config = create_simple_config()
    response = mock_api_handler(config)

    if response["status"] == "success":
        print(f"✅ API调用成功")
        print(f"📊 内容类型: {response['content_type']}")
        print(f"📏 HTML大小: {response['size']} 字节")
        print(f"💡 可以直接返回给前端，无需额外的静态资源")
    else:
        print(f"❌ API调用失败: {response['message']}")


def demo_custom_theme_config():
    """演示自定义主题配置"""
    print("\n🎨 演示：自定义主题配置")

    custom_config = {
        "title": "智能报销系统技术架构",
        "layers": [
            {
                "title": "用户/外部系统层",
                "order": 1,
                "theme": "blue",
                "services": [
                    "员工报销门户(Web/App)",
                    "财务管理系统",
                    "第三方支付平台",
                    "企业ERP系统"
                ]
            },
            {
                "title": "应用服务层",
                "order": 2,
                "theme": "green",
                "service_groups": [
                    {
                        "type": "default",
                        "services": ["报销单管理", "审批工作流引擎", "合规校验服务"]
                    },
                    {
                        "type": "default",
                        "services": ["风险控制服务", "报表分析服务", "审计日志服务"]
                    }
                ]
            },
            {
                "title": "AI能力层",
                "order": 3,
                "theme": "purple",
                "services": [
                    "OCR识别服务",
                    "NLP处理服务",
                    "模型推理服务",
                    "规则引擎服务",
                    "数据标注平台"
                ]
            },
            {
                "title": "数据层",
                "order": 4,
                "theme": "orange",
                "service_groups": [
                    {
                        "type": "database",
                        "services": ["结构化数据(MySQL)", "文档数据(MongoDB)", "缓存(Redis)"]
                    },
                    {
                        "type": "database",
                        "services": ["文件存储(MinIO)", "消息队列(Kafka)", "数据仓库(ClickHouse)"]
                    }
                ]
            }
        ],
        "left_panel": {
            "title": "基础设施",
            "enabled": True,
            "width_percentage": 20,
            "theme": "gray",
            "blocks": [
                {
                    "title": "计算资源",
                    "content": ["Kubernetes集群", "Docker容器", "Serverless"],
                    "theme": "gray"
                },
                {
                    "title": "网络与安全",
                    "content": ["VPC网络", "负载均衡", "WAF防火墙"],
                    "theme": "red"
                }
            ]
        },
        "right_panel": {
            "title": "开发运维",
            "enabled": True,
            "width_percentage": 20,
            "theme": "cyan",
            "blocks": [
                {
                    "title": "CI/CD",
                    "content": ["GitLab CI", "Jenkins", "ArgoCD"],
                    "theme": "cyan"
                },
                {
                    "title": "监控告警",
                    "content": ["Prometheus", "Grafana", "ELK"],
                    "theme": "red"
                },
                {
                    "title": "API管理",
                    "content": ["Kong网关", "Swagger UI", "API版本控制"],
                    "theme": "indigo"
                }
            ]
        },
        "connections": [
            {
                "from": "layer_1",
                "to": "layer_2",
                "type": "arrow_right",
                "label": "API调用"
            },
            {
                "from": "layer_2",
                "to": "layer_3",
                "type": "arrow_right",
                "label": "AI服务调用"
            },
            {
                "from": "layer_3",
                "to": "layer_4",
                "type": "arrow_right",
                "label": "数据存取"
            },
            {
                "from": "left-panel",
                "to": "layer_4",
                "type": "arrow_right",
                "label": "资源供给"
            },
            {
                "from": "right-panel",
                "to": "layer_2",
                "type": "arrow_left",
                "label": "运维管理"
            }
        ],
        "layout_config": {
            "direction": "bottom-to-top",
            "enable_side_panels": True,
            "show_connections": True,
            "center_width_percentage": 60
        }
    }

    html_content = generate_standalone_html_package(
        custom_config,
        "output/custom_theme_standalone.html"
    )
    print("✅ 自定义主题架构图已生成: output/custom_theme_standalone.html")


def main():
    """主函数 - 运行所有演示"""
    print("=" * 60)
    print("🎯 独立HTML包生成器使用演示")
    print("=" * 60)

    # 演示1：生成HTML字符串
    # demo_generate_html_string()
    #
    # # 演示2：保存到文件
    # demo_save_to_file()
    #
    # # 演示3：API响应场景
    # demo_api_response_simulation()

    # 演示4：自定义主题
    demo_custom_theme_config()

    print("\n" + "=" * 60)
    print("🎉 所有演示完成！")
    print("=" * 60)
    print("\n📖 使用说明:")
    print("1. generate_standalone_html_package(config) - 返回HTML字符串")
    print("2. generate_standalone_html_package(config, 'path.html') - 保存到文件")
    print("\n✨ 特点:")
    print("• 包含所有CSS和JavaScript，无需外部依赖")
    print("• 可以直接在浏览器中打开")
    print("• 适合API响应、邮件附件、离线使用等场景")
    print("• 支持所有原有功能：主题、侧面板、连接线、交互控制等")
    print("• 🆕 新增：每层级和侧面板可独立设置主题")
    print("• 🔧 修复：中间层背景色控制问题")
    print("• 🔧 修复：连接线控制功能")
    print("\n🧪 测试提示:")
    print("- 打开生成的HTML文件")
    print("- 测试右侧面板中每个层级和侧面板的独立主题选择")
    print("- 测试中间层背景色自定义功能")
    print("- 测试连接线隐藏/显示功能")


if __name__ == "__main__":
    main()
