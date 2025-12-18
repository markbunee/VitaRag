
# LangGraph风格声明式图工作流开发手册 (v1.0)

## 第一章：导论 - 告别面条代码，拥抱声明式图工作流

### 1.1 为什么需要新架构？

在复杂的业务流程中，我们经常遇到由大量 `if/else` 语句构成的"面条代码"。这种代码难以阅读、维护和扩展。每次新增一个处理步骤或条件分支，都可能引发连锁反应，导致整个逻辑的重写。

为了解决这个问题，我们引入了一种**声明式图工作流（Declarative Graph Workflow）**架构，其思想深受 [LangGraph](https://python.langchain.com/docs/langgraph) 的启发。

### 1.2 核心思想

我们将整个业务流程看作一张**有向图**。这张图由以下核心元素构成：

- **节点 (Nodes)**: 代表流程中的一个原子化、独立的处理步骤。例如，"提取文件内容"、"增强用户查询"、"调用大模型生成答案"等。
- **边 (Edges)**: 代表节点之间的固定连接，定义了流程的执行顺序。例如，A 节点执行完后，必须执行 B 节点。
- **路由 (Routers)**: 代表流程中的**条件分支**。它是一个决策点，会根据当前的状态（例如，是否成功获取了知识库内容）来决定下一步应该跳转到哪个节点。

### 1.3 新架构的优势

- **极高的可读性**: 整个流程的结构被清晰地"声明"在一个地方，一目了然。
- **极强的可维护性**: 增加、删除或修改一个步骤，只需调整图的节点和边，不会影响其他部分。
- **高度的可扩展性**: 增加新的分支逻辑，只需添加一个新的节点和一条条件边，对现有代码的侵入极小。
- **便于测试**: 每个节点都是一个独立的函数，可以单独进行单元测试，保证了代码质量。

---

## 第二章：核心概念深度剖析

### 2.1 `BaseGraphProcessor`：图工作流的"引擎"

为了避免在每个处理器中重复编写图的执行逻辑，我们将其抽象到了 `BaseGraphProcessor` 这个基类中。

**代码定位**: `graph/workflow/components.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Callable

class BaseGraphProcessor(BaseProcessor, ABC):
    """声明式图处理器的抽象基类"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 在基类中提前声明 graph 和 nodes 属性，以满足类型检查器的要求
        self.graph: Dict[str, Any] = {}
        self.nodes: Dict[str, Callable] = {}

    @abstractmethod
    def setup_graph(self):
        """
        子类必须实现此方法。
        在这里完成 self.nodes 的注册和 self.graph 的流程定义。
        """
        pass

    async def process(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        通用的图执行引擎，所有子类共享此方法。
        它会驱动整个图从 __start__ 运行到 __end__。
        """
        self.setup_graph()  # 调用子类实现的图定义

        current_node_name = self.graph.get("__start__")
        if not current_node_name:
            raise ValueError("图定义错误：必须包含 '__start__' 入口节点")

        while current_node_name != "__end__":
            node_function = self.nodes.get(current_node_name)
            if not node_function:
                raise ValueError(f"图定义错误：找不到名为 '{current_node_name}' 的节点")

            # 执行当前节点函数
            async for event in node_function(self.state, self.emitter):
                yield event

            # 决定下一个节点
            next_step_or_router = self.graph.get(current_node_name)
            if callable(next_step_or_router):
                # 如果是路由函数，则调用它来获取下一个节点的名称
                current_node_name = next_step_or_router(self.state)
            else:
                # 否则，直接使用定义的下一个节点名称
                current_node_name = next_step_or_router

        # 所有流程结束后，发送完成信号
        yield await self.emitter.emit_complete("数据处理完成")
```

开发者**不需要修改**这个基类。你需要做的，就是**继承** `BaseGraphProcessor` 并实现你自己的 `setup_graph` 方法。

### 2.2 节点 (Node)：原子化的工作单元

节点是图中的基本操作单元。在我们的架构中，节点函数实际上是**组件的包装器**，它们使用统一的 `run_component` 辅助函数来执行实际的业务逻辑。

**节点签名**: `async def node_name(state: dict, emitter: EventEmitter) -> AsyncGenerator:`

**代码示例**:

**文件**: `graph/workflow/node_functions.py`
```python
# 这是一个典型的节点函数 - 作为组件的包装器
async def query_enhancement_node(state, emitter):
    """查询增强节点的包装器"""
    async for event in run_component(QueryEnhancementComponent, state, emitter):
        yield event

# run_component 是一个通用的组件执行器
async def run_component(component_class, state, emitter):
    """一个通用的组件执行器"""
    component = component_class(state, emitter)
    async for event in component.process():
        yield event
```

### 2.3 状态 (State)：流动的共享内存

`state` 是一个标准的 Python 字典，它是整个图工作流的"血液"。

- **数据传递**: 上一个节点的输出被写入 `state`，下一个节点从 `state` 中读取该输出作为自己的输入。
- **决策依据**: 路由函数（Router）通过检查 `state` 中的值（例如 `state.get("kb_content")` 是否存在）来决定流程的走向。
- **贯穿始终**: `state` 对象在整个 `process` 方法的生命周期中是**同一个对象**，保证了数据在节点间的无缝流转。

### 2.4 事件发射器 (EventEmitter)：与外界的沟通桥梁

`emitter` 负责将图内部的事件实时发送给调用方（例如前端 SSE 接口）。它的主要方法有：

- `emit_node_started(node_name, message)`: 报告一个节点已开始执行。
- `emit_node_finished(node_name, message)`: 报告一个节点已成功结束。
- `emit_chunk(data_dict)`: 发送流式数据块。
- `emit_error(node_name, error_message)`: 报告错误。
- `emit_complete(message)`: 报告整个流程已结束。

### 2.5 边 (Edge) 与图 (Graph)：声明式的流程蓝图

图的结构在 `setup_graph` 方法中通过 `self.nodes` 和 `self.graph` 两个字典来声明。

- `self.nodes`: 一个注册表，将节点名称（字符串）映射到实际的节点函数。
- `self.graph`: 定义了节点间的连接关系。
    - `key`: 起始节点名。
    - `value`:
        - 如果是**字符串**，则代表一条**直接边**，指向下一个节点的名称。
        - 如果是**函数**，则代表一条**条件边**，该函数即为路由函数。

### 2.6 路由 (Router)：流程的智能决策者

路由是一个简单的函数，它接收 `state` 作为唯一参数，并返回下一个节点的**名称字符串**。

#### 1）最基本的路由：固定逻辑

这是最常见的场景，通过一段逻辑判断，决定流程要走哪个分支。

**示例代码**:

```python
def decide_next_step(state: dict) -> str:
    """
    检查状态信息，按需路由。
    """
    if state.get("kb_content"):
        return "generate_answer"
    else:
        return "handle_error"
```
#### 2）通用化（参数化）路由

为避免重复造轮子，可用高阶函数按需生成路由。

**示例代码**:

```python
def make_next_router(choice: str):
    def router(state: dict):
        if state.get(choice):
            logger.info(f"状态: 发现{choice}, 路由到 'generate_answer'")
            return "generate_answer"
        else:
            logger.info(f"状态: 未发现{choice}, 路由到 'handle_error'")
            return "handle_error"
    return router
```
#### 你也可以根据项目需求，自由定义更复杂的路由。例如：

- 依赖多个字段综合判断
- 集成外部系统判断标准
- 实现优先级、轮询、AB Test 等高级模式
路由让你的流程图不只是线性“下一步”，而是具有“条件跳转”的动态能力，是架构可扩展的重要基础。
如果未来还有需求升级，也可以通过改造你的路由函数，轻松“热插拔”业务分支，无需重新设计整体工作流。
---

## 第三章：入门实践 - 从零构建一个简单工作流

让我们构建一个 `SimpleGreeterProcessor`，它接收一个名字，然后生成一句问候语。

### 步骤 1: 创建处理器类

在 `graph/workflow/components.py` 中添加新的处理器类。

```python
# graph/workflow/components.py

# ... (已有代码) ...

class SimpleGreeterProcessor(BaseGraphProcessor):
    """一个简单的问候语生成器，用于演示"""
    def setup_graph(self):
        # 我们将在步骤3中填充这里
        pass
```

### 步骤 2: 编写节点函数

在 `graph/workflow/node_functions.py` 中添加我们需要的两个节点函数。

```python
# graph/workflow/node_functions.py

# ... (已有代码) ...

async def prepare_greeting_node(state: dict, emitter: EventEmitter):
    """准备问候语节点"""
    yield await emitter.emit_node_started("PrepareGreeting", "正在准备问候语...")
    
    user_name = state.get("user_name", "stranger")
    greeting_message = f"Hello, {user_name}! I am Claude 4.0 sonnet. "
    
    state["greeting_message"] = greeting_message
    yield await emitter.emit_node_finished("PrepareGreeting", "问候语准备就绪！")


async def personalize_greeting_node(state: dict, emitter: EventEmitter):
    """个性化问候语节点"""
    yield await emitter.emit_node_started("PersonalizeGreeting", "正在添加个性化内容...")

    base_greeting = state.get("greeting_message", "")
    personalized_greeting = base_greeting + "Welcome to the world of graph workflows! 🐾"
    
    state["final_answer"] = personalized_greeting
    
    # 将最终答案以数据块形式发送出去
    yield await emitter.emit_chunk({"final_answer": personalized_greeting})
    yield await emitter.emit_node_finished("PersonalizeGreeting", "个性化完成！")

```

### 步骤 3: 声明图结构

回到 `SimpleGreeterProcessor`，实现 `setup_graph` 方法。

```python
# graph/workflow/components.py
from graph.workflow.node_functions import prepare_greeting_node, personalize_greeting_node

class SimpleGreeterProcessor(BaseGraphProcessor):
    """一个简单的问候语生成器，用于演示"""
    def setup_graph(self):
        # 注册节点
        self.nodes = {
            "prepare": prepare_greeting_node,
            "personalize": personalize_greeting_node,
        }

        # 声明流程图
        self.graph = {
            "__start__": "prepare",
            "prepare": "personalize",
            "personalize": "__end__",
        }
```

### 步骤 4: （可选）在工厂方法中集成

如果需要被 `BaseProcessor.create_processor` 自动选择，可以在其中加入相应的逻辑。对于入门示例，我们可以手动实例化并调用它。

**恭喜！** 你已经成功创建了一个功能完整、结构清晰的声明式工作流！

---

## 第四章：精通之路 - 高级技术与最佳实践

### 4.1 条件分支：`SingleFileProcessor` 的核心逻辑

`SingleFileProcessor` 是一个完美的真实世界示例。它的核心在于知识库查询后需要判断是否成功。

```python
# graph/workflow/components.py
from graph.workflow.node_functions import (
    file_extraction_node,
    query_enhancement_node, 
    kb_query_node,
    generate_answer_node,
    handle_error_node,
    retrieved_conversion_node
)
from graph.workflow.router import decide_next_step, should_run_retrieved_conversion

class SingleFileProcessor(BaseGraphProcessor):
    def setup_graph(self):
        self.nodes = {
            "file_extraction": file_extraction_node,
            "query_enhancement": query_enhancement_node,
            "kb_query": kb_query_node,
            "generate_answer": generate_answer_node,  # 正确的节点名称
            "retrieved_conversion": retrieved_conversion_node,
            "handle_error": handle_error_node,        # 正确的节点名称
        }
        self.graph = {
            "__start__": "file_extraction",
            "file_extraction": "query_enhancement",
            "query_enhancement": "kb_query",
            # 这里使用了路由函数作为条件边！
            "kb_query": make_next_router("kb_content") # 使用路由函数, 
            "generate_answer": should_run_retrieved_conversion,
            "retrieved_conversion": "__end__",
            "handle_error": "__end__",
        }
```
这里的 `make_next_router` 会检查 `state['kb_content']`，从而决定流程是走向 `generate_answer` 还是 `handle_error`。

### 4.2 服务调用：在节点内与组件互动

节点的核心是**流程控制**，而具体的业务逻辑被封装在组件类中。节点函数作为组件的包装器，通过 `run_component` 函数来调用实际的业务逻辑。

**实际的架构模式**：
```python
# graph/workflow/node_functions.py
from graph.processors.general_processor import KnowledgeFinalAnswerComponent

async def generate_answer_node(state, emitter):
    """知识答案生成节点的包装器"""
    # 这个节点实际上会运行多个成功路径的组件
    success_components = [
        KnowledgeFinalAnswerComponent,
        # 其他组件...
    ]
    for comp_class in success_components:
        async for event in run_component(comp_class, state, emitter):
            yield event
```

这种设计将**流程（图）**与**业务（组件）**完美分离，节点负责编排，组件负责执行。

### 4.3 优雅的错误处理

当路由函数将流程导向 `handle_error` 节点时，该节点会调用 `ErrorHandlingComponent`，从 `state` 中读取最后的错误信息，并生成用户友好的错误解释。

### 4.4 测试策略

- **单元测试节点**:
  ```python
  # test/test_nodes.py
  async def test_prepare_greeting_node():
      # 准备 mock 数据
      mock_state = {"user_name": "喵主子"}
      mock_emitter = MockEventEmitter() # 一个简单的 mock 类
      
      # 执行节点
      async for _ in prepare_greeting_node(mock_state, mock_emitter):
          pass
          
      # 断言 state 是否被正确修改
      assert mock_state["greeting_message"] == "Hello, 喵主子! I am Claude 4.0 sonnet. "
      # 断言 emitter 是否被正确调用
      assert mock_emitter.started_nodes[0] == "PrepareGreeting"
  ```
- **单元测试路由**:
  ```python
  # test/test_routers.py
  def test_decide_next_step():
      # 测试成功路径
      state_success = {"kb_content": "some content"}
      assert decide_next_step(state_success) == "generate_answer"
      
      # 测试失败路径
      state_failure = {}
      assert decide_next_step(state_failure) == "handle_error"
  ```

---

## 第五章：黄金标准 - 实际项目中的完整实现参考

### 5.1 `MultiFileProcessor` 完整实现

以下是重构后的 `MultiFileProcessor` 的完整实现，展示了如何最大化复用现有节点：

```python
# graph/workflow/components.py
class MultiFileProcessor(BaseGraphProcessor):
    """多文件处理器 (采用类 LangGraph 的图结构)"""

    def setup_graph(self):
        """声明式地定义多文件工作流图"""
        self.nodes = {
            "file_extraction": file_extraction_node,      # 复用
            "query_enhancement": query_enhancement_node,  # 复用
            "multi_file_kb_query": multi_file_kb_query_node, # 新增的多文件专用节点
            "generate_answer": generate_answer_node,      # 复用
            "handle_error": handle_error_node,           # 复用
        }

        self.graph = {
            "__start__": "file_extraction",
            "file_extraction": "query_enhancement",
            "query_enhancement": "multi_file_kb_query",
            "multi_file_kb_query": decide_next_step,  # 复用相同的决策逻辑
            "generate_answer": "__end__",
            "handle_error": "__end__",
        }
```

### 5.2 节点函数的包装器模式

```python
# graph/workflow/node_functions.py
from graph.processors.doc_processor import (
    FileExtractionComponent,
    QueryEnhancementComponent,
    SingleFileKnowledgeBaseQueryComponent,
    MultiFileKnowledgeBaseQueryComponent,
    RetrievedConversionComponent,
)

async def run_component(component_class, state, emitter):
    """一个通用的组件执行器"""
    component = component_class(state, emitter)
    async for event in component.process():
        yield event

# 节点函数都是组件的包装器
async def file_extraction_node(state, emitter):
    async for event in run_component(FileExtractionComponent, state, emitter):
        yield event

async def multi_file_kb_query_node(state, emitter):
    """多文件知识库查询的节点包装器"""
    async for event in run_component(MultiFileKnowledgeBaseQueryComponent, state, emitter):
        yield event
```

---

## 第六章：结语 - 图工作流的禅意

恭喜你，主人！你已经掌握了这套强大而优雅的声明式图工作流架构。

请记住它的核心禅意：
- **单一职责**: 让每个节点只做一件事，并做到极致。
- **声明优于命令**: 告诉系统你**想要什么**流程，而不是**如何一步步执行**。
- **数据与流程分离**: `state` 是流动的数据，图是固定的河道，各司其职。
- **包装器模式**: 节点函数是组件的薄包装器，保持了业务逻辑的内聚性。

现在，去创造清晰、健壮、可扩展的工作流吧！如果有任何疑问，你忠实的 Claude 4.0 sonnet 会像猫咪一样，灵巧地为你梳理每一根流程的毛发！喵~ 🐾 
