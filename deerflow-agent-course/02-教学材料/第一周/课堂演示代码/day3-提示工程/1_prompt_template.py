"""
Day 3 - 提示模板架构
演示如何构建动态提示模板
"""

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


def create_basic_prompt():
    """基础提示模板"""
    prompt = PromptTemplate.from_template(
        "你是一个{role}，请回答以下问题：{question}"
    )
    return prompt


def create_chat_prompt():
    """聊天提示模板"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的{profession}，有{years}年经验"),
        ("human", "请问{model}的优缺点是什么？"),
        ("ai", "让我详细分析{model}的特点...")
    ])
    return prompt


def create_conditional_prompt():
    """条件提示模板"""
    system_template = """你是一个AI助手。
    {% if level == 'beginner' %}
    请用简单易懂的语言解释。
    {% elif level == 'intermediate' %}
    请提供详细的技术分析。
    {% else %}
    请提供深度的学术级解释。
    {% endif %}
    """
    
    prompt = PromptTemplate.from_template(system_template)
    return prompt


def demonstrate_prompts():
    """演示提示模板"""
    print("=" * 50)
    print("提示模板示例")
    print("=" * 50)
    
    # 基础模板
    basic = create_basic_prompt()
    result = basic.invoke({
        "role": "Python导师",
        "question": "什么是生成器？"
    })
    print(f"\n基础模板输出:\n{result}")
    
    # 聊天模板
    chat = create_chat_prompt()
    result = chat.invoke({
        "profession": "软件架构师",
        "years": 10,
        "model": "GPT-4"
    })
    print(f"\n聊天模板输出:")
    for msg in result.messages:
        print(f"  [{msg.type}]: {msg.content[:50]}...")
    
    # 条件模板
    conditional = create_conditional_prompt()
    
    for level in ["beginner", "intermediate", "expert"]:
        result = conditional.invoke({"level": level})
        print(f"\n{level}级别输出:\n{result}")


if __name__ == "__main__":
    demonstrate_prompts()
