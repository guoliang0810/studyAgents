"""
Day 2 - ThreadState状态管理
演示如何定义和使用TypedDict状态
"""

from typing import TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, START, END, MessageGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class UserProfile(TypedDict):
    """用户资料"""
    user_id: str
    name: str
    preferences: dict


class ThreadState(TypedDict):
    """DeerFlow风格的状态定义"""
    # 消息历史
    messages: Annotated[Sequence[str], add_messages]
    
    # 用户上下文
    user: UserProfile
    
    # 当前执行的工具
    current_tool: Optional[str]
    
    # 下一步动作
    next_action: str
    
    # 元数据
    metadata: dict


class AgentConfig(BaseModel):
    """Agent配置"""
    max_iterations: int = Field(default=10)
    temperature: float = Field(default=0.7)
    timeout: int = Field(default=300)
    
    model_config = {"extra": "forbid"}


def create_initial_state() -> ThreadState:
    """创建初始状态"""
    return {
        "messages": [],
        "user": {
            "user_id": "user_001",
            "name": "小明",
            "preferences": {"language": "zh-CN"}
        },
        "current_tool": None,
        "next_action": "start",
        "metadata": {"session_id": "sess_123"}
    }


def update_user_preference(state: ThreadState, key: str, value: any) -> ThreadState:
    """更新用户偏好"""
    new_user = state["user"].copy()
    new_user["preferences"][key] = value
    return {"user": new_user}


def add_message(state: ThreadState, message: str) -> ThreadState:
    """添加消息"""
    return {"messages": [message]}


def demonstrate_state_updates():
    """演示状态更新"""
    print("=" * 50)
    print("ThreadState状态管理示例")
    print("=" * 50)
    
    # 创建初始状态
    state = create_initial_state()
    print(f"\n初始状态:")
    print(f"  用户: {state['user']['name']}")
    print(f"  消息数: {len(state['messages'])}")
    
    # 添加消息
    state = add_message(state, "你好，Agent!")
    state = add_message(state, "我想查询天气")
    
    print(f"\n添加消息后:")
    for msg in state["messages"]:
        print(f"  - {msg}")
    
    # 更新用户偏好
    state = update_user_preference(state, "theme", "dark")
    
    print(f"\n更新偏好后:")
    print(f"  主题: {state['user']['preferences'].get('theme')}")
    
    # 演示配置
    config = AgentConfig(max_iterations=5)
    print(f"\nAgent配置:")
    print(f"  最大迭代: {config.max_iterations}")
    print(f"  温度: {config.temperature}")


if __name__ == "__main__":
    demonstrate_state_updates()
