"""
Day 3 - 内存上下文注入
演示如何在对话中注入历史上下文
"""

from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


class ConversationContext(TypedDict):
    """对话上下文"""
    history: List[BaseMessage]
    user_profile: dict
    current_topic: str


def create_context_injection():
    """创建上下文注入提示"""
    context_template = """## 对话历史
{chat_history}

## 用户信息
- 用户名: {user_name}
- 偏好: {preferences}

## 当前主题
{current_topic}

## 当前问题
{question}
"""
    return context_template


def format_history(history: List[BaseMessage]) -> str:
    """格式化对话历史"""
    formatted = []
    for msg in history[-5:]:  # 最近5条
        role = "用户" if isinstance(msg, HumanMessage) else "AI"
        formatted.append(f"{role}: {msg.content[:100]}")
    return "\n".join(formatted)


def demonstrate_context_injection():
    """演示上下文注入"""
    print("=" * 50)
    print("内存上下文注入示例")
    print("=" * 50)
    
    # 模拟对话历史
    history = [
        HumanMessage(content="我想学习Python"),
        AIMessage(content="很好！Python是一门易学易用的编程语言。您想从哪个方面开始学习？"),
        HumanMessage(content="我想了解装饰器"),
        AIMessage(content="装饰器是Python中一种强大的语法糖，可以用来修改函数或类的行为。")
    ]
    
    # 构建上下文
    context = {
        "chat_history": format_history(history),
        "user_name": "小明",
        "preferences": "喜欢动手实践",
        "current_topic": "Python装饰器",
        "question": "装饰器怎么用在类上？"
    }
    
    template = create_context_injection()
    final_prompt = template.format(**context)
    
    print("\n最终提示:")
    print("-" * 30)
    print(final_prompt)


if __name__ == "__main__":
    demonstrate_context_injection()
