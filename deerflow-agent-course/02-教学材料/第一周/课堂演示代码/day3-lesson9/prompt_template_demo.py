#!/usr/bin/env python3
# 教育代码说明：本文件为AI Agent架构师训练营课堂演示代码，包含详细注释用于教学目的
# Educational code note: This file contains detailed comments for teaching purposes in AI Agent Architect Training Camp
"""
Day 3 Lesson 9: 提示模板架构 - 课堂演示代码

本文件演示提示模板系统的完整设计与实现，包含四个部分：
1. 模板架构模拟 - 五大设计原则验证和继承体系展示
2. 模板渲染状态机实现 - 变量替换、条件逻辑、多语言支持
3. 模块化模板系统设计 - 基类设计和具体模板实现
4. 模板架构分析 - 设计模式、性能优化、最佳实践分析

学习目标：
- 掌握提示模板的五大设计原则（角色、任务、约束、格式、示例）
- 理解模板继承体系的设计决策和实现方式
- 实现安全高效的模板渲染和变量替换
- 设计支持多语言、动态内容的专业模板系统

版本: 1.0
作者: DeerFlow架构师训练营
日期: 2024年3月27日
"""

import json
import re
import time
from typing import TypedDict, Optional, List, Dict, Any, Union, Callable, Protocol
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import defaultdict
import argparse

# ============================================================================
# 第一部分：模板架构模拟
# ============================================================================

print("=" * 60)
print("第一部分：模板架构模拟")
print("=" * 60)
print()

# ============================================================================
# 1.1 五大设计原则定义与验证
# ============================================================================

print("🔍 1.1 五大设计原则定义与验证")
print()


class DesignPrinciple(Enum):
    """提示模板五大设计原则枚举"""

    ROLE_DEFINITION = "role_definition"  # 角色定义
    TASK_DESCRIPTION = "task_description"  # 任务描述
    CONSTRAINTS = "constraints"  # 约束条件
    OUTPUT_FORMAT = "output_format"  # 输出格式
    EXAMPLES = "examples"  # 示例演示


class PrincipleValidator:
    """设计原则验证器"""

    @staticmethod
    def validate_role_definition(template: str) -> bool:
        """验证角色定义原则：模板是否明确定义AI角色"""
        # 检查是否包含角色关键词
        role_keywords = ["你是一个", "你扮演", "作为", "role:", "角色:"]
        return any(keyword in template.lower() for keyword in role_keywords)

    @staticmethod
    def validate_task_description(template: str) -> bool:
        """验证任务描述原则：模板是否清晰描述任务"""
        # 检查是否包含任务描述关键词
        task_keywords = ["任务是", "需要", "要求", "task:", "目标:"]
        return any(keyword in template.lower() for keyword in task_keywords)

    @staticmethod
    def validate_constraints(template: str) -> bool:
        """验证约束条件原则：模板是否明确约束条件"""
        # 检查是否包含约束关键词
        constraint_keywords = ["不要", "避免", "必须", "禁止", "约束:", "限制:"]
        return any(keyword in template.lower() for keyword in constraint_keywords)

    @staticmethod
    def validate_output_format(template: str) -> bool:
        """验证输出格式原则：模板是否定义输出格式"""
        # 检查是否包含格式关键词
        format_keywords = [
            "格式:",
            "输出为",
            "结构:",
            "按以下格式",
            "json",
            "xml",
            "markdown",
        ]
        return any(keyword in template.lower() for keyword in format_keywords)

    @staticmethod
    def validate_examples(template: str) -> bool:
        """验证示例演示原则：模板是否提供示例"""
        # 检查是否包含示例关键词
        example_keywords = ["例如:", "例子:", "示例:", "example:", "e.g.", "比如:"]
        return any(keyword in template.lower() for keyword in example_keywords)

    @classmethod
    def validate_all(cls, template: str) -> Dict[DesignPrinciple, bool]:
        """验证所有五大原则"""
        return {
            DesignPrinciple.ROLE_DEFINITION: cls.validate_role_definition(template),
            DesignPrinciple.TASK_DESCRIPTION: cls.validate_task_description(template),
            DesignPrinciple.CONSTRAINTS: cls.validate_constraints(template),
            DesignPrinciple.OUTPUT_FORMAT: cls.validate_output_format(template),
            DesignPrinciple.EXAMPLES: cls.validate_examples(template),
        }


# 测试模板
test_templates = {
    "good_template": """
你是一个专业的代码助手，精通Python、Java和Go语言。
任务是帮助用户分析和优化代码，提供最佳实践建议。
约束：不要提供不安全的代码示例，避免推荐过时的技术。
输出格式：按以下格式提供建议：
1. 问题分析
2. 优化建议
3. 代码示例
4. 注意事项
示例：对于Python列表推导式优化...
""",
    "bad_template": "帮我写代码",
    "medium_template": """
你是一个翻译助手。
任务是翻译文本。
输出格式：json格式。
""",
}

print("📋 测试模板五大原则验证结果:")
print()

for name, template in test_templates.items():
    print(f"  {name}:")
    validation = PrincipleValidator.validate_all(template)
    for principle, passed in validation.items():
        status = "✅" if passed else "❌"
        print(f"    {status} {principle.value}: {principle.name}")
    print()

# ============================================================================
# 1.2 模板继承体系模拟
# ============================================================================

print("🏗️ 1.2 模板继承体系模拟")
print()


class TemplateType(Enum):
    """模板类型枚举"""

    SYSTEM_PROMPT = "system_prompt"  # 系统提示
    USER_PROMPT = "user_prompt"  # 用户提示
    TOOL_PROMPT = "tool_prompt"  # 工具提示
    CUSTOM_PROMPT = "custom_prompt"  # 自定义提示


@dataclass
class TemplateNode:
    """模板继承树节点"""

    name: str
    template_type: TemplateType
    parent: Optional["TemplateNode"] = None
    children: List["TemplateNode"] = field(default_factory=list)

    def add_child(self, child: "TemplateNode"):
        """添加子节点"""
        child.parent = self
        self.children.append(child)

    def get_full_hierarchy(self) -> str:
        """获取完整继承层级"""
        if not self.parent:
            return self.name
        return f"{self.parent.get_full_hierarchy()} → {self.name}"

    def get_all_principles(self) -> List[DesignPrinciple]:
        """获取节点支持的所有设计原则（模拟）"""
        # 根据模板类型返回不同的原则支持
        base_principles = [
            DesignPrinciple.ROLE_DEFINITION,
            DesignPrinciple.TASK_DESCRIPTION,
        ]

        if self.template_type == TemplateType.SYSTEM_PROMPT:
            return base_principles + [
                DesignPrinciple.CONSTRAINTS,
                DesignPrinciple.OUTPUT_FORMAT,
            ]
        elif self.template_type == TemplateType.USER_PROMPT:
            return base_principles + [
                DesignPrinciple.EXAMPLES,
            ]
        elif self.template_type == TemplateType.TOOL_PROMPT:
            return base_principles + [
                DesignPrinciple.CONSTRAINTS,
                DesignPrinciple.EXAMPLES,
                DesignPrinciple.OUTPUT_FORMAT,
            ]
        else:
            return list(DesignPrinciple)


# 构建模板继承树
print("🌳 构建模板继承树:")
print()

root = TemplateNode("PromptTemplate", TemplateType.SYSTEM_PROMPT)

system_prompt = TemplateNode("SystemPrompt", TemplateType.SYSTEM_PROMPT)
user_prompt = TemplateNode("UserPrompt", TemplateType.USER_PROMPT)
tool_prompt = TemplateNode("ToolPrompt", TemplateType.TOOL_PROMPT)

root.add_child(system_prompt)
root.add_child(user_prompt)
root.add_child(tool_prompt)

# 添加具体模板
code_assistant = TemplateNode("CodeAssistantPrompt", TemplateType.CUSTOM_PROMPT)
translation_assistant = TemplateNode(
    "TranslationAssistantPrompt", TemplateType.CUSTOM_PROMPT
)
customer_service = TemplateNode("CustomerServicePrompt", TemplateType.CUSTOM_PROMPT)

system_prompt.add_child(code_assistant)
user_prompt.add_child(translation_assistant)
tool_prompt.add_child(customer_service)


# 显示继承关系
def display_tree(node: TemplateNode, indent: int = 0):
    """显示树结构"""
    prefix = "  " * indent
    hierarchy = node.get_full_hierarchy()
    principles = node.get_all_principles()
    principle_names = [p.name for p in principles]

    print(f"{prefix}📄 {node.name} ({node.template_type.value})")
    print(f"{prefix}  继承路径: {hierarchy}")
    print(f"{prefix}  支持原则: {', '.join(principle_names)}")
    print()

    for child in node.children:
        display_tree(child, indent + 1)


display_tree(root)

# ============================================================================
# 1.3 模板质量评估系统
# ============================================================================

print("📊 1.3 模板质量评估系统")
print()


@dataclass
class TemplateQualityScore:
    """模板质量评分"""

    template_name: str
    principle_scores: Dict[DesignPrinciple, float]
    completeness_score: float
    clarity_score: float
    maintainability_score: float

    @property
    def overall_score(self) -> float:
        """计算总体得分"""
        # 加权平均
        weights = {
            "principle": 0.4,
            "completeness": 0.3,
            "clarity": 0.2,
            "maintainability": 0.1,
        }

        principle_avg = sum(self.principle_scores.values()) / len(self.principle_scores)

        return (
            principle_avg * weights["principle"]
            + self.completeness_score * weights["completeness"]
            + self.clarity_score * weights["clarity"]
            + self.maintainability_score * weights["maintainability"]
        )

    def get_grade(self) -> str:
        """获取等级"""
        score = self.overall_score
        if score >= 0.9:
            return "A+ (优秀)"
        elif score >= 0.8:
            return "A (良好)"
        elif score >= 0.7:
            return "B (合格)"
        elif score >= 0.6:
            return "C (需改进)"
        else:
            return "D (不合格)"


class TemplateQualityEvaluator:
    """模板质量评估器"""

    @staticmethod
    def evaluate_template(template: str, template_name: str) -> TemplateQualityScore:
        """评估模板质量"""
        # 验证五大原则
        validation = PrincipleValidator.validate_all(template)
        principle_scores = {
            principle: 1.0 if passed else 0.0
            for principle, passed in validation.items()
        }

        # 计算完整性得分（检查关键部分）
        sections = ["角色", "任务", "约束", "格式", "示例"]
        section_count = sum(1 for section in sections if section in template)
        completeness_score = section_count / len(sections)

        # 计算清晰度得分（基于长度和结构）
        lines = template.strip().split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        clarity_score = min(1.0, len(non_empty_lines) / 20)  # 最多20行

        # 计算可维护性得分（基于模板复杂性）
        complexity_indicators = ["如果", "否则", "循环", "条件", "变量"]
        complexity_count = sum(
            1 for indicator in complexity_indicators if indicator in template
        )
        maintainability_score = max(0.0, 1.0 - complexity_count * 0.1)

        return TemplateQualityScore(
            template_name=template_name,
            principle_scores=principle_scores,
            completeness_score=completeness_score,
            clarity_score=clarity_score,
            maintainability_score=maintainability_score,
        )


# 评估测试模板
print("📈 模板质量评估结果:")
print()

for name, template in test_templates.items():
    score = TemplateQualityEvaluator.evaluate_template(template, name)
    print(f"  📝 {name}:")
    print(
        f"    五大原则得分: {sum(score.principle_scores.values()) / len(score.principle_scores):.1%}"
    )
    print(f"    完整性得分: {score.completeness_score:.1%}")
    print(f"    清晰度得分: {score.clarity_score:.1%}")
    print(f"    可维护性得分: {score.maintainability_score:.1%}")
    print(f"    总体得分: {score.overall_score:.1%} ({score.get_grade()})")
    print()

print(
    "🎯 第一部分总结: 通过五大原则验证、继承体系模拟和质量评估，学员已掌握模板架构的核心概念。"
)
print()

# ============================================================================
# 第二部分：模板渲染状态机实现
# ============================================================================

print("=" * 60)
print("第二部分：模板渲染状态机实现")
print("=" * 60)
print()

# ============================================================================
# 2.1 模板渲染状态机定义
# ============================================================================

print("🔄 2.1 模板渲染状态机定义")
print()


class TemplateRenderState(Enum):
    """模板渲染状态枚举"""

    IDLE = "idle"  # 空闲状态
    PARSING = "parsing"  # 解析模板
    VARIABLE_SUBSTITUTION = "variable_substitution"  # 变量替换
    CONDITIONAL_PROCESSING = "conditional_processing"  # 条件处理
    MULTILINGUAL_SWITCHING = "multilingual_switching"  # 多语言切换
    VALIDATION = "validation"  # 验证结果
    COMPLETED = "completed"  # 完成
    ERROR = "error"  # 错误


class TemplateRenderEvent(Enum):
    """模板渲染事件枚举"""

    START = "start"  # 开始渲染
    PARSE_COMPLETE = "parse_complete"  # 解析完成
    VARIABLES_READY = "variables_ready"  # 变量就绪
    CONDITION_EVALUATED = "condition_evaluated"  # 条件评估完成
    LANGUAGE_SELECTED = "language_selected"  # 语言选择完成
    VALIDATION_PASSED = "validation_passed"  # 验证通过
    VALIDATION_FAILED = "validation_failed"  # 验证失败
    COMPLETE = "complete"  # 完成
    ERROR = "error"  # 错误


class TemplateRenderStateMachine:
    """模板渲染状态机"""

    def __init__(self):
        self.state = TemplateRenderState.IDLE
        self.context = {}
        self.transition_history = []

    def transition(
        self, event: TemplateRenderEvent, data: Dict[str, Any] = None
    ) -> bool:
        """状态转移"""
        old_state = self.state
        new_state = self._get_next_state(old_state, event)

        if new_state != old_state:
            self.state = new_state
            if data:
                self.context.update(data)

            transition_record = {
                "from": old_state,
                "to": new_state,
                "event": event,
                "timestamp": time.time(),
            }
            self.transition_history.append(transition_record)

            print(
                f"  🔄 状态转移: {old_state.value} → {new_state.value} (事件: {event.value})"
            )
            return True
        else:
            print(f"  ⏸️  状态保持: {old_state.value} (事件: {event.value})")
            return False

    def _get_next_state(
        self, state: TemplateRenderState, event: TemplateRenderEvent
    ) -> TemplateRenderState:
        """获取下一个状态（状态转移表）"""
        transition_table = {
            (
                TemplateRenderState.IDLE,
                TemplateRenderEvent.START,
            ): TemplateRenderState.PARSING,
            (
                TemplateRenderState.PARSING,
                TemplateRenderEvent.PARSE_COMPLETE,
            ): TemplateRenderState.VARIABLE_SUBSTITUTION,
            (
                TemplateRenderState.VARIABLE_SUBSTITUTION,
                TemplateRenderEvent.VARIABLES_READY,
            ): TemplateRenderState.CONDITIONAL_PROCESSING,
            (
                TemplateRenderState.CONDITIONAL_PROCESSING,
                TemplateRenderEvent.CONDITION_EVALUATED,
            ): TemplateRenderState.MULTILINGUAL_SWITCHING,
            (
                TemplateRenderState.MULTILINGUAL_SWITCHING,
                TemplateRenderEvent.LANGUAGE_SELECTED,
            ): TemplateRenderState.VALIDATION,
            (
                TemplateRenderState.VALIDATION,
                TemplateRenderEvent.VALIDATION_PASSED,
            ): TemplateRenderState.COMPLETED,
            (
                TemplateRenderState.VALIDATION,
                TemplateRenderEvent.VALIDATION_FAILED,
            ): TemplateRenderState.ERROR,
            (
                TemplateRenderState.COMPLETED,
                TemplateRenderEvent.COMPLETE,
            ): TemplateRenderState.IDLE,
            (
                TemplateRenderState.ERROR,
                TemplateRenderEvent.ERROR,
            ): TemplateRenderState.IDLE,
        }

        return transition_table.get((state, event), state)

    def render_template(
        self, template: str, variables: Dict[str, Any], language: str = "zh-CN"
    ) -> str:
        """渲染模板（完整流程）"""
        print("🚀 开始模板渲染流程...")

        # 1. 开始渲染
        self.transition(TemplateRenderEvent.START, {"template": template})

        # 2. 解析模板
        parsed_template = self._parse_template(template)
        self.transition(
            TemplateRenderEvent.PARSE_COMPLETE, {"parsed_template": parsed_template}
        )

        # 3. 变量替换
        substituted = self._substitute_variables(parsed_template, variables)
        self.transition(
            TemplateRenderEvent.VARIABLES_READY, {"substituted": substituted}
        )

        # 4. 条件处理
        conditional_processed = self._process_conditionals(substituted, variables)
        self.transition(
            TemplateRenderEvent.CONDITION_EVALUATED,
            {"conditional_processed": conditional_processed},
        )

        # 5. 多语言切换
        multilingual = self._switch_language(conditional_processed, language)
        self.transition(
            TemplateRenderEvent.LANGUAGE_SELECTED, {"multilingual": multilingual}
        )

        # 6. 验证结果
        is_valid = self._validate_result(multilingual)
        if is_valid:
            self.transition(TemplateRenderEvent.VALIDATION_PASSED)
            result = multilingual
            self.transition(TemplateRenderEvent.COMPLETE, {"result": result})
        else:
            self.transition(
                TemplateRenderEvent.VALIDATION_FAILED, {"error": "渲染结果验证失败"}
            )
            result = f"ERROR: {template}"

        print(f"✅ 渲染完成，最终状态: {self.state.value}")
        print(f"📊 状态转移历史: {len(self.transition_history)} 次转移")
        return result

    def _parse_template(self, template: str) -> str:
        """解析模板（模拟）"""
        print("  🔍 解析模板...")
        # 实际实现会解析模板语法
        return template

    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """变量替换"""
        print("  🔄 变量替换...")
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
                print(f"    替换: {placeholder} → {value}")
        return result

    def _process_conditionals(self, template: str, variables: Dict[str, Any]) -> str:
        """处理条件逻辑"""
        print("  🔀 处理条件逻辑...")
        # 简单条件处理：{{#if condition}}...{{/if}}
        result = template
        # 模拟条件处理
        if "{{#if" in template and "{{/if}}" in template:
            print("    检测到条件块，进行条件评估...")
            # 简化实现
            result = template.replace("{{#if debug}}", "").replace("{{/if}}", "")
        return result

    def _switch_language(self, template: str, language: str) -> str:
        """多语言切换"""
        print(f"  🌐 多语言切换 (目标语言: {language})...")
        # 模拟多语言支持
        if language != "zh-CN":
            # 在实际实现中，这里会加载不同语言的模板
            return f"[{language}] {template}"
        return template

    def _validate_result(self, result: str) -> bool:
        """验证渲染结果"""
        print("  ✅ 验证渲染结果...")
        # 简单验证：结果不能为空，不能包含未替换的变量
        if not result or not result.strip():
            return False

        # 检查是否还有未替换的变量占位符
        import re

        unmatched_variables = re.findall(r"\{[^}]*\}", result)
        if unmatched_variables:
            print(f"    警告: 发现未替换的变量: {unmatched_variables}")
            # 在实际系统中，可能返回部分渲染结果或抛出错误
            return len(unmatched_variables) == 0

        return True


# 演示状态机
print("🎬 演示模板渲染状态机:")
print()

state_machine = TemplateRenderStateMachine()

# 测试模板
test_template = """
你是一个{role}，任务是{task}。
{{#if debug}}
调试模式：开启详细日志
{{/if}}
请用{language}回答。
"""

test_variables = {
    "role": "代码助手",
    "task": "帮助用户编写Python代码",
    "language": "中文",
    "debug": True,
}

result = state_machine.render_template(test_template, test_variables, language="zh-CN")
print()
print(f"📝 原始模板: {test_template.strip()}")
print(f"🔄 渲染结果: {result}")
print()

# ============================================================================
# 2.2 高级模板功能：条件逻辑和循环
# ============================================================================

print("⚡ 2.2 高级模板功能：条件逻辑和循环")
print()


class AdvancedTemplateRenderer:
    """高级模板渲染器（支持条件、循环、嵌套）"""

    def __init__(self):
        self.patterns = {
            "variable": r"\{([^{}]+)\}",
            "conditional": r"\{\{#if ([^{}]+)\}\}(.*?)\{\{/if\}\}",
            "loop": r"\{\{#each ([^{}]+)\}\}(.*?)\{\{/each\}\}",
            "comment": r"\{\{!--(.*?)--\}\}",
        }

    def render(self, template: str, context: Dict[str, Any]) -> str:
        """渲染高级模板"""
        print("🎨 渲染高级模板...")

        # 1. 移除注释
        result = self._remove_comments(template)

        # 2. 处理循环
        result = self._process_loops(result, context)

        # 3. 处理条件
        result = self._process_conditionals(result, context)

        # 4. 替换变量
        result = self._replace_variables(result, context)

        return result

    def _remove_comments(self, template: str) -> str:
        """移除注释"""
        import re

        return re.sub(self.patterns["comment"], "", template, flags=re.DOTALL)

    def _process_conditionals(self, template: str, context: Dict[str, Any]) -> str:
        """处理条件逻辑"""
        import re

        def replace_conditional(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # 评估条件
            try:
                # 简单条件评估
                condition_value = context.get(condition, False)
                if condition_value:
                    return content
                else:
                    return ""
            except Exception:
                return ""

        result = template
        while True:
            new_result = re.sub(
                self.patterns["conditional"],
                replace_conditional,
                result,
                flags=re.DOTALL,
            )
            if new_result == result:
                break
            result = new_result

        return result

    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """处理循环"""
        import re

        def replace_loop(match):
            list_name = match.group(1).strip()
            item_template = match.group(2)

            # 获取列表
            items = context.get(list_name, [])
            if not isinstance(items, list):
                return f"[错误: {list_name} 不是列表]"

            # 渲染每个项目
            results = []
            for index, item in enumerate(items):
                # 创建子上下文
                sub_context = context.copy()
                sub_context["item"] = item
                sub_context["index"] = index
                sub_context["first"] = index == 0
                sub_context["last"] = index == len(items) - 1

                # 渲染项目模板
                item_result = self._replace_variables(item_template, sub_context)
                results.append(item_result)

            return "\n".join(results)

        result = template
        while True:
            new_result = re.sub(
                self.patterns["loop"], replace_loop, result, flags=re.DOTALL
            )
            if new_result == result:
                break
            result = new_result

        return result

    def _replace_variables(self, template: str, context: Dict[str, Any]) -> str:
        """替换变量"""
        import re

        def replace_variable(match):
            variable_name = match.group(1).strip()
            value = context.get(variable_name, f"{{{variable_name}}}")
            return str(value)

        result = template
        while True:
            new_result = re.sub(self.patterns["variable"], replace_variable, result)
            if new_result == result:
                break
            result = new_result

        return result


# 演示高级模板
print("🧪 演示高级模板功能:")
print()

advanced_renderer = AdvancedTemplateRenderer()

advanced_template = """
{{!-- 用户信息列表模板 --}}
用户列表：
{{#each users}}
{{index + 1}}. 姓名: {item.name}, 年龄: {item.age}, 角色: {item.role}
{{#if item.premium}}
  (高级用户)
{{/if}}
{{/each}}

{{#if show_summary}}
总计: {total_users} 个用户
{{/if}}
"""

advanced_context = {
    "users": [
        {"name": "张三", "age": 25, "role": "开发者", "premium": True},
        {"name": "李四", "age": 30, "role": "设计师", "premium": False},
        {"name": "王五", "age": 28, "role": "产品经理", "premium": True},
    ],
    "show_summary": True,
    "total_users": 3,
}

advanced_result = advanced_renderer.render(advanced_template, advanced_context)
print("📋 高级模板:")
print(advanced_template)
print()
print("🎨 渲染结果:")
print(advanced_result)
print()

# ============================================================================
# 2.3 多语言模板系统
# ============================================================================

print("🌍 2.3 多语言模板系统")
print()


class MultilingualTemplateSystem:
    """多语言模板系统"""

    def __init__(self):
        # 嵌套字典结构: 第一层键是语言，第二层键是模板名称，值是模板内容
        self.templates = defaultdict(dict)
        self.current_language = "zh-CN"
        self.fallback_language = "en-US"

    def register_template(self, name: str, template: str, language: str = "zh-CN"):
        """注册模板"""
        self.templates[language][name] = template
        print(f"📝 注册模板: {name} ({language})")

    def get_template(self, name: str, language: str = None) -> str:
        """获取模板（支持回退）"""
        target_language = language or self.current_language

        # 1. 尝试目标语言
        if (
            target_language in self.templates
            and name in self.templates[target_language]
        ):
            return self.templates[target_language][name]

        # 2. 尝试回退语言
        if (
            self.fallback_language in self.templates
            and name in self.templates[self.fallback_language]
        ):
            print(f"  🔄 语言回退: {target_language} → {self.fallback_language}")
            return self.templates[self.fallback_language][name]

        # 3. 尝试任何语言
        for lang, templates in self.templates.items():
            if name in templates:
                print(f"  🔄 语言回退: {target_language} → {lang}")
                return templates[name]

        raise ValueError(f"模板 '{name}' 未找到")

    def render_multilingual(
        self, name: str, variables: Dict[str, Any], language: str = None
    ) -> str:
        """渲染多语言模板"""
        template = self.get_template(name, language)

        # 简单变量替换
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))

        return result


# 演示多语言系统
print("🗣️ 演示多语言模板系统:")
print()

ml_system = MultilingualTemplateSystem()

# 注册不同语言的模板
ml_system.register_template("welcome", "欢迎，{name}！今天是{date}。", "zh-CN")

ml_system.register_template("welcome", "Welcome, {name}! Today is {date}.", "en-US")

ml_system.register_template(
    "welcome", "Bienvenue, {name}! Aujourd'hui, c'est le {date}.", "fr-FR"
)

# 渲染不同语言
test_vars = {"name": "张三", "date": "2024年3月27日"}

for lang in ["zh-CN", "en-US", "fr-FR", "de-DE"]:  # de-DE 未注册
    try:
        result = ml_system.render_multilingual("welcome", test_vars, lang)
        print(f"  {lang}: {result}")
    except ValueError as e:
        print(f"  {lang}: ❌ {e}")

print()
print(
    "🎯 第二部分总结: 通过状态机实现、高级模板功能和多语言支持，学员已掌握模板渲染的核心技术。"
)
print()

# ============================================================================
# 第三部分：模块化模板系统设计
# ============================================================================

print("=" * 60)
print("第三部分：模块化模板系统设计")
print("=" * 60)
print()

print("🏗️ 3.1 PromptTemplate基类设计")
print()

from abc import ABC, abstractmethod
from typing import Dict, Any


class PromptTemplate(ABC):
    """提示模板基类（抽象类）"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.variables = {}
        self.validation_rules = {}

    @abstractmethod
    def get_template(self) -> str:
        """获取模板内容（抽象方法）"""
        pass

    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板"""
        template = self.get_template()
        # 简单变量替换
        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """验证上下文是否满足模板要求"""
        # 检查必需变量
        required_vars = self.validation_rules.get("required", [])
        for var in required_vars:
            if var not in context:
                return False
        return True

    def get_principles_report(self) -> Dict[str, bool]:
        """获取五大原则符合性报告"""
        template = self.get_template()
        return PrincipleValidator.validate_all(template)


class SystemPrompt(PromptTemplate):
    """系统提示模板"""

    def __init__(self, name: str, system_role: str, constraints: List[str] = None):
        super().__init__(name, f"系统提示: {system_role}")
        self.system_role = system_role
        self.constraints = constraints or []

    def get_template(self) -> str:
        """生成系统提示模板"""
        constraints_text = "\n".join([f"- {c}" for c in self.constraints])
        return f"""你是一个{self.system_role}。

约束条件:
{constraints_text}

请按照要求完成任务。"""


class UserPrompt(PromptTemplate):
    """用户提示模板"""

    def __init__(self, name: str, task_description: str, examples: List[str] = None):
        super().__init__(name, f"用户提示: {task_description}")
        self.task_description = task_description
        self.examples = examples or []

    def get_template(self) -> str:
        """生成用户提示模板"""
        examples_text = "\n".join([f"示例: {e}" for e in self.examples])
        return f"""任务: {self.task_description}

{examples_text}

请完成上述任务。"""


# 演示模块化系统
print("🔧 演示模块化模板系统:")
print()

# 创建系统提示模板
system_template = SystemPrompt(
    name="代码审查助手",
    system_role="专业的代码审查专家",
    constraints=[
        "只审查Python代码",
        "提供具体的改进建议",
        "不要重复代码",
        "遵循PEP8规范",
    ],
)

# 创建用户提示模板
user_template = UserPrompt(
    name="代码优化请求",
    task_description="优化以下Python代码，提高性能和可读性",
    examples=[
        "原始代码: for i in range(len(items)): print(items[i])",
        "优化后: for item in items: print(item)",
    ],
)

# 渲染模板
context = {"additional_note": "请特别关注性能优化"}

print(f"📋 系统模板: {system_template.name}")
print(system_template.render(context))
print()

print(f"📋 用户模板: {user_template.name}")
print(user_template.render(context))
print()

# 验证原则符合性
print("✅ 五大原则符合性检查:")
system_report = system_template.get_principles_report()
user_report = user_template.get_principles_report()

print(f"  系统模板: {sum(system_report.values())}/{len(system_report)} 项符合")
print(f"  用户模板: {sum(user_report.values())}/{len(user_report)} 项符合")
print()

# ============================================================================
# 第四部分：模板架构分析
# ============================================================================

print("=" * 60)
print("第四部分：模板架构分析")
print("=" * 60)
print()

print("📊 4.1 设计模式分析")
print()

print("🔍 识别到的设计模式:")
print("  1. 模板方法模式: PromptTemplate基类定义渲染算法骨架")
print("  2. 策略模式: 不同的模板类型实现不同的模板生成策略")
print("  3. 状态模式: 模板渲染状态机管理渲染流程状态")
print("  4. 组合模式: 模板继承树支持复杂的模板组合")
print("  5. 工厂模式: MultilingualTemplateSystem按需创建模板实例")
print()

print("⚖️ 4.2 架构决策权衡")
print()

print("🔑 关键架构决策:")
print("  1. 继承 vs 组合: 使用继承建立模板类型体系，组合实现具体功能")
print("  2. 集中式 vs 分布式: 集中式模板注册表便于管理，分布式更灵活")
print("  3. 静态 vs 动态: 静态类型检查提高安全性，动态模板支持更灵活")
print("  4. 性能 vs 可维护性: 缓存渲染结果提升性能，模块化设计提升可维护性")
print()

print("🚀 4.3 性能优化建议")
print()

print("💡 优化策略:")
print("  1. 模板缓存: 缓存解析后的模板AST，避免重复解析")
print("  2. 变量索引: 建立变量引用索引，加速变量替换")
print("  3. 懒加载: 多语言模板按需加载，减少内存占用")
print("  4. 预编译: 预编译常用模板，提升渲染性能")
print()

print("⚠️ 4.4 常见反模式")
print()

print("❌ 需要避免的反模式:")
print("  1. 魔法字符串: 避免在代码中硬编码模板内容")
print("  2. 过度嵌套: 避免过深的模板继承层次，增加复杂性")
print("  3. 全局状态: 避免全局模板状态，导致难以测试")
print("  4. 紧耦合: 避免模板与具体业务逻辑紧耦合")
print()

print("🎯 4.5 最佳实践总结")
print()

print("✅ 推荐的最佳实践:")
print("  1. 遵循五大设计原则: 确保模板质量")
print("  2. 类型安全: 使用TypedDict定义模板变量类型")
print("  3. 单元测试: 为每个模板编写渲染测试")
print("  4. 版本管理: 对模板进行版本控制")
print("  5. 文档化: 为模板提供使用文档和示例")
print()

print("=" * 60)
print("课程总结")
print("=" * 60)
print()

print("✨ 恭喜完成Day 3第9节课的学习！")
print()
print("📚 学习成果:")
print("  • 掌握了提示模板的五大设计原则")
print("  • 理解了模板继承体系的设计方法")
print("  • 实现了模板渲染状态机和高级功能")
print("  • 设计了模块化的模板系统架构")
print("  • 学会了模板系统的性能优化和最佳实践")
print()
print("🚀 下一步:")
print("  • 完成课后练习，巩固所学知识")
print("  • 在实际项目中应用模板设计原则")
print("  • 预习下一节课: 内存上下文注入机制")
print()

# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="提示模板架构演示程序")
    parser.add_argument(
        "--part", type=int, choices=[1, 2, 3, 4], help="运行特定部分演示 (1-4)"
    )
    args = parser.parse_args()

    # 如果指定了部分，只运行该部分
    # 注意：实际实现需要调整，这里简化处理
    if args.part:
        print(f"🎯 运行第{args.part}部分演示...")
        # 实际实现中会根据参数过滤内容
    else:
        print("🚀 运行完整演示程序")
