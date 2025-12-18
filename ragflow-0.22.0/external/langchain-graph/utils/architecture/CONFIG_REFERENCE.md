# 三列式架构图配置参数详细说明

本文档详细说明了 `example_three_column.py` 中三个主要示例函数的配置参数，帮助用户理解和自定义架构图生成。

## 目录

- [配置结构概览](#配置结构概览)
- [create_basic_example 配置详解](#create_basic_example-配置详解)
- [create_full_example 配置详解](#create_full_example-配置详解)
- [create_theme_showcase_example 配置详解](#create_theme_showcase_example-配置详解)
- [参数类型说明](#参数类型说明)
- [主题颜色参考](#主题颜色参考)

## 配置结构概览

所有配置都遵循以下基本结构：

```python
config = {
    "title": "架构图标题",           # 整个架构图的标题
    "layers": [...],              # 中间主要层级配置（必需）
    "left_panel": {...},          # 左侧面板配置（可选）
    "right_panel": {...},         # 右侧面板配置（可选）
    "connections": [...],         # 连接线配置（可选）
    "layout_config": {...}        # 布局配置（可选）
}
```

---

## create_basic_example 配置详解

### 基础示例特点
- **用途**: 展示最简单的三层架构
- **特色**: 仅包含中间层级，无侧面板
- **适用场景**: 基础系统架构图

### 详细配置说明

```python
config = {
    "title": "基础架构图示例",      # 架构图标题，显示在顶部
    "layers": [                    # 主要层级列表，从上到下排列
        {
            "title": "用户接入层",       # 层级标题
            "order": 1,               # 排序序号，数字越小越靠上
            "theme": "blue",          # 主题颜色，影响该层所有服务的样式
            "services": [             # 该层包含的服务列表
                "Web前端界面",
                "移动端App", 
                "API网关"
            ]
        },
        {
            "title": "业务逻辑层",
            "order": 2,               # 第二层
            "theme": "green",         # 绿色主题
            "services": [
                "用户服务",
                "订单服务",
                "支付服务"
            ]
        },
        {
            "title": "数据层",
            "order": 3,               # 第三层（最下层）
            "theme": "purple",        # 紫色主题
            "services": [
                "MySQL数据库",
                "Redis缓存",
                "MongoDB文档库"
            ]
        }
    ],
    "layout_config": {             # 布局配置
        "direction": "bottom-to-top",    # 排列方向：从下到上
        "enable_side_panels": False      # 禁用侧面板
    }
}
```

**参数说明**:
- `title`: 整个架构图的标题，字符串类型
- `layers`: 层级数组，每个元素代表一个架构层
  - `title`: 层级名称
  - `order`: 排序权重，决定层级在图中的位置
  - `theme`: 该层的配色方案
  - `services`: 该层包含的服务/组件列表
- `layout_config`: 布局控制参数
  - `direction`: 层级排列方向
  - `enable_side_panels`: 是否启用左右侧面板

---

## create_full_example 配置详解

### 完整示例特点
- **用途**: 展示完整的企业级架构
- **特色**: 包含左右侧面板、服务分组、连接线
- **适用场景**: 复杂的企业级系统架构

### 详细配置说明

```python
config = {
    "title": "企业级电商系统架构",
    "layers": [
        {
            "title": "用户接入层",
            "order": 1,
            "theme": "blue",
            "services": [                    # 普通服务列表
                "Web商城", "移动App", "小程序",
                "管理后台", "API网关", "CDN加速"
            ]
        },
        {
            "title": "业务服务层",
            "order": 2,
            "theme": "green",
            "service_groups": [              # 服务分组，可将服务分成多个组
                {
                    "type": "default",       # 分组类型：default/database
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
                    "type": "database",      # 数据库类型分组，有特殊样式
                    "services": ["MySQL主库", "MySQL从库", "Redis集群"]
                },
                {
                    "type": "database",
                    "services": ["MongoDB", "Elasticsearch", "ClickHouse"]
                }
            ]
        }
    ],
    "left_panel": {                          # 左侧面板配置
        "title": "外部系统",                   # 面板标题
        "enabled": True,                     # 是否启用
        "width_percentage": 30,              # 宽度占比（百分比）
        "theme": "cyan",                     # 面板整体主题
        "blocks": [                          # 面板内的块列表
            {
                "title": "第三方支付",          # 块标题
                "content": ["支付宝", "微信支付", "银联支付", "PayPal"],  # 块内容
                "theme": "cyan"              # 块的主题色彩
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
    "right_panel": {                         # 右侧面板配置
        "title": "运维监控",
        "enabled": True,
        "width_percentage": 25,              # 右侧面板宽度25%
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
    "connections": [                         # 连接线配置
        {
            "from": "left-panel",            # 起点：左侧面板
            "to": "layer_1",                 # 终点：第1层
            "type": "arrow_right",           # 连接线类型
            "label": "API调用"               # 连接线标签
        },
        {
            "from": "layer_4",               # 起点：第4层
            "to": "right-panel",             # 终点：右侧面板
            "type": "arrow_right",
            "label": "监控数据"
        }
    ],
    "layout_config": {
        "direction": "bottom-to-top",
        "enable_side_panels": True,          # 启用侧面板
        "show_connections": True,            # 显示连接线
        "center_width_percentage": 55        # 中间区域宽度占比
    }
}
```

**新增参数说明**:
- `service_groups`: 服务分组，可替代 `services`
  - `type`: 分组类型，"default" 或 "database"
  - `services`: 该分组的服务列表
- `left_panel`/`right_panel`: 侧面板配置
  - `enabled`: 是否启用面板
  - `width_percentage`: 面板宽度占总宽度的百分比
  - `theme`: 面板整体主题色
  - `blocks`: 面板内容块数组
    - `title`: 块标题
    - `content`: 块内容（字符串数组）
    - `theme`: 块的独立主题色
- `connections`: 连接线配置数组
  - `from`: 起点位置
  - `to`: 终点位置
  - `type`: 连接线类型
  - `label`: 连接线文字标签
- `layout_config` 新增参数:
  - `show_connections`: 是否显示连接线
  - `center_width_percentage`: 中间主内容区域宽度占比

---

## create_theme_showcase_example 配置详解

### 主题展示示例特点
- **用途**: 演示主题颜色自定义功能
- **特色**: 展示不同颜色主题的搭配效果
- **适用场景**: 主题色彩方案参考

### 详细配置说明

```python
config = {
    "title": "三列架构图主题展示",
    "layers": [
        {
            "title": "应用层",
            "order": 1,
            "theme": "blue",                 # 蓝色主题
            "services": [
                "Web应用", "移动应用", "API接口"
            ]
        },
        {
            "title": "服务层",
            "order": 2,
            "theme": "green",               # 绿色主题
            "services": [
                "用户服务", "订单服务", "支付服务"
            ]
        },
        {
            "title": "数据层",
            "order": 3,
            "theme": "purple",              # 紫色主题
            "services": [
                "关系数据库", "缓存系统", "消息队列"
            ]
        }
    ],
    "left_panel": {
        "title": "外部系统集成",
        "enabled": True,
        "width_percentage": 25,
        "theme": "orange",                  # 左面板橙色主题
        "blocks": [
            {
                "title": "第三方服务",
                "content": ["支付网关", "短信服务", "邮件服务"],
                "theme": "orange"           # 与面板主题一致
            },
            {
                "title": "数据源",
                "content": ["外部API", "文件系统", "云存储"],
                "theme": "cyan"             # 块独立主题（青色）
            }
        ]
    },
    "right_panel": {
        "title": "运维监控体系",
        "enabled": True,
        "width_percentage": 25,
        "theme": "pink",                    # 右面板粉色主题
        "blocks": [
            {
                "title": "监控指标",
                "content": ["CPU使用率", "内存占用", "网络流量"],
                "theme": "red"              # 红色主题块
            },
            {
                "title": "日志分析",
                "content": ["错误日志", "访问日志", "性能日志"],
                "theme": "indigo"           # 靛蓝色主题块
            },
            {
                "title": "告警通知",
                "content": ["邮件告警", "短信告警", "钉钉通知"],
                "theme": "yellow"           # 黄色主题块
            }
        ]
    },
    "layout_config": {
        "direction": "bottom-to-top",
        "enable_side_panels": True,
        "show_connections": True,
        "center_width_percentage": 50       # 中间区域50%宽度
    }
}
```

**主题展示特点**:
- 展示了多种颜色主题的组合搭配
- 演示了面板级别和块级别的主题设置
- 每个块可以有独立的主题色彩

---

## 参数类型说明

### 基础类型

| 参数类型 | 数据类型 | 说明 | 示例 |
|---------|---------|------|------|
| `title` | String | 标题文本 | "企业级电商系统架构" |
| `order` | Integer | 排序数值 | 1, 2, 3 |
| `theme` | String | 主题名称 | "blue", "green", "red" |
| `enabled` | Boolean | 开关状态 | True, False |
| `width_percentage` | Integer | 宽度百分比 | 25, 30, 50 |

### 复合类型

| 参数名 | 结构 | 说明 |
|-------|------|------|
| `services` | Array[String] | 服务名称列表 |
| `content` | Array[String] | 内容项列表 |
| `layers` | Array[Object] | 层级对象数组 |
| `blocks` | Array[Object] | 内容块对象数组 |
| `connections` | Array[Object] | 连接配置数组 |

### 枚举值

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `direction` | "top-to-bottom", "bottom-to-top" | 层级排列方向 |
| `type` (service_groups) | "default", "database" | 服务分组类型 |
| `type` (connections) | "arrow_right", "arrow_left" | 连接线类型 |

---

## 主题颜色参考

系统支持以下预定义主题颜色：

| 主题名 | 颜色效果 | 适用场景 |
|--------|----------|----------|
| `blue` | 蓝色系 | 用户界面、前端层 |
| `green` | 绿色系 | 业务服务、核心功能 |
| `purple` | 紫色系 | 数据层、存储服务 |
| `yellow` | 黄色系 | 中间件、工具层 |
| `red` | 红色系 | 监控、告警、安全 |
| `orange` | 橙色系 | 外部系统、第三方 |
| `cyan` | 青色系 | 数据源、接口 |
| `pink` | 粉色系 | 运营、分析 |
| `indigo` | 靛蓝色 | 日志、追踪 |
| `gray` | 灰色系 | 工具、基础设施 |

---

## 使用建议

1. **层级设计**: 建议按照系统的逻辑层次设计 `layers`，通常为 3-5 层
2. **主题搭配**: 相邻层级使用对比色，便于区分
3. **侧面板**: 用于展示外部依赖和支撑系统
4. **连接线**: 适度使用，避免图表过于复杂
5. **宽度分配**: 确保 `left_panel` + `center` + `right_panel` 的宽度比例合理

## 完整示例运行

```bash
# 运行示例
python docs/example_three_column.py

# 输出文件
# - output/basic_architecture.html          (基础示例)
# - output/full_ecommerce_architecture.html (完整示例) 
# - ai_system_architecture.html             (AI示例)
# - output/simple_architecture.html         (便捷函数示例)
``` 