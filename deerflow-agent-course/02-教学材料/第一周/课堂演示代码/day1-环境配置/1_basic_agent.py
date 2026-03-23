"""
Day 1 - 最简单的Agent实现
演示LangGraph StateGraph的基础用法
"""

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    """简单的Agent状态"""
    messages: list[str]


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """根据消息内容决定下一步"""
    last_message = state["messages"][-1].lower()
    if "calculate" in last_message or "compute" in last_message:
        return "tools"
    return "__end__"


def calculator(expression: str) -> str:
    """计算器工具"""
    try:
        result = eval(expression)
        return f"结果: {result}"
    except Exception as e:
        return f"错误: {str(e)}"


def node_input(state: AgentState) -> AgentState:
    """输入处理节点"""
    print(f"收到输入: {state['messages'][-1]}")
    return state


def node_tools(state: AgentState) -> AgentState:
    """工具执行节点"""
    expr = state["messages"][-1].replace("calculate ", "").replace("compute ", "")
    result = calculator(expr)
    return {"messages": state["messages"] + [result]}


def node_output(state: AgentState) -> AgentState:
    """输出节点"""
    print(f"最终结果: {state['messages'][-1]}")
    return state


def build_graph():
    """构建StateGraph"""
    graph = StateGraph(AgentState)
    
    graph.add_node("input", node_input)
    graph.add_node("tools", node_tools)
    graph.add_node("output", node_output)
    
    graph.add_edge(START, "input")
    graph.add_conditional_edges(
        "input",
        should_continue,
        {"tools": "tools", "__end__": END}
    )
    graph.add_edge("tools", "output")
    graph.add_edge("output", END)
    
    return graph.compile()


if __name__ == "__main__":
    print("=" * 50)
    print("Day 1: 最简单的Agent")
    print("=" * 50)
    
    app = build_graph()
    
    # 测试用例
    initial_state = {"messages": ["calculate 2 + 3 * 4"]}
    result = app.invoke(initial_state)
    
    print("\n执行结果:")
    for msg in result["messages"]:
        print(f"  -> {msg}")
