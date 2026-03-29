#!/usr/bin/env python3
"""
Day 14 - 第54节课：提示词记忆注入
==================================

本演示代码实现提示词记忆注入系统，包括：
1. BasePromptTemplate - 基础提示词模板类
2. MemoryPromptTemplate - 支持记忆注入的扩展模板类
3. TemplateVariableSystem - 模板变量系统
4. ContextInjector - 上下文注入器

运行方式:
    python memory_prompt_template_demo.py          # 运行演示
    python memory_prompt_template_demo.py --test   # 运行测试
"""

import time
import json
import re
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import sys
from abc import ABC, abstractmethod


# ============================================================================
# 第一部分：数据模型和枚举定义
# ============================================================================

class TemplateType(Enum):
    """模板类型枚举"""
    SIMPLE = "simple"        # 简单模板，直接文本替换
    STRUCTURED = "structured"  # 结构化模板，支持条件逻辑
    DYNAMIC = "dynamic"      # 动态模板，支持运行时生成


class VariableType(Enum):
    """变量类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    ANY = "any"


class InjectionMode(Enum):
    """注入模式枚举"""
    PREPEND = "prepend"      # 前置注入
    APPEND = "append"        # 后置注入
    INTERLEAVE = "interleave"  # 交错注入
    CONDITIONAL = "conditional"  # 条件注入


@dataclass
class TemplateVariable:
    """模板变量定义"""
    name: str
    var_type: VariableType
    default: Any = None
    description: str = ""
    required: bool = False
    validator: Optional[Callable[[Any], bool]] = None
    
    def validate(self, value: Any) -> bool:
        """验证变量值"""
        if value is None and self.required:
            return False
        
        if value is None:
            return self.default is not None or not self.required
        
        # 类型检查
        try:
            if self.var_type == VariableType.STRING:
                if not isinstance(value, str):
                    return False
            elif self.var_type == VariableType.INTEGER:
                if not isinstance(value, int):
                    return False
            elif self.var_type == VariableType.FLOAT:
                if not isinstance(value, (int, float)):
                    return False
            elif self.var_type == VariableType.BOOLEAN:
                if not isinstance(value, bool):
                    return False
            elif self.var_type == VariableType.LIST:
                if not isinstance(value, list):
                    return False
            elif self.var_type == VariableType.DICT:
                if not isinstance(value, dict):
                    return False
            # ANY类型不进行类型检查
        except:
            return False
        
        # 自定义验证器
        if self.validator and not self.validator(value):
            return False
        
        return True


@dataclass
class Fact:
    """事实数据模型（简化版）"""
    content: str
    source: str
    confidence: float = 1.0
    id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())


# ============================================================================
# 第二部分：基础提示词模板类
# ============================================================================

class BasePromptTemplate(ABC):
    """基础提示词模板类（抽象基类）"""
    
    def __init__(self, template: str, template_type: TemplateType = TemplateType.SIMPLE):
        self.template = template
        self.template_type = template_type
        self.variables: Dict[str, TemplateVariable] = {}
        self._compiled_template: Optional[str] = None
    
    def add_variable(self, variable: TemplateVariable):
        """添加模板变量"""
        self.variables[variable.name] = variable
    
    def get_variable(self, name: str) -> Optional[TemplateVariable]:
        """获取模板变量"""
        return self.variables.get(name)
    
    def validate_variables(self, values: Dict[str, Any]) -> List[str]:
        """验证变量值，返回错误列表"""
        errors = []
        
        # 检查必填变量
        for name, var in self.variables.items():
            if var.required and name not in values:
                errors.append(f"缺少必填变量: {name}")
        
        # 检查变量值
        for name, value in values.items():
            if name in self.variables:
                var = self.variables[name]
                if not var.validate(value):
                    errors.append(f"变量 {name} 验证失败: {value}")
            else:
                # 允许额外的变量（宽松模式）
                pass
        
        return errors
    
    def compile_template(self, values: Dict[str, Any]) -> str:
        """编译模板（基础实现）"""
        # 验证变量
        errors = self.validate_variables(values)
        if errors:
            raise ValueError(f"模板变量验证失败: {errors}")
        
        # 简单变量替换
        result = self.template
        for name, value in values.items():
            placeholder = f"{{{{{name}}}}}"  # 双花括号
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        self._compiled_template = result
        return result
    
    @abstractmethod
    def format(self, **kwargs) -> str:
        """格式化模板（抽象方法）"""
        pass
    
    def get_used_variables(self) -> List[str]:
        """获取模板中使用的变量"""
        # 从模板中提取变量名
        pattern = r"\{\{(\w+)\}\}"
        matches = re.findall(pattern, self.template)
        return list(set(matches))


# ============================================================================
# 第三部分：模板变量系统
# ============================================================================

class TemplateVariableSystem:
    """模板变量系统"""
    
    def __init__(self):
        self._variables: Dict[str, TemplateVariable] = {}
        self._variable_values: Dict[str, Any] = {}
        self._variable_history: Dict[str, List[Any]] = {}
    
    def register_variable(self, variable: TemplateVariable):
        """注册变量"""
        self._variables[variable.name] = variable
    
    def set_value(self, name: str, value: Any, validate: bool = True):
        """设置变量值"""
        if name not in self._variables:
            # 自动创建变量
            self._variables[name] = TemplateVariable(
                name=name, var_type=VariableType.ANY, required=False
            )
        
        if validate:
            var = self._variables[name]
            if not var.validate(value):
                raise ValueError(f"变量 {name} 验证失败: {value}")
        
        self._variable_values[name] = value
        
        # 记录历史
        if name not in self._variable_history:
            self._variable_history[name] = []
        self._variable_history[name].append(value)
    
    def get_value(self, name: str, default: Any = None) -> Any:
        """获取变量值"""
        return self._variable_values.get(name, default)
    
    def get_all_values(self) -> Dict[str, Any]:
        """获取所有变量值"""
        return self._variable_values.copy()
    
    def clear_values(self):
        """清空变量值"""
        self._variable_values.clear()
    
    def interpolate(self, text: str) -> str:
        """插值变量到文本"""
        result = text
        
        # 支持 {{var}} 格式
        for name, value in self._variable_values.items():
            placeholder = f"{{{{{name}}}}}"  # 双花括号
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result
    
    def validate_all(self) -> List[str]:
        """验证所有变量"""
        errors = []
        
        for name, var in self._variables.items():
            value = self._variable_values.get(name)
            if var.required and value is None:
                errors.append(f"必填变量 {name} 未设置")
            elif value is not None and not var.validate(value):
                errors.append(f"变量 {name} 验证失败: {value}")
        
        return errors


# ============================================================================
# 第四部分：上下文注入器
# ============================================================================

class ContextInjector:
    """上下文注入器"""
    
    def __init__(self, injection_mode: InjectionMode = InjectionMode.PREPEND):
        self.injection_mode = injection_mode
        self._context_cache: Dict[str, List[Fact]] = {}
    
    def inject_context(self, prompt: str, context: List[Fact], 
                      max_contexts: int = 5) -> str:
        """注入上下文到提示词"""
        if not context:
            return prompt
        
        # 限制上下文数量
        context = context[:max_contexts]
        
        # 格式化上下文
        context_text = self._format_context(context)
        
        # 根据注入模式组合
        if self.injection_mode == InjectionMode.PREPEND:
            return f"{context_text}\n\n{prompt}"
        elif self.injection_mode == InjectionMode.APPEND:
            return f"{prompt}\n\n{context_text}"
        elif self.injection_mode == InjectionMode.INTERLEAVE:
            # 简化实现：交错注入
            lines = prompt.split('\n')
            if len(lines) > 1:
                mid = len(lines) // 2
                return '\n'.join(lines[:mid] + [context_text] + lines[mid:])
            else:
                return f"{context_text}\n\n{prompt}"
        elif self.injection_mode == InjectionMode.CONDITIONAL:
            # 条件注入：只有当上下文相关时才注入
            return self._conditional_inject(prompt, context_text, context)
        else:
            return prompt
    
    def _format_context(self, context: List[Fact]) -> str:
        """格式化上下文"""
        lines = ["以下是相关上下文信息："]
        for i, fact in enumerate(context, 1):
            tags = f" [标签: {', '.join(fact.tags)}]" if fact.tags else ""
            lines.append(f"{i}. {fact.content} (来源: {fact.source}, 置信度: {fact.confidence:.2f}){tags}")
        return '\n'.join(lines)
    
    def _conditional_inject(self, prompt: str, context_text: str, context: List[Fact]) -> str:
        """条件注入"""
        # 简单实现：基于置信度阈值
        avg_confidence = sum(f.confidence for f in context) / len(context)
        if avg_confidence > 0.5:
            return f"{context_text}\n\n{prompt}"
        else:
            return prompt
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化实现）"""
        # 移除停用词和标点
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        keywords = [w for w in words if w not in stopwords and len(w) > 1]
        return list(set(keywords))[:10]  # 去重并限制数量


# ============================================================================
# 第五部分：记忆提示词模板（扩展类）
# ============================================================================

class MemoryPromptTemplate(BasePromptTemplate):
    """记忆提示词模板（扩展类）"""
    
    def __init__(self, template: str, 
                 template_type: TemplateType = TemplateType.SIMPLE,
                 injection_mode: InjectionMode = InjectionMode.PREPEND):
        super().__init__(template, template_type)
        self.context_injector = ContextInjector(injection_mode)
        self.variable_system = TemplateVariableSystem()
        self.memory_store: List[Fact] = []
        self._cache: Dict[str, str] = {}  # 缓存编译结果
    
    def add_memory(self, fact: Fact):
        """添加记忆"""
        self.memory_store.append(fact)
    
    def search_memory(self, query: str, limit: int = 5) -> List[Fact]:
        """搜索相关记忆"""
        keywords = self.context_injector.extract_keywords(query)
        if not keywords:
            return []
        
        results = []
        for fact in self.memory_store:
            # 简单的关键词匹配
            content_lower = fact.content.lower()
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches > 0:
                # 计算相关性分数
                relevance = matches / len(keywords) * fact.confidence
                results.append((fact, relevance))
        
        # 按相关性排序
        results.sort(key=lambda x: x[1], reverse=True)
        return [fact for fact, _ in results[:limit]]
    
    def format(self, query: str = "", **kwargs) -> str:
        """格式化模板（支持记忆注入）"""
        # 1. 编译基础模板
        base_prompt = self.compile_template(kwargs)
        
        # 2. 搜索相关记忆
        context = self.search_memory(query) if query else []
        
        # 3. 注入上下文
        final_prompt = self.context_injector.inject_context(base_prompt, context)
        
        # 4. 应用变量系统插值
        for name, value in kwargs.items():
            self.variable_system.set_value(name, value, validate=False)
        
        # 应用剩余的变量
        final_prompt = self.variable_system.interpolate(final_prompt)
        
        return final_prompt
    
    def format_with_memory(self, memory_context: List[Fact], **kwargs) -> str:
        """使用指定的记忆上下文格式化"""
        # 编译基础模板
        base_prompt = self.compile_template(kwargs)
        
        # 注入指定上下文
        return self.context_injector.inject_context(base_prompt, memory_context)
    
    def add_parameterized_memory(self, template: str, parameters: Dict[str, Any]) -> Fact:
        """添加参数化记忆"""
        # 使用变量系统插值
        for name, value in parameters.items():
            self.variable_system.set_value(name, value, validate=False)
        
        content = self.variable_system.interpolate(template)
        
        # 创建事实
        fact = Fact(
            content=content,
            source="parameterized",
            confidence=0.8,
            tags=list(parameters.keys())
        )
        
        self.add_memory(fact)
        return fact
    
    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
    
    def get_template_info(self) -> Dict[str, Any]:
        """获取模板信息"""
        return {
            "template_type": self.template_type.value,
            "variable_count": len(self.variables),
            "memory_count": len(self.memory_store),
            "injection_mode": self.context_injector.injection_mode.value,
            "used_variables": self.get_used_variables()
        }


# ============================================================================
# 第六部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行提示词记忆注入测试套件")
    print("=" * 60)
    
    passed, total = 0, 8
    
    # 测试1: 基础模板变量替换
    print("\n📊 测试1: 基础模板变量替换")
    try:
        template = BasePromptTemplate("Hello, {{name}}!")
        template.add_variable(TemplateVariable("name", VariableType.STRING, required=True))
        result = template.compile_template({"name": "World"})
        assert "World" in result
        print("   ✅ 基础模板变量替换正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试2: 变量验证
    print("\n📊 测试2: 变量验证")
    try:
        template = BasePromptTemplate("Age: {{age}}")
        template.add_variable(TemplateVariable("age", VariableType.INTEGER, required=True))
        errors = template.validate_variables({"age": "not_a_number"})
        assert len(errors) > 0  # 应该有验证错误
        print("   ✅ 变量验证正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试3: 模板变量系统
    print("\n📊 测试3: 模板变量系统")
    try:
        var_system = TemplateVariableSystem()
        var_system.register_variable(TemplateVariable("username", VariableType.STRING, required=True))
        var_system.set_value("username", "Alice")
        assert var_system.get_value("username") == "Alice"
        result = var_system.interpolate("Hello, {{username}}!")
        assert "Alice" in result
        print("   ✅ 模板变量系统正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试4: 上下文注入
    print("\n📊 测试4: 上下文注入")
    try:
        injector = ContextInjector(InjectionMode.PREPEND)
        facts = [Fact("Python是流行语言", "system", confidence=0.9)]
        prompt = "如何学习编程？"
        result = injector.inject_context(prompt, facts)
        assert "Python" in result
        assert prompt in result
        print("   ✅ 上下文注入正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试5: MemoryPromptTemplate基础功能
    print("\n📊 测试5: MemoryPromptTemplate基础功能")
    try:
        template = MemoryPromptTemplate("问题: {{query}}")
        template.add_variable(TemplateVariable("query", VariableType.STRING, required=True))
        result = template.format(query="测试问题")
        assert "测试问题" in result
        print("   ✅ 基础功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试6: 记忆搜索和注入
    print("\n📊 测试6: 记忆搜索和注入")
    try:
        template = MemoryPromptTemplate("请回答以下问题：{{question}}")
        template.add_memory(Fact("Python适合数据分析", "expert", confidence=0.8, tags=["python", "data"]))
        template.add_memory(Fact("Java适合企业应用", "expert", confidence=0.7, tags=["java", "enterprise"]))
        
        result = template.format("数据分析用什么语言？", question="数据分析")
        assert "Python" in result or "python" in result.lower()
        print("   ✅ 记忆搜索和注入正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试7: 参数化记忆
    print("\n📊 测试7: 参数化记忆")
    try:
        template = MemoryPromptTemplate("模板测试")
        fact = template.add_parameterized_memory(
            "{{language}}适合{{domain}}开发",
            {"language": "Python", "domain": "Web"}
        )
        assert "Python" in fact.content
        assert "Web" in fact.content
        print("   ✅ 参数化记忆正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试8: 模板信息获取
    print("\n📊 测试8: 模板信息获取")
    try:
        template = MemoryPromptTemplate("测试模板")
        template.add_variable(TemplateVariable("test", VariableType.STRING))
        template.add_memory(Fact("测试记忆", "test"))
        info = template.get_template_info()
        assert info["variable_count"] == 1
        assert info["memory_count"] == 1
        print("   ✅ 模板信息获取正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试通过！")
    return passed == total


# ============================================================================
# 第七部分：演示主程序
# ============================================================================

def run_demo():
    """运行演示"""
    print("💬 Day 14 - 第54节课：提示词记忆注入演示")
    print("=" * 60)
    
    print("\n📝 演示1: 基础模板变量系统")
    
    # 创建基础模板
    base_template = BasePromptTemplate("""
用户: {{user_name}}
问题: {{question}}
时间: {{timestamp}}
    """)
    
    base_template.add_variable(TemplateVariable("user_name", VariableType.STRING, required=True))
    base_template.add_variable(TemplateVariable("question", VariableType.STRING, required=True))
    base_template.add_variable(TemplateVariable("timestamp", VariableType.STRING, default="未知时间"))
    
    result = base_template.compile_template({
        "user_name": "张三",
        "question": "如何学习AI？",
        "timestamp": "2024-03-27"
    })
    
    print("基础模板结果:")
    print(result)
    
    print("\n\n📝 演示2: MemoryPromptTemplate记忆注入")
    
    # 创建记忆模板
    memory_template = MemoryPromptTemplate("""
请基于以下上下文回答问题：

问题: {{query}}

请提供详细解答。
    """, injection_mode=InjectionMode.PREPEND)
    
    memory_template.add_variable(TemplateVariable("query", VariableType.STRING, required=True))
    
    # 添加记忆
    memories = [
        Fact("AI需要学习数学和编程", "expert", 0.9, tags=["ai", "learning"]),
        Fact("Python是AI开发的常用语言", "expert", 0.85, tags=["python", "ai"]),
        Fact("机器学习需要大量数据", "expert", 0.8, tags=["ml", "data"]),
        Fact("深度学习使用神经网络", "expert", 0.75, tags=["dl", "neural"]),
    ]
    
    for memory in memories:
        memory_template.add_memory(memory)
    
    # 测试不同查询
    queries = [
        "如何开始学习AI？",
        "推荐什么编程语言？",
        "需要哪些基础知识？",
    ]
    
    for query in queries:
        result = memory_template.format(query, query=query)
        print(f"\n查询: {query}")
        print(f"结果预览: {result[:200]}...")
    
    print("\n\n📝 演示3: 参数化记忆")
    
    # 创建参数化记忆
    param_memory = memory_template.add_parameterized_memory(
        "{{skill}}在{{domain}}领域很重要，需要{{time}}个月掌握",
        {"skill": "Python编程", "domain": "数据分析", "time": "3-6"}
    )
    
    print(f"参数化记忆内容: {param_memory.content}")
    print(f"记忆标签: {param_memory.tags}")
    
    print("\n\n📝 演示4: 模板信息")
    
    info = memory_template.get_template_info()
    print(f"模板信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if run_tests() else 1)
    else:
        run_demo()