# Day 1 代码示例：环境配置与第一个Agent

## 📁 目录结构
```
day1-环境配置/
├── README.md           # 本文件
├── 1_basic_agent.py    # 最简单的Agent
├── 2_state_graph.py    # StateGraph示例
├── 3_langchain_tools.py # LangChain工具调用
├── 4_deerflow_setup.py  # DeerFlow环境配置
├── requirements.txt     # 依赖列表
└── config/
    └── agent.yaml       # Agent配置文件
```

## 1. 最简单的Agent

```python
# 1_basic_agent.py
"""
最基础的Agent实现示例
演示如何使用LangGraph创建最简单的Agent
"""

from typing import TypedDict, Literal
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: list[str]
    next_action: str


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """决定是否继续执行工具"""
    last_message = state["messages"][-1]
    if "execute" in last_message.lower() or "run" in last_message.lower():
        return "tools"
    return "__end__"


def process_input(state: AgentState) -> AgentState:
    """处理用户输入"""
    return {"messages": state["messages"]}


# 定义工具
def calculator_tool(expression: str) -> str:
    """简单的计算器工具"""
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


# 定义节点
def node_input(state: AgentState) -> AgentState:
    """输入节点"""
    print(f"收到输入: {state['messages'][-1]}")
    return state


def node_tools(state: AgentState) -> AgentState:
    """工具节点"""
    expr = state["messages"][-1]
    result = calculator_tool(expr)
    new_messages = state["messages"] + [result]
    return {"messages": new_messages}


def node_output(state: AgentState) -> AgentState:
    """输出节点"""
    print(f"最终输出: {state['messages'][-1]}")
    return state


def build_graph():
    """构建StateGraph"""
    # 创建图构建器
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("input", node_input)
    graph.add_node("tools", node_tools)
    graph.add_node("output", node_output)
    
    # 添加边
    graph.add_edge(START, "input")
    graph.add_conditional_edges(
        "input",
        should_continue,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    graph.add_edge("tools", "output")
    graph.add_edge("output", END)
    
    return graph.compile()


def main():
    """主函数"""
    print("=" * 50)
    print("最简单的Agent示例")
    print("=" * 50)
    
    # 构建图
    app = build_graph()
    
    # 初始化状态
    initial_state = {
        "messages": ["2 + 3 * 4"],
        "next_action": ""
    }
    
    # 运行
    result = app.invoke(initial_state)
    
    print("\n执行结果:")
    for i, msg in enumerate(result["messages"]):
        print(f"  {i+1}. {msg}")


if __name__ == "__main__":
    main()
```

## 2. StateGraph示例

```python
# 2_state_graph.py
"""
StateGraph状态机示例
演示LangGraph状态管理的核心概念
"""

from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
import operator


class AgentState(TypedDict):
    """带消息历史的状态"""
    messages: Annotated[Sequence[str], add_messages]
    context: dict
    current_step: str


def create_agent_graph():
    """创建完整的Agent图"""
    
    # 定义节点
    def node_start(state: AgentState) -> AgentState:
        """开始节点"""
        print(f"[START] 初始化Agent...")
        return {
            **state,
            "current_step": "start"
        }
    
    def node_process(state: AgentState) -> AgentState:
        """处理节点"""
        print(f"[PROCESS] 处理消息: {state['messages'][-1]}")
        return {
            **state,
            "current_step": "process"
        }
    
    def node_respond(state: AgentState) -> AgentState:
        """响应节点"""
        response = f"Agent响应: 收到 '{state['messages'][-1]}'"
        print(f"[RESPOND] {response}")
        return {
            **state,
            "messages": state["messages"] + [response],
            "current_step": "respond"
        }
    
    def node_end(state: AgentState) -> AgentState:
        """结束节点"""
        print(f"[END] Agent执行完成")
        return {
            **state,
            "current_step": "end"
        }
    
    # 创建图
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("start", node_start)
    graph.add_node("process", node_process)
    graph.add_node("respond", node_respond)
    graph.add_node("end", node_end)
    
    # 设置入口和出口
    graph.set_entry_point("start")
    graph.add_edge("start", "process")
    graph.add_edge("process", "respond")
    graph.add_edge("respond", "end")
    graph.add_edge("end", END)
    
    return graph.compile()


def demonstrate_state_management():
    """演示状态管理"""
    print("\n" + "=" * 50)
    print("StateGraph状态管理示例")
    print("=" * 50)
    
    # 创建图
    app = create_agent_graph()
    
    # 初始状态
    initial_state = {
        "messages": ["Hello, Agent!"],
        "context": {"user_id": "user_001"},
        "current_step": ""
    }
    
    # 执行
    result = app.invoke(initial_state)
    
    print("\n最终状态:")
    print(f"  当前步骤: {result['current_step']}")
    print(f"  消息数量: {len(result['messages'])}")
    print(f"  上下文: {result['context']}")


if __name__ == "__main__":
    demonstrate_state_management()
```

## 3. LangChain工具调用

```python
# 3_langchain_tools.py
"""
LangChain工具调用示例
演示如何定义和使用LangChain工具
"""

from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent


# ============ 方式1：使用@tool装饰器 ============
@tool
def get_weather(city: str) -> str:
    """获取城市天气信息
    
    Args:
        city: 城市名称
        
    Returns:
        天气信息字符串
    """
    # 模拟天气查询
    weather_data = {
        "北京": "晴，25°C",
        "上海": "多云，28°C",
        "深圳": "阵雨，30°C"
    }
    return weather_data.get(city, f"未找到{city}的天气信息")


@tool
def calculator(expression: str) -> str:
    """执行数学计算
    
    Args:
        expression: 数学表达式，如 "2+3*4"
        
    Returns:
        计算结果
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


# ============ 方式2：继承BaseTool ============
class SearchToolInput(BaseModel):
    """搜索工具输入schema"""
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="最大结果数")


class SearchTool(BaseTool):
    """自定义搜索工具"""
    name: str = "web_search"
    description: str = "用于搜索网络信息。输入搜索关键词，返回相关结果。"
    args_schema: Type[BaseModel] = SearchToolInput
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """同步执行"""
        # 模拟搜索结果
        results = [
            f"结果{i}: 关于'{query}'的信息..." 
            for i in range(1, max_results + 1)
        ]
        return "\n".join(results)
    
    async def _arun(self, query: str, max_results: int = 5) -> str:
        """异步执行"""
        return self._run(query, max_results)


class DateTimeTool(BaseTool):
    """日期时间工具"""
    name: str = "get_datetime"
    description: str = "获取当前日期和时间"
    
    def _run(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_agent_with_tools():
    """创建带工具的Agent"""
    
    # 初始化LLM
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # 定义工具列表
    tools = [
        get_weather,
        calculator,
        SearchTool(),
        DateTimeTool()
    ]
    
    # 创建ReAct Agent
    agent = create_react_agent(llm, tools)
    
    return agent


def demonstrate_tools():
    """演示工具调用"""
    print("\n" + "=" * 50)
    print("LangChain工具调用示例")
    print("=" * 50)
    
    # 创建Agent
    agent = create_agent_with_tools()
    
    # 测试不同工具
    test_queries = [
        "北京的天气怎么样？",
        "计算 (15 + 25) * 2",
        "现在几点了？",
        "搜索Python异步编程"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 30)
        
        # 使用流式输出
        for event in agent.stream({"messages": [("user", query)]}):
            for value in event.values():
                if "messages" in value:
                    last_msg = value["messages"][-1]
                    if hasattr(last_msg, "content"):
                        print(f"Agent: {last_msg.content}")


if __name__ == "__main__":
    demonstrate_tools()
```

## 4. DeerFlow环境配置

```python
# 4_deerflow_setup.py
"""
DeerFlow环境配置示例
演示如何配置DeerFlow开发环境
"""

import os
import yaml
from pathlib import Path
from typing import Optional


class DeerFlowConfig:
    """DeerFlow配置管理类"""
    
    DEFAULT_CONFIG = {
        "model": {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        "sandbox": {
            "type": "local",
            "timeout": 300,
            "max_memory_mb": 512
        },
        "tools": {
            "enabled": True,
            "sandbox_enabled": True
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置"""
        self.config = self.DEFAULT_CONFIG.copy()
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, path: str) -> None:
        """从YAML文件加载配置"""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                self._merge_config(self.config, user_config)
    
    def _merge_config(self, base: dict, update: dict) -> None:
        """深度合并配置"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return self.config.copy()


def check_environment():
    """检查环境配置"""
    print("\n" + "=" * 50)
    print("DeerFlow环境检查")
    print("=" * 50)
    
    # 检查Python版本
    import sys
    print(f"Python版本: {sys.version}")
    if sys.version_info < (3, 12):
        print("⚠️ 警告: 建议使用Python 3.12+")
    
    # 检查关键依赖
    required_packages = [
        "langgraph",
        "langchain_openai",
        "langchain_core",
        "pydantic",
        "pyyaml"
    ]
    
    print("\n依赖包检查:")
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (未安装)")
    
    # 检查环境变量
    print("\n环境变量:")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"  OPENAI_API_KEY: {masked_key}")
    else:
        print("  OPENAI_API_KEY: 未设置 (请设置)")
    
    # 测试配置加载
    print("\n配置测试:")
    config = DeerFlowConfig()
    print(f"  模型: {config.get('model.model_name')}")
    print(f"  沙箱类型: {config.get('sandbox.type')}")


def create_sample_config():
    """创建示例配置文件"""
    config = {
        "model": {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 4096,
            "api_key_env": "OPENAI_API_KEY"
        },
        "sandbox": {
            "type": "local",
            "timeout": 300,
            "max_memory_mb": 512,
            "network_enabled": False
        },
        "tools": {
            "enabled": True,
            "sandbox_enabled": True,
            "allowed_paths": ["/tmp/agent", "/home/user/data"]
        },
        "middleware": {
            "chain": [
                "ThreadDataMiddleware",
                "UploadsMiddleware",
                "SandboxMiddleware",
                "ToolErrorHandlingMiddleware"
            ]
        },
        "logging": {
            "level": "INFO",
            "file": "logs/deerflow.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    return config


if __name__ == "__main__":
    # 检查环境
    check_environment()
    
    # 创建示例配置
    print("\n" + "=" * 50)
    print("生成示例配置文件")
    print("=" * 50)
    
    config = create_sample_config()
    
    # 保存到文件
    config_dir = Path(__file__).parent / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "agent.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"配置已保存到: {config_file}")
    
    # 验证配置
    loaded_config = DeerFlowConfig(str(config_file))
    print("\n验证配置加载:")
    print(f"  模型: {loaded_config.get('model.model_name')}")
    print(f"  温度: {loaded_config.get('model.temperature')}")
    print(f"  中间件链: {loaded_config.get('middleware.chain')}")
```

## 5. 配置文件

```yaml
# config/agent.yaml
# DeerFlow Agent 配置文件

model:
  provider: openai
  model_name: gpt-4o-mini
  temperature: 0.7
  max_tokens: 4096
  api_key_env: OPENAI_API_KEY

sandbox:
  type: local
  timeout: 300
  max_memory_mb: 512
  network_enabled: false
  allowed_paths:
    - /tmp/agent
    - /home/user/data

tools:
  enabled: true
  sandbox_enabled: true
  allowed_tools:
    - calculator
    - web_search
    - file_reader

middleware:
  chain:
    - ThreadDataMiddleware
    - UploadsMiddleware
    - SandboxMiddleware
    - ToolErrorHandlingMiddleware
    - ClarificationMiddleware
    - MemoryMiddleware

logging:
  level: INFO
  file: logs/deerflow.log
  max_bytes: 10485760
  backup_count: 5
```

## 6. 依赖列表

```text
# requirements.txt
# Day 1 环境配置示例依赖

# 核心框架
langgraph>=0.0.20
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-core>=0.1.0

# 配置管理
pydantic>=2.0.0
pyyaml>=6.0.0

# 异步支持
aiohttp>=3.9.0
asyncio-throttle>=1.0.0

# 日志和监控
structlog>=23.0.0
prometheus-client>=0.19.0

# 开发工具
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
ruff>=0.1.0
mypy>=1.7.0

# 类型扩展
types-PyYAML>=6.0.0
types-aiohttp>=3.9.0
```

## 📖 运行说明

### 环境准备

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export OPENAI_API_KEY="your-api-key-here"

# 4. 运行示例
python 1_basic_agent.py
python 2_state_graph.py
python 3_langchain_tools.py
python 4_deerflow_setup.py
```

### 学习目标

完成Day 1代码示例后，您将掌握：

1. ✅ 如何创建最简单的LangGraph Agent
2. ✅ StateGraph状态管理机制
3. ✅ LangChain工具定义和使用
4. ✅ DeerFlow环境配置方法
5. ✅ 配置文件的加载和管理

---

**下一步**: 继续学习Day 2的"状态管理"代码示例
