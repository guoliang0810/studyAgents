"""
Day 2 - RunnableConfig运行时配置
演示如何在运行时传递和覆盖配置
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import ConfigurableField


class ConfigurableState(TypedDict):
    """可配置状态"""
    task: str
    result: Optional[str]


def configurable_node(state: ConfigurableState, config: dict) -> ConfigurableState:
    """可配置节点 - 根据config调整行为"""
    print(f"任务: {state['task']}")
    
    # 从config获取参数
    max_retries = config.get("configurable", {}).get("max_retries", 3)
    timeout = config.get("configurable", {}).get("timeout", 60)
    
    print(f"最大重试: {max_retries}, 超时: {timeout}秒")
    
    return {"result": f"处理完成 (retries={max_retries})"}


def build_configurable_graph():
    """构建可配置图"""
    graph = StateGraph(ConfigurableState)
    
    graph.add_node("process", configurable_node)
    graph.add_edge(START, "process")
    graph.add_edge("process", END)
    
    return graph.compile()


def demonstrate_runtime_config():
    """演示运行时配置"""
    print("=" * 50)
    print("RunnableConfig运行时配置")
    print("=" * 50)
    
    app = build_configurable_graph()
    
    initial_state = {"task": "数据处理任务", "result": None}
    
    # 默认配置
    print("\n1. 默认配置:")
    result = app.invoke(initial_state)
    print(f"   结果: {result['result']}")
    
    # 自定义配置
    print("\n2. 自定义配置 (max_retries=5, timeout=120):")
    custom_config = {"configurable": {"max_retries": 5, "timeout": 120}}
    result = app.invoke(initial_state, config=custom_config)
    print(f"   结果: {result['result']}")
    
    # 流式调用演示
    print("\n3. 使用with_config()方法:")
    result = app.invoke(
        initial_state,
        config={"configurable": {"max_retries": 10}}
    )
    print(f"   结果: {result['result']}")


if __name__ == "__main__":
    demonstrate_runtime_config()
