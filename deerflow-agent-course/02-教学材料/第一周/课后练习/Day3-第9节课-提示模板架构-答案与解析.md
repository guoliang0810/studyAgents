# 🎓 Day 3 第9节课：提示模板架构 - 答案与解析

## 📋 答案说明

**目标**: 提供课后练习的参考答案和详细解析，帮助学生深入理解提示模板架构的核心概念。

**注意**: 以下答案供参考，实际实现可能有多种正确方式。鼓励学生探索不同的解决方案。

---

## 🧠 第一部分：概念理解与选择 - 答案与解析

### 1.1 多项选择题

**1. 提示模板五大设计原则中，哪一项负责定义AI的角色和专业领域？**
**答案**: B) 角色定义  
**解析**: 角色定义原则明确AI在对话中的身份、专业领域和职责范围，是模板的基础。其他原则：任务描述定义具体任务，约束条件设定限制，输出格式规定响应格式，示例演示提供范例。

**2. 在模板继承体系中，SystemPrompt、UserPrompt、ToolPrompt的主要区别是什么？**
**答案**: B) 使用场景和目标不同  
**解析**: SystemPrompt用于定义系统角色和约束，UserPrompt用于用户任务描述，ToolPrompt用于工具调用。它们服务于不同的AI交互场景，目标不同但互补。

**3. 模板渲染状态机中，哪个状态负责处理变量替换？**
**答案**: C) VARIABLE_SUBSTITUTION  
**解析**: VARIABLE_SUBSTITUTION状态专门处理模板中的变量占位符替换为实际值。IDLE是空闲状态，PARSING是解析状态，CONDITIONAL_PROCESSING处理条件逻辑，MULTILINGUAL_SWITCHING处理多语言切换。

**4. 多语言模板系统的回退机制主要解决什么问题？**
**答案**: C) 模板缺失时的优雅降级  
**解析**: 回退机制确保当请求的语言版本不存在时，系统能优雅地降级到其他可用语言版本，而不是直接失败，提高系统的健壮性和用户体验。

**5. 模块化模板设计中，PromptTemplate基类使用哪种设计模式？**
**答案**: C) 模板方法模式  
**解析**: PromptTemplate基类定义渲染算法的骨架（模板方法），将具体步骤延迟到子类实现，是典型的模板方法模式应用。其他模式：单例确保唯一实例，观察者处理事件通知，代理控制访问，装饰器动态添加功能。

### 1.2 判断题

**1. "好的提示模板应该尽可能长，包含所有可能的细节。"**
**答案**: 错误  
**解析**: 好的提示模板应该简洁而完整，过长会导致模型注意力分散，增加token消耗。模板应包含必要信息但避免冗余，遵循"最小必要信息"原则。

**2. "模板继承层次越深越好，可以最大化代码复用。"**
**答案**: 错误  
**解析**: 继承层次过深会增加复杂性，降低可维护性，可能导致"脆弱的基类"问题。一般建议继承层次不超过3-4层，优先使用组合而非深度继承。

**3. "多语言模板系统中，每个语言版本必须完全独立，不能共享任何代码。"**
**答案**: 错误  
**解析**: 多语言模板可以共享模板结构和逻辑，只需替换文本内容。完全独立会导致代码重复和维护困难。合理的设计是共享基类，子类提供语言特定内容。

**4. "模板渲染状态机必须严格按照顺序执行所有状态，不能跳过任何步骤。"**
**答案**: 错误  
**解析**: 状态机应根据实际情况灵活跳转。例如，如果模板没有条件逻辑，可以跳过CONDITIONAL_PROCESSING状态；如果不需要多语言支持，可以跳过MULTILINGUAL_SWITCHING状态。

**5. "验证五大设计原则只能通过人工检查，无法自动化实现。"**
**答案**: 错误  
**解析**: 可以通过关键词匹配、规则检查、自然语言处理等技术自动化验证五大原则。虽然自动化验证可能不完美，但可以大幅提高效率和一致性。

### 1.3 填空题

**1. 五大设计原则的英文缩写是: ______、______、______、______、______。**
**答案**: ROLE_DEFINITION、TASK_DESCRIPTION、CONSTRAINTS、OUTPUT_FORMAT、EXAMPLES

**2. 模板渲染状态机的三个核心状态是: ______ → ______ → ______。**
**答案**: PARSING → VARIABLE_SUBSTITUTION → VALIDATION  
**解析**: 这是最基本的渲染流程：解析模板 → 替换变量 → 验证结果。其他状态（条件处理、多语言切换）是可选的。

**3. 多语言模板系统的两个关键配置是: ______ 和 ______。**
**答案**: current_language、fallback_language  
**解析**: current_language指定当前使用的语言，fallback_language指定回退语言，用于处理模板缺失的情况。

**4. PromptTemplate基类的两个抽象方法是: ______ 和 ______。**
**答案**: get_template、render（或validate等，根据具体设计）  
**解析**: 常见的抽象方法包括get_template（获取模板内容）和render（渲染模板），具体设计可能有所不同。

**5. 模板质量评估的四个维度是: ______、______、______、______。**
**答案**: 完整性、清晰度、可维护性、原则符合性  
**解析**: 完整性检查是否包含所有必要部分，清晰度评估可读性，可维护性评估修改难度，原则符合性检查五大设计原则。

---

## 💻 第二部分：代码实现 - 答案与解析

### 2.1 实现五大原则验证器

**完整实现**:

```python
import re
from enum import Enum
from typing import Dict

class DesignPrinciple(Enum):
    ROLE_DEFINITION = "role_definition"
    TASK_DESCRIPTION = "task_description"
    CONSTRAINTS = "constraints"
    OUTPUT_FORMAT = "output_format"
    EXAMPLES = "examples"

class PrincipleValidator:
    """设计原则验证器"""
    
    @staticmethod
    def validate_role_definition(template: str) -> bool:
        """验证角色定义原则"""
        # 角色定义关键词（支持中英文）
        role_keywords = [
            "你是一个", "你扮演", "作为", "role:", "角色:", 
            "you are", "as a", "acting as", "扮演", "身份是"
        ]
        template_lower = template.lower()
        return any(keyword in template_lower for keyword in role_keywords)
    
    @staticmethod
    def validate_task_description(template: str) -> bool:
        """验证任务描述原则"""
        # 任务描述关键词
        task_keywords = [
            "任务是", "需要", "要求", "task:", "目标:", "目的:",
            "the task is", "need to", "required to", "goal:", "objective:"
        ]
        template_lower = template.lower()
        return any(keyword in template_lower for keyword in task_keywords)
    
    @staticmethod
    def validate_constraints(template: str) -> bool:
        """验证约束条件原则"""
        # 约束关键词
        constraint_keywords = [
            "不要", "避免", "必须", "禁止", "约束:", "限制:", "条件:",
            "do not", "avoid", "must", "prohibited", "constraint:", "limit:", "condition:"
        ]
        template_lower = template.lower()
        return any(keyword in template_lower for keyword in constraint_keywords)
    
    @staticmethod
    def validate_output_format(template: str) -> bool:
        """验证输出格式原则"""
        # 输出格式关键词
        format_keywords = [
            "格式:", "输出为", "结构:", "按以下格式", "json", "xml", "markdown", "yaml",
            "format:", "output as", "structure:", "in the following format"
        ]
        template_lower = template.lower()
        return any(keyword in template_lower for keyword in format_keywords)
    
    @staticmethod
    def validate_examples(template: str) -> bool:
        """验证示例演示原则"""
        # 示例关键词
        example_keywords = [
            "例如:", "例子:", "示例:", "example:", "e.g.", "比如:", "for example",
            "示例演示", "example demonstration"
        ]
        template_lower = template.lower()
        return any(keyword in template_lower for keyword in example_keywords)
    
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

# 测试用例
def test_principle_validator():
    """测试五大原则验证器"""
    test_cases = [
        (
            "你是一个代码助手。任务是优化代码。不要使用eval()。格式: JSON。例如: ...",
            [True, True, True, True, True]
        ),
        (
            "help me write code",
            [False, False, False, False, False]
        ),
        (
            "你是一个翻译助手。任务是翻译文本。",
            [True, True, False, False, False]
        ),
    ]
    
    for template, expected in test_cases:
        result = PrincipleValidator.validate_all(template)
        actual = [result[principle] for principle in DesignPrinciple]
        print(f"模板: {template[:50]}...")
        print(f"预期: {expected}")
        print(f"实际: {actual}")
        print(f"通过: {actual == expected}")
        print()

if __name__ == "__main__":
    test_principle_validator()
```

**关键点解析**:
1. **关键词设计**: 同时支持中英文关键词，提高验证准确性
2. **大小写处理**: 统一转换为小写进行匹配，避免大小写敏感问题
3. **可扩展性**: 关键词列表易于扩展和维护
4. **测试覆盖**: 提供多种测试用例，验证边界情况

### 2.2 实现模板渲染状态机

**完整实现**:

```python
from enum import Enum
from typing import Dict, Any

class TemplateRenderState(Enum):
    IDLE = "idle"
    PARSING = "parsing"
    VARIABLE_SUBSTITUTION = "variable_substitution"
    CONDITIONAL_PROCESSING = "conditional_processing"
    MULTILINGUAL_SWITCHING = "multilingual_switching"
    VALIDATION = "validation"
    COMPLETED = "completed"
    ERROR = "error"

class TemplateRenderEvent(Enum):
    START = "start"
    PARSE_COMPLETE = "parse_complete"
    VARIABLES_READY = "variables_ready"
    CONDITION_EVALUATED = "condition_evaluated"
    LANGUAGE_SELECTED = "language_selected"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    COMPLETE = "complete"
    ERROR = "error"

class TemplateRenderStateMachine:
    """模板渲染状态机"""
    
    def __init__(self):
        self.state = TemplateRenderState.IDLE
        self.context = {}
        self.transition_history = []
        
    def transition(self, event: TemplateRenderEvent, data: Dict[str, Any] = None) -> bool:
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
            
            print(f"  🔄 状态转移: {old_state.value} → {new_state.value} (事件: {event.value})")
            return True
        else:
            print(f"  ⏸️  状态保持: {old_state.value} (事件: {event.value})")
            return False
    
    def _get_next_state(self, state: TemplateRenderState, event: TemplateRenderEvent) -> TemplateRenderState:
        """获取下一个状态（状态转移表）"""
        transition_table = {
            # 正常流程
            (TemplateRenderState.IDLE, TemplateRenderEvent.START): TemplateRenderState.PARSING,
            (TemplateRenderState.PARSING, TemplateRenderEvent.PARSE_COMPLETE): TemplateRenderState.VARIABLE_SUBSTITUTION,
            (TemplateRenderState.VARIABLE_SUBSTITUTION, TemplateRenderEvent.VARIABLES_READY): TemplateRenderState.CONDITIONAL_PROCESSING,
            (TemplateRenderState.CONDITIONAL_PROCESSING, TemplateRenderEvent.CONDITION_EVALUATED): TemplateRenderState.MULTILINGUAL_SWITCHING,
            (TemplateRenderState.MULTILINGUAL_SWITCHING, TemplateRenderEvent.LANGUAGE_SELECTED): TemplateRenderState.VALIDATION,
            (TemplateRenderState.VALIDATION, TemplateRenderEvent.VALIDATION_PASSED): TemplateRenderState.COMPLETED,
            (TemplateRenderState.VALIDATION, TemplateRenderEvent.VALIDATION_FAILED): TemplateRenderState.ERROR,
            (TemplateRenderState.COMPLETED, TemplateRenderEvent.COMPLETE): TemplateRenderState.IDLE,
            (TemplateRenderState.ERROR, TemplateRenderEvent.ERROR): TemplateRenderState.IDLE,
            
            # 错误恢复流程
            (TemplateRenderState.ERROR, TemplateRenderEvent.START): TemplateRenderState.PARSING,
            
            # 跳过条件处理（如果没有条件）
            (TemplateRenderState.VARIABLE_SUBSTITUTION, TemplateRenderEvent.CONDITION_EVALUATED): TemplateRenderState.MULTILINGUAL_SWITCHING,
            
            # 跳过多语言切换（如果不需要）
            (TemplateRenderState.CONDITIONAL_PROCESSING, TemplateRenderEvent.LANGUAGE_SELECTED): TemplateRenderState.VALIDATION,
        }
        
        return transition_table.get((state, event), state)
    
    def render_template(self, template: str, variables: Dict[str, Any], language: str = "zh-CN") -> str:
        """渲染模板（完整流程）"""
        # 实现略，参考课堂演示代码
        pass

# 测试状态机
def test_state_machine():
    """测试状态机状态转移"""
    sm = TemplateRenderStateMachine()
    
    # 测试正常流程
    transitions = [
        (TemplateRenderEvent.START, None),
        (TemplateRenderEvent.PARSE_COMPLETE, None),
        (TemplateRenderEvent.VARIABLES_READY, None),
        (TemplateRenderEvent.CONDITION_EVALUATED, None),
        (TemplateRenderEvent.LANGUAGE_SELECTED, None),
        (TemplateRenderEvent.VALIDATION_PASSED, None),
        (TemplateRenderEvent.COMPLETE, None),
    ]
    
    print("测试正常流程:")
    for event, data in transitions:
        sm.transition(event, data)
    
    # 测试错误流程
    sm2 = TemplateRenderStateMachine()
    print("\n测试错误流程:")
    sm2.transition(TemplateRenderEvent.START)
    sm2.transition(TemplateRenderEvent.PARSE_COMPLETE)
    sm2.transition(TemplateRenderEvent.VALIDATION_FAILED)  # 直接验证失败
    sm2.transition(TemplateRenderEvent.ERROR)  # 错误恢复
    sm2.transition(TemplateRenderEvent.START)  # 重新开始

if __name__ == "__main__":
    test_state_machine()
```

**关键点解析**:
1. **完整状态转移表**: 覆盖所有可能的状态-事件组合
2. **错误恢复**: 支持从错误状态恢复，提高系统健壮性
3. **灵活跳转**: 支持跳过可选状态（如条件处理、多语言切换）
4. **状态历史**: 记录状态转移历史，便于调试和监控

### 2.3 实现多语言模板系统

**完整实现**:

```python
from collections import defaultdict
from typing import Dict, Optional

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
        if target_language in self.templates and name in self.templates[target_language]:
            print(f"✅ 找到模板 '{name}' ({target_language})")
            return self.templates[target_language][name]
        
        print(f"⚠️  模板 '{name}' 在语言 '{target_language}' 中未找到，尝试回退...")
        
        # 2. 尝试回退语言
        if self.fallback_language in self.templates and name in self.templates[self.fallback_language]:
            print(f"🔀 语言回退: {target_language} → {self.fallback_language}")
            return self.templates[self.fallback_language][name]
        
        # 3. 尝试任何语言
        for lang, templates in self.templates.items():
            if name in templates:
                print(f"🔀 语言回退: {target_language} → {lang}")
                return templates[name]
        
        # 4. 所有尝试失败
        error_msg = f"模板 '{name}' 在所有可用语言中均未找到"
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    def render_multilingual(self, name: str, variables: Dict[str, Any], language: str = None) -> str:
        """渲染多语言模板"""
        template = self.get_template(name, language)
        
        # 简单变量替换
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        
        return result

# 测试多语言系统
def test_multilingual_system():
    """测试多语言模板系统"""
    system = MultilingualTemplateSystem()
    
    # 注册模板
    system.register_template("welcome", "欢迎，{name}！", "zh-CN")
    system.register_template("welcome", "Welcome, {name}!", "en-US")
    system.register_template("welcome", "Bienvenue, {name}!", "fr-FR")
    
    # 测试正常获取
    print("测试1: 获取中文模板")
    template = system.get_template("welcome", "zh-CN")
    print(f"结果: {template}")
    
    # 测试回退获取
    print("\n测试2: 获取德语模板（回退到英文）")
    try:
        template = system.get_template("welcome", "de-DE")
        print(f"结果: {template}")
    except ValueError as e:
        print(f"错误: {e}")
    
    # 测试渲染
    print("\n测试3: 渲染多语言模板")
    variables = {"name": "张三"}
    for lang in ["zh-CN", "en-US", "fr-FR", "de-DE"]:
        try:
            result = system.render_multilingual("welcome", variables, lang)
            print(f"{lang}: {result}")
        except ValueError as e:
            print(f"{lang}: 错误 - {e}")

if __name__ == "__main__":
    test_multilingual_system()
```

**关键点解析**:
1. **三级回退机制**: 目标语言 → 回退语言 → 任何语言，确保高可用性
2. **详细日志**: 记录查找过程，便于调试和监控
3. **优雅错误处理**: 清晰错误信息，帮助快速定位问题
4. **灵活配置**: 支持动态设置当前语言和回退语言

---

## 🏗️ 第三部分：架构设计 - 答案与解析

### 3.1 设计电商客服Agent提示模板系统

**架构设计方案**:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                   电商客服Agent提示模板系统架构                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   模板分类层  │  │   多语言层   │  │ 个性化适配层 │  │ 质量保障层   ││
│  │ (Categories) │  │ (Multilingual)│  │ (Personalization)│  │ (Quality)   ││
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤│
│  │• 售前咨询    │  │• 中文模板    │  │• 用户等级识别 │  │• 五大原则验证 ││
│  │• 售后服务    │  │• 英文模板    │  │• 语气调整    │  │• 完整性检查   ││
│  │• 投诉处理    │  │• 日文模板    │  │• 内容个性化  │  │• A/B测试     ││
│  │• 退货退款    │  │• 翻译管理    │  │• 历史记录参考 │  │• 效果监控    ││
│  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘  └─────┬───────┘│
│        │                 │                 │                 │      │
│  ┌─────┴─────────────────┴─────────────────┴─────────────────┴─────┐│
│  │                    统一模板接口层 (TemplateService)               ││
│  ├─────────────────────────────────────────────────────────────────┤│
│  │• 模板获取与渲染                                                  ││
│  │• 变量替换与验证                                                  ││
│  │• 性能优化与缓存                                                  ││
│  │• 错误处理与回退                                                  ││
│  └─────┬─────────────────────────────────────────────────────────┬─┘│
│        │                                                         │  │
│  ┌─────┴─────┐                                         ┌─────────┴─┐│
│  │ 客户端SDK │                                         │ 管理控制台 ││
│  │ (Client)  │                                         │ (Console)  ││
│  ├───────────┤                                         ├───────────┤│
│  │• API调用   │                                         │• 模板编辑   ││
│  │• 本地缓存   │                                         │• 版本管理   ││
│  │• 自动刷新   │                                         │• 权限管理   ││
│  │• 降级策略   │                                         │• 数据分析   ││
│  └───────────┘                                         └───────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

**核心类和接口**:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum

class ScenarioType(Enum):
    """客服场景类型"""
    PRE_SALES = "pre_sales"      # 售前咨询
    AFTER_SALES = "after_sales"  # 售后服务
    COMPLAINT = "complaint"      # 投诉处理
    RETURN_REFUND = "return_refund"  # 退货退款

class UserLevel(Enum):
    """用户等级"""
    NORMAL = "normal"    # 普通用户
    VIP = "vip"          # VIP用户

class CustomerServiceTemplate(ABC):
    """客服模板基类"""
    
    def __init__(self, scenario: ScenarioType, base_template: str):
        self.scenario = scenario
        self.base_template = base_template
        self.language_versions = {}  # language -> template
        self.personalization_rules = {}
    
    @abstractmethod
    def personalize(self, user_level: UserLevel, user_history: Dict) -> str:
        """个性化调整模板"""
        pass
    
    def get_template(self, language: str = "zh-CN") -> str:
        """获取指定语言版本模板"""
        return self.language_versions.get(language, self.base_template)
    
    def add_language_version(self, language: str, template: str):
        """添加语言版本"""
        self.language_versions[language] = template

class EcommerceTemplateSystem:
    """电商模板系统"""
    
    def __init__(self):
        self.templates = {}  # scenario_type -> CustomerServiceTemplate
        self.quality_validator = TemplateQualityValidator()
        self.cache = TemplateCache()
    
    def render_template(self, scenario: ScenarioType, context: Dict[str, Any], 
                       language: str = "zh-CN", user_level: UserLevel = UserLevel.NORMAL) -> str:
        """渲染模板"""
        # 1. 获取模板
        template_obj = self.templates.get(scenario)
        if not template_obj:
            raise ValueError(f"未找到场景 '{scenario}' 的模板")
        
        # 2. 获取语言版本
        template = template_obj.get_template(language)
        
        # 3. 个性化调整
        personalized = template_obj.personalize(user_level, context.get("user_history", {}))
        
        # 4. 变量替换
        rendered = self._replace_variables(personalized, context)
        
        # 5. 质量验证
        if not self.quality_validator.validate(rendered):
            # 降级到基础模板
            rendered = self._replace_variables(template_obj.base_template, context)
        
        return rendered
```

**关键设计决策**:
1. **分层架构**: 分离关注点，提高可维护性
2. **模板继承**: 基类提供通用功能，场景类实现具体逻辑
3. **多语言管理**: 中心化语言版本管理，支持动态添加
4. **个性化适配**: 基于用户等级和历史进行动态调整
5. **质量保障**: 自动验证和降级机制，确保服务质量

**性能与扩展性**:
- **缓存策略**: 模板缓存、渲染结果缓存
- **懒加载**: 语言模板按需加载
- **水平扩展**: 无状态设计，支持多实例部署
- **监控指标**: 渲染成功率、响应时间、缓存命中率

### 3.2 设计模板性能优化方案

**优化方案**:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                   模板系统性能优化方案                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 优化维度      优化措施                         预期效果              │
├─────────────────────────────────────────────────────────────────────┤
│ 1. 缓存策略   • 模板解析结果缓存                减少50%解析时间       │
│              • 渲染结果缓存（带有效期）          减少70%渲染时间       │
│              • 多级缓存（内存→Redis→磁盘）      提高缓存命中率        │
│                                                                     │
│ 2. 懒加载     • 语言模板按需加载                减少80%内存占用       │
│              • 大模板分块加载                    提高加载速度         │
│              • 预加载热门模板                    提高响应速度         │
│                                                                     │
│ 3. 预编译     • 常用模板预编译为AST             减少90%渲染时间       │
│              • 变量引用预分析                    优化替换算法         │
│              • 条件逻辑预计算                    减少运行时开销       │
│                                                                     │
│ 4. 内存管理   • 对象池复用                     减少GC压力           │
│              • 内存映射文件                     减少内存拷贝         │
│              • 压缩存储                         减少存储空间         │
│                                                                     │
│ 5. 并发处理   • 无状态设计                     支持水平扩展         │
│              • 连接池管理                       提高并发能力         │
│              • 异步渲染                         提高吞吐量           │
└─────────────────────────────────────────────────────────────────────┘
```

**实施路线图**:

**短期（1-2周）**:
1. 实现模板解析结果缓存
2. 添加基础的内存管理
3. 优化变量替换算法

**中期（1-2月）**:
1. 实现多级缓存系统
2. 添加懒加载机制
3. 实现预编译优化

**长期（3-6月）**:
1. 构建分布式缓存
2. 实现智能预加载
3. 优化GC和内存管理

**监控指标**:
- 渲染响应时间P95/P99
- 缓存命中率
- 内存使用率
- 并发处理能力
- 错误率

### 3.3 设计模板版本管理和A/B测试系统

**系统设计**:

```python
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ExperimentStatus(Enum):
    DRAFT = "draft"          # 草稿
    RUNNING = "running"      # 运行中
    PAUSED = "paused"        # 暂停
    COMPLETED = "completed"  # 完成
    ARCHIVED = "archived"    # 归档

@dataclass
class TemplateVersion:
    """模板版本"""
    version_id: str
    template_name: str
    content: str
    language: str
    created_at: datetime
    created_by: str
    description: str
    metadata: Dict[str, Any]

@dataclass
class Experiment:
    """A/B测试实验"""
    experiment_id: str
    name: str
    description: str
    template_name: str
    language: str
    variants: List[TemplateVersion]  # 实验变体
    control_group: str  # 对照组版本ID
    traffic_allocation: Dict[str, float]  # 变体流量分配
    status: ExperimentStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    metrics: Dict[str, float]  # 评估指标
    
    def allocate_variant(self, user_id: str) -> str:
        """根据用户ID分配实验变体"""
        # 简单哈希算法分配
        hash_value = hash(user_id) % 100
        cumulative = 0
        for variant_id, percentage in self.traffic_allocation.items():
            cumulative += percentage
            if hash_value < cumulative:
                return variant_id
        return self.control_group

class TemplateVersioningSystem:
    """模板版本管理系统"""
    
    def __init__(self):
        self.versions = {}  # template_name -> List[TemplateVersion]
        self.experiments = {}  # experiment_id -> Experiment
    
    def create_version(self, template_name: str, content: str, 
                      language: str, created_by: str, description: str = "") -> TemplateVersion:
        """创建新版本"""
        version_id = f"{template_name}-{language}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        version = TemplateVersion(
            version_id=version_id,
            template_name=template_name,
            content=content,
            language=language,
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
            metadata={}
        )
        
        if template_name not in self.versions:
            self.versions[template_name] = []
        self.versions[template_name].append(version)
        
        return version
    
    def create_experiment(self, name: str, template_name: str, language: str,
                         variants: List[TemplateVersion], 
                         traffic_allocation: Dict[str, float]) -> Experiment:
        """创建A/B测试实验"""
        experiment_id = f"exp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 自动选择第一个变体作为对照组
        control_group = variants[0].version_id if variants else ""
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=f"A/B测试: {name}",
            template_name=template_name,
            language=language,
            variants=variants,
            control_group=control_group,
            traffic_allocation=traffic_allocation,
            status=ExperimentStatus.DRAFT,
            start_time=None,
            end_time=None,
            metrics={}
        )
        
        self.experiments[experiment_id] = experiment
        return experiment
    
    def get_template_for_user(self, template_name: str, language: str, 
                             user_id: str, context: Dict) -> str:
        """为用户获取模板（考虑实验分配）"""
        # 1. 查找相关实验
        active_experiments = [
            exp for exp in self.experiments.values()
            if (exp.template_name == template_name and 
                exp.language == language and 
                exp.status == ExperimentStatus.RUNNING)
        ]
        
        # 2. 分配实验变体
        selected_version_id = None
        for experiment in active_experiments:
            selected_version_id = experiment.allocate_variant(user_id)
            if selected_version_id != experiment.control_group:
                # 记录实验分配
                self._record_experiment_assignment(experiment.experiment_id, 
                                                  user_id, selected_version_id)
                break
        
        # 3. 获取模板内容
        if selected_version_id:
            # 查找实验变体
            for experiment in active_experiments:
                for variant in experiment.variants:
                    if variant.version_id == selected_version_id:
                        return variant.content
        
        # 4. 默认返回最新稳定版本
        return self.get_latest_stable_version(template_name, language)
```

**关键特性**:
1. **语义化版本管理**: 自动生成版本ID，支持版本回滚
2. **灵活的实验配置**: 支持多变量、自定义流量分配
3. **用户一致性**: 同一用户始终看到相同变体
4. **效果评估**: 内置指标收集和分析
5. **安全发布**: 灰度发布、快速回滚机制

**发布流程**:
```text
1. 创建模板版本 → 2. 代码审查 → 3. 单元测试 → 4. 集成测试 → 
5. 创建实验 → 6. 小流量测试 → 7. 逐步放量 → 8. 全量发布 → 
9. 效果评估 → 10. 版本固化
```

---

## 🎯 第四部分：场景应用 - 答案与解析

### 4.1 翻译助手模板设计

**完整实现**:

```python
from typing import Dict, List, Optional

class TranslationAssistantPrompt(PromptTemplate):
    """翻译助手提示模板"""
    
    def __init__(self, source_lang: str, target_lang: str, 
                 formality: str = "neutral", domain: str = "general"):
        name = f"translation_{source_lang}_to_{target_lang}_{domain}"
        description = f"翻译助手: {source_lang} → {target_lang} ({domain}领域)"
        
        super().__init__(name, description)
        
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.formality = formality  # formal, neutral, informal
        self.domain = domain
        self.terminology = {}  # 术语库
        
        # 设置验证规则
        self.validation_rules = {
            "required": ["text", "context"],
            "optional": ["style_preference", "format_requirements"]
        }
    
    def get_template(self) -> str:
        """生成专业翻译模板"""
        # 根据正式程度调整语气
        formality_map = {
            "formal": "正式",
            "neutral": "中性", 
            "informal": "非正式"
        }
        formality_text = formality_map.get(self.formality, "中性")
        
        # 构建术语库提示
        terminology_hint = ""
        if self.terminology:
            term_list = "\n".join([f"- {src}: {tgt}" for src, tgt in self.terminology.items()])
            terminology_hint = f"\n\n请使用以下术语对照表:\n{term_list}"
        
        template = f"""你是一个专业的{self.domain}领域翻译助手，精通{self.source_lang}和{self.target_lang}。

任务是将{self.source_lang}文本翻译成{self.target_lang}，保持{formality_text}语气。

约束条件:
1. 准确传达原文意思，不随意增删内容
2. 考虑文化差异，进行适当的本地化调整
3. 保持专业术语的一致性
4. 输出流畅自然的{self.target_lang}表达
5. 如果原文有特定格式（如Markdown、代码块），请保持格式
6. 如果遇到歧义，根据上下文选择最合适的翻译

输出格式:
1. 翻译结果
2. 翻译说明（可选，如有需要说明的文化差异或翻译决策）
3. 术语表（本次翻译使用的新术语）

示例:
原文: "Hello, world! This is a test."
翻译结果: "你好，世界！这是一个测试。"
翻译说明: "保持原文的感叹语气，'test'译为'测试'符合技术语境。"

{terminology_hint}

现在请翻译以下文本: {{text}}

上下文信息: {{context}}
{{#if style_preference}}
风格偏好: {{style_preference}}
{{/if}}
{{#if format_requirements}}
格式要求: {{format_requirements}}
{{/if}}"""
        
        return template
    
    def add_terminology(self, source_term: str, target_term: str):
        """添加术语映射"""
        self.terminology[source_term] = target_term
    
    def evaluate_translation_quality(self, source: str, translation: str) -> float:
        """评估翻译质量（简化实现）"""
        # 在实际系统中，这里会调用翻译质量评估API或使用BLEU等指标
        # 这里实现一个简化的评估逻辑
        
        score = 0.0
        
        # 1. 长度检查（翻译不应过长或过短）
        source_len = len(source)
        translation_len = len(translation)
        length_ratio = translation_len / max(source_len, 1)
        if 0.5 <= length_ratio <= 2.0:
            score += 0.3
        
        # 2. 术语一致性检查
        term_match_score = 0.0
        for src_term, tgt_term in self.terminology.items():
            if src_term in source and tgt_term in translation:
                term_match_score += 1.0
        if self.terminology:
            term_match_ratio = term_match_score / len(self.terminology)
            score += term_match_ratio * 0.3
        
        # 3. 格式保持检查（简化）
        format_indicators = ["```", "**", "*", "# ", "> "]
        format_preserved = 0
        for indicator in format_indicators:
            if indicator in source and indicator in translation:
                format_preserved += 1
        format_score = format_preserved / max(len(format_indicators), 1)
        score += format_score * 0.2
        
        # 4. 语言规范性检查（简化）
        # 在实际系统中会使用语言模型或语法检查器
        score += 0.2  # 基础分
        
        return min(score, 1.0)

# 使用示例
def demo_translation_assistant():
    """演示翻译助手"""
    # 创建技术文档翻译助手
    translator = TranslationAssistantPrompt(
        source_lang="英文",
        target_lang="中文", 
        formality="formal",
        domain="技术文档"
    )
    
    # 添加术语
    translator.add_terminology("API", "应用程序接口")
    translator.add_terminology("database", "数据库")
    translator.add_terminology("framework", "框架")
    
    # 渲染模板
    context = {
        "text": "The API provides access to the database through a RESTful interface.",
        "context": "技术文档翻译，需要准确传达技术概念",
        "style_preference": "技术文档风格，简洁准确",
        "format_requirements": "保持原文的技术术语和格式"
    }
    
    template = translator.get_template()
    print("📋 翻译模板:")
    print(template[:500], "...")
    print()
    
    # 评估翻译质量
    source = "The API provides access to the database."
    translation = "应用程序接口提供对数据库的访问。"
    quality = translator.evaluate_translation_quality(source, translation)
    print(f"📊 翻译质量评分: {quality:.2f}/1.0")
```

**设计要点**:
1. **领域特定**: 支持不同领域的专业翻译
2. **术语管理**: 内置术语库确保一致性
3. **质量评估**: 简易质量评估算法
4. **灵活配置**: 支持正式程度、格式要求等参数

### 4.2 代码审查助手模板设计

**完整实现**:

```python
from typing import List, Dict, Any
from enum import Enum

class CodeLanguage(Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"

class CodeReviewPrompt(PromptTemplate):
    """代码审查助手提示模板"""
    
    def __init__(self, language: CodeLanguage, strict_mode: bool = True, 
                 focus_areas: List[str] = None):
        name = f"code_review_{language.value}_{'strict' if strict_mode else 'normal'}"
        description = f"代码审查助手: {language.value}语言，{'严格' if strict_mode else '普通'}模式"
        
        super().__init__(name, description)
        
        self.language = language
        self.strict_mode = strict_mode
        self.focus_areas = focus_areas or ["性能", "安全", "可读性", "可维护性"]
        self.custom_rules = {}
        
        # 设置验证规则
        self.validation_rules = {
            "required": ["code", "purpose"],
            "optional": ["context", "constraints", "existing_issues"]
        }
    
    def get_template(self) -> str:
        """生成代码审查模板"""
        # 语言特定的审查要点
        language_tips = {
            CodeLanguage.PYTHON: "检查PEP8规范、类型注解、异常处理",
            CodeLanguage.JAVA: "检查代码规范、异常处理、设计模式",
            CodeLanguage.JAVASCRIPT: "检查ES6+特性、异步处理、错误处理",
            CodeLanguage.TYPESCRIPT: "检查类型安全、接口设计、泛型使用",
            CodeLanguage.GO: "检查错误处理、并发安全、代码组织",
            CodeLanguage.RUST: "检查所有权、生命周期、错误处理",
        }
        
        language_tip = language_tips.get(self.language, "检查代码质量和最佳实践")
        
        # 严格模式额外要求
        strict_requirements = ""
        if self.strict_mode:
            strict_requirements = """
严格模式额外要求:
1. 零容忍安全漏洞
2. 性能必须达到最优
3. 代码必须完全符合规范
4. 必须提供详细的优化建议
"""
        
        # 关注区域
        focus_text = "\n".join([f"- {area}" for area in self.focus_areas])
        
        # 自定义规则
        custom_rules_text = ""
        if self.custom_rules:
            rules_list = "\n".join([f"- {name}: {desc}" for name, desc in self.custom_rules.items()])
            custom_rules_text = f"\n自定义审查规则:\n{rules_list}"
        
        template = f"""你是一个专业的{self.language.value}代码审查专家，具有10年以上开发经验。

任务是审查以下{self.language.value}代码，提供全面的质量评估和改进建议。

审查要点:
{focus_text}

{language_tip}

约束条件:
1. 只审查代码质量问题，不修改功能逻辑
2. 按优先级排序问题（严重、重要、建议）
3. 每个问题必须提供具体理由和修改建议
4. 避免主观意见，基于事实和最佳实践
5. 考虑代码的上下文和用途
{strict_requirements}

输出格式:
## 代码审查报告

### 总体评估
- 质量等级: [优秀/良好/合格/需改进]
- 主要问题: [简要总结]

### 详细问题列表
#### 严重问题（必须修复）
1. [问题描述]
   - 位置: [行号]
   - 影响: [说明影响]
   - 建议: [修改建议]
   - 示例: [修改示例]

#### 重要问题（建议修复）
...

#### 改进建议（可选）
...

### 总结与建议
- 主要优点: [列出优点]
- 关键改进: [优先级最高的改进]
- 后续步骤: [具体行动建议]
{custom_rules_text}

示例:
代码: `for i in range(len(items)): print(items[i])`
问题: 使用低效的索引遍历
建议: 改为直接迭代 `for item in items: print(item)`

现在请审查以下代码:

代码:
```{self.language.value}
{{code}}
```

代码用途: {{purpose}}
{{#if context}}
上下文: {{context}}
{{/if}}
{{#if constraints}}
约束条件: {{constraints}}
{{/if}}
{{#if existing_issues}}
已知问题: {{existing_issues}}
{{/if}}"""
        
        return template
    
    def add_custom_rule(self, rule_name: str, rule_description: str):
        """添加自定义审查规则"""
        self.custom_rules[rule_name] = rule_description
    
    def generate_report(self, code: str, issues: List[Dict]) -> str:
        """生成审查报告（简化实现）"""
        # 在实际系统中，这里会根据AI的审查结果生成结构化报告
        # 这里提供一个示例报告生成逻辑
        
        if not issues:
            return "✅ 代码审查通过，未发现明显问题。"
        
        # 按严重程度分组
        critical = [i for i in issues if i.get("severity") == "critical"]
        important = [i for i in issues if i.get("severity") == "important"]
        suggestion = [i for i in issues if i.get("severity") == "suggestion"]
        
        report = f"""## 代码审查报告

### 总体评估
- 质量等级: {'需改进' if critical else '良好' if important else '优秀'}
- 主要问题: 发现{len(critical)}个严重问题，{len(important)}个重要问题，{len(suggestion)}个改进建议

"""
        
        if critical:
            report += "### 严重问题（必须修复）\n"
            for i, issue in enumerate(critical, 1):
                report += f"{i}. {issue.get('description', '未知问题')}\n"
                report += f"   - 位置: {issue.get('location', '未知')}\n"
                report += f"   - 影响: {issue.get('impact', '未知')}\n"
                report += f"   - 建议: {issue.get('suggestion', '无')}\n\n"
        
        if important:
            report += "### 重要问题（建议修复）\n"
            for i, issue in enumerate(important, 1):
                report += f"{i}. {issue.get('description', '未知问题')}\n"
                report += f"   - 位置: {issue.get('location', '未知')}\n"
                report += f"   - 建议: {issue.get('suggestion', '无')}\n\n"
        
        if suggestion:
            report += "### 改进建议（可选）\n"
            for i, issue in enumerate(suggestion, 1):
                report += f"{i}. {issue.get('description', '未知问题')}\n"
        
        report += "### 总结与建议\n"
        if critical:
            report += "- 主要优点: 代码功能基本完整\n"
            report += f"- 关键改进: 优先修复{len(critical)}个严重问题\n"
            report += "- 后续步骤: 立即修复严重问题，然后处理重要问题\n"
        else:
            report += "- 主要优点: 代码质量良好\n"
            report += "- 关键改进: 可以考虑优化性能和可读性\n"
            report += "- 后续步骤: 按优先级处理改进建议\n"
        
        return report

# 使用示例
def demo_code_review():
    """演示代码审查助手"""
    # 创建Python代码审查器
    reviewer = CodeReviewPrompt(
        language=CodeLanguage.PYTHON,
        strict_mode=True,
        focus_areas=["安全", "性能", "可读性"]
    )
    
    # 添加自定义规则
    reviewer.add_custom_rule("no_hardcoded_secrets", "禁止硬编码密钥和密码")
    reviewer.add_custom_rule("type_hints_required", "必须添加类型注解")
    
    # 渲染模板
    context = {
        "code": "def process_data(data):\n    return [x*2 for x in data]",
        "purpose": "数据处理函数，用于批量处理数据",
        "context": "生产环境核心模块",
        "constraints": "需要高性能处理大量数据"
    }
    
    template = reviewer.get_template()
    print("📋 代码审查模板:")
    print(template[:500], "...")
    print()
    
    # 生成示例报告
    sample_issues = [
        {
            "severity": "critical",
            "description": "缺少输入验证，可能引发安全漏洞",
            "location": "第1行",
            "impact": "可能被注入恶意数据",
            "suggestion": "添加数据验证和类型检查"
        },
        {
            "severity": "important", 
            "description": "列表推导式可能内存占用高",
            "location": "第2行",
            "suggestion": "考虑使用生成器表达式"
        }
    ]
    
    report = reviewer.generate_report(context["code"], sample_issues)
    print("📊 示例审查报告:")
    print(report)
```

**设计要点**:
1. **语言特定**: 针对不同编程语言提供专业审查
2. **严格模式**: 支持不同严格级别的审查
3. **自定义规则**: 可扩展的审查规则系统
4. **结构化报告**: 生成易于理解的审查报告

### 4.3 客服Agent动态模板选择系统

**设计框架**:

```python
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class UserEmotion(Enum):
    """用户情绪"""
    ANGRY = "angry"        # 愤怒
    FRUSTRATED = "frustrated"  # 沮丧
    NEUTRAL = "neutral"    # 中性
    HAPPY = "happy"        # 高兴
    CONFUSED = "confused"  # 困惑

class ProblemType(Enum):
    """问题类型"""
    TECHNICAL = "technical"      # 技术问题
    BILLING = "billing"          # 账单问题
    ACCOUNT = "account"          # 账户问题
    PRODUCT = "product"          # 产品问题
    GENERAL = "general"          # 一般咨询

@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    level: str  # normal, vip, svip
    history: List[Dict]  # 历史交互记录
    preferences: Dict[str, Any]  # 用户偏好

class DynamicTemplateSelector:
    """动态模板选择器"""
    
    def __init__(self, template_registry: Dict[str, Dict]):
        self.template_registry = template_registry  # template_name -> metadata
        self.emotion_keywords = {
            UserEmotion.ANGRY: ["生气", "愤怒", "不满意", "投诉", "垃圾"],
            UserEmotion.FRUSTRATED: ["困惑", "不明白", "怎么", "为什么", "不懂"],
            UserEmotion.HAPPY: ["谢谢", "感谢", "很好", "满意", "棒"],
            UserEmotion.CONFUSED: ["?", "怎么", "如何", "请问", "帮助"],
        }
        self.problem_keywords = {
            ProblemType.TECHNICAL: ["错误", "bug", "崩溃", "无法", "问题"],
            ProblemType.BILLING: ["扣费", "账单", "付款", "价格", "收费"],
            ProblemType.ACCOUNT: ["登录", "注册", "密码", "账号", "验证"],
            ProblemType.PRODUCT: ["功能", "使用", "教程", "指南", "操作"],
        }
        
        # 模板匹配规则
        self.matching_rules = [
            # (条件函数, 模板名称, 优先级)
            (self._is_angry_user, "安抚模板", 100),
            (self._is_vip_user, "VIP专属模板", 90),
            (self._is_technical_problem, "技术问题模板", 80),
            (self._is_billing_problem, "账单问题模板", 70),
            (lambda f, p, h: True, "通用客服模板", 10),  # 默认
        ]
    
    def extract_features(self, user_input: str, user_profile: UserProfile) -> Dict:
        """提取特征"""
        features = {
            "emotion": self._detect_emotion(user_input),
            "problem_type": self._detect_problem_type(user_input),
            "urgency": self._detect_urgency(user_input),
            "complexity": self._detect_complexity(user_input),
            "user_level": user_profile.level,
            "interaction_count": len(user_profile.history),
            "previous_satisfaction": self._calculate_previous_satisfaction(user_profile.history),
        }
        return features
    
    def _detect_emotion(self, text: str) -> UserEmotion:
        """检测用户情绪"""
        text_lower = text.lower()
        for emotion, keywords in self.emotion_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return emotion
        return UserEmotion.NEUTRAL
    
    def _detect_problem_type(self, text: str) -> ProblemType:
        """检测问题类型"""
        text_lower = text.lower()
        for problem_type, keywords in self.problem_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return problem_type
        return ProblemType.GENERAL
    
    def _detect_urgency(self, text: str) -> int:
        """检测紧急程度（1-5）"""
        urgency_indicators = {
            5: ["紧急", "立刻", "马上", "现在", "asap", "urgent"],
            4: ["尽快", "赶快", "快点", "急", "quickly"],
            3: ["问题", "帮忙", "帮助", "麻烦"],
            2: ["咨询", "了解", "请问", "想问"],
            1: ["谢谢", "感谢", "好评"],  # 低紧急度
        }
        
        text_lower = text.lower()
        for level, keywords in urgency_indicators.items():
            if any(keyword in text_lower for keyword in keywords):
                return level
        return 3  # 默认中等紧急度
    
    def _detect_complexity(self, text: str) -> int:
        """检测问题复杂度（1-5）"""
        # 基于文本长度和特殊符号
        length = len(text)
        if length > 200:
            return 5
        elif length > 100:
            return 4
        elif length > 50:
            return 3
        elif length > 20:
            return 2
        else:
            return 1
    
    def _calculate_previous_satisfaction(self, history: List[Dict]) -> float:
        """计算历史满意度"""
        if not history:
            return 0.5  # 默认
        
        scores = [h.get("satisfaction_score", 0) for h in history]
        return sum(scores) / len(scores)
    
    def select_template(self, features: Dict) -> str:
        """选择模板"""
        # 应用匹配规则
        applicable_rules = []
        for condition_func, template_name, priority in self.matching_rules:
            if condition_func(features, None, None):  # 简化调用
                applicable_rules.append((template_name, priority))
        
        if not applicable_rules:
            return "通用客服模板"
        
        # 选择优先级最高的模板
        applicable_rules.sort(key=lambda x: x[1], reverse=True)
        return applicable_rules[0][0]
    
    def adjust_template(self, template: str, user_profile: UserProfile) -> str:
        """个性化调整模板"""
        adjusted = template
        
        # 根据用户等级调整语气
        if user_profile.level == "vip":
            adjusted = adjusted.replace("尊敬的客户", "尊敬的VIP客户")
            adjusted += "\n（作为VIP客户，您将享受优先服务）"
        elif user_profile.level == "svip":
            adjusted = adjusted.replace("尊敬的客户", "尊贵的SVIP客户")
            adjusted += "\n（作为SVIP客户，您将享受专属服务经理服务）"
        
        # 根据历史记录调整
        if user_profile.history:
            last_interaction = user_profile.history[-1]
            if last_interaction.get("satisfaction_score", 0) < 0.3:
                adjusted += "\n（我们注意到上次服务未能让您满意，本次将特别关注您的问题）"
        
        return adjusted
    
    def collect_feedback(self, conversation_id: str, satisfaction_score: float):
        """收集反馈"""
        # 在实际系统中，这里会将反馈存储到数据库
        # 并更新用户画像和模板选择算法
        
        print(f"📊 收集反馈: 会话 {conversation_id}, 满意度 {satisfaction_score}")
        
        # 根据反馈调整算法
        if satisfaction_score < 0.3:
            print("⚠️  低满意度反馈，可能需要调整模板选择策略")
        elif satisfaction_score > 0.8:
            print("✅ 高满意度反馈，当前模板选择策略有效")
    
    # 匹配规则条件函数
    def _is_angry_user(self, features: Dict, profile, history) -> bool:
        return features.get("emotion") == UserEmotion.ANGRY
    
    def _is_vip_user(self, features: Dict, profile, history) -> bool:
        return features.get("user_level") in ["vip", "svip"]
    
    def _is_technical_problem(self, features: Dict, profile, history) -> bool:
        return features.get("problem_type") == ProblemType.TECHNICAL
    
    def _is_billing_problem(self, features: Dict, profile, history) -> bool:
        return features.get("problem_type") == ProblemType.BILLING

# 使用示例
def demo_dynamic_selector():
    """演示动态模板选择器"""
    selector = DynamicTemplateSelector({})
    
    # 模拟用户输入和画像
    user_inputs = [
        ("你们的产品又出bug了！根本无法使用！", "愤怒用户"),
        ("请问如何修改账户密码？", "普通咨询"),
        ("我是VIP客户，账单有问题", "VIP账单问题"),
        ("谢谢你们的帮助，问题解决了", "满意用户"),
    ]
    
    user_profile = UserProfile(
        user_id="user123",
        level="vip",
        history=[
            {"satisfaction_score": 0.8, "problem": "技术问题"},
            {"satisfaction_score": 0.9, "problem": "一般咨询"},
        ],
        preferences={"prefer_formal": True}
    )
    
    for user_input, description in user_inputs:
        print(f"\n📝 用户输入: {description}")
        print(f"  内容: {user_input}")
        
        # 提取特征
        features = selector.extract_features(user_input, user_profile)
        print(f"  提取特征: {features}")
        
        # 选择模板
        template_name = selector.select_template(features)
        print(f"  选择模板: {template_name}")
        
        # 调整模板
        adjusted = selector.adjust_template(f"[{template_name}] 您好，有什么可以帮您？", user_profile)
        print(f"  调整后模板: {adjusted[:50]}...")
```

**设计要点**:
1. **特征提取**: 多维度特征分析
2. **规则引擎**: 基于规则的模板匹配
3. **个性化调整**: 基于用户画像的动态调整
4. **反馈学习**: 持续优化的反馈机制

---

## 📊 第五部分：综合挑战 - 参考答案

### 5.1 模板系统性能压测方案

**压测方案设计**:

```python
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

class TemplateSystemBenchmark:
    """模板系统性能压测"""
    
    def __init__(self, template_system):
        self.system = template_system
        self.results = []
    
    def benchmark_rendering(self, template_name: str, variables: Dict[str, Any], 
                           concurrency: int = 10, requests: int = 100) -> Dict[str, Any]:
        """压测渲染性能"""
        print(f"🚀 开始渲染压测: {concurrency}并发，{requests}请求")
        
        latencies = []
        errors = 0
        
        def render_request():
            start = time.time()
            try:
                self.system.render_template(template_name, variables)
                latency = time.time() - start
                return {"success": True, "latency": latency}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(render_request) for _ in range(requests)]
            
            for future in futures:
                result = future.result()
                if result["success"]:
                    latencies.append(result["latency"])
                else:
                    errors += 1
        
        # 计算统计指标
        if latencies:
            stats = {
                "total_requests": requests,
                "successful_requests": len(latencies),
                "failed_requests": errors,
                "error_rate": errors / requests,
                "avg_latency": statistics.mean(latencies),
                "p95_latency": self._percentile(latencies, 95),
                "p99_latency": self._percentile(latencies, 99),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "throughput": len(latencies) / (max(latencies) if latencies else 1),
            }
        else:
            stats = {"error": "所有请求失败"}
        
        self.results.append({
            "scenario": f"渲染压测_{concurrency}并发",
            "stats": stats
        })
        
        return stats
    
    def benchmark_loading(self, template_count: int, template_size: str = "medium") -> Dict[str, Any]:
        """压测模板加载性能"""
        # 实现略
        pass
    
    def benchmark_cache(self, cache_size: int) -> Dict[str, Any]:
        """压测缓存性能"""
        # 实现略
        pass
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        weight = index - lower
        
        if upper >= len(sorted_data):
            return sorted_data[lower]
        
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def generate_report(self) -> str:
        """生成压测报告"""
        report = "# 模板系统性能压测报告\n\n"
        
        for result in self.results:
            report += f"## {result['scenario']}\n"
            stats = result['stats']
            
            if 'error' in stats:
                report += f"错误: {stats['error']}\n"
            else:
                report += f"- 总请求数: {stats['total_requests']}\n"
                report += f"- 成功请求: {stats['successful_requests']}\n"
                report += f"- 失败请求: {stats['failed_requests']}\n"
                report += f"- 错误率: {stats['error_rate']:.2%}\n"
                report += f"- 平均延迟: {stats['avg_latency']*1000:.2f}ms\n"
                report += f"- P95延迟: {stats['p95_latency']*1000:.2f}ms\n"
                report += f"- P99延迟: {stats['p99_latency']*1000:.2f}ms\n"
                report += f"- 最小延迟: {stats['min_latency']*1000:.2f}ms\n"
                report += f"- 最大延迟: {stats['max_latency']*1000:.2f}ms\n"
                report += f"- 吞吐量: {stats['throughput']:.2f} req/s\n"
            
            report += "\n"
        
        # 瓶颈分析
        report += "## 瓶颈分析与优化建议\n"
        report += "### 识别到的瓶颈:\n"
        report += "1. **模板解析**: 复杂模板解析耗时较长\n"
        report += "2. **变量替换**: 大量变量替换影响性能\n"
        report += "3. **内存分配**: 频繁的对象创建导致GC压力\n"
        report += "4. **并发竞争**: 高并发下的锁竞争\n\n"
        
        report += "### 优化建议:\n"
        report += "1. **缓存优化**: 预编译模板AST，缓存解析结果\n"
        report += "2. **算法优化**: 优化变量替换算法，使用索引加速\n"
        report += "3. **内存池**: 实现对象池，减少内存分配\n"
        report += "4. **无锁设计**: 使用无锁数据结构减少竞争\n"
        report += "5. **异步处理**: 非关键路径异步执行\n"
        
        return report

# 使用示例
def run_benchmark():
    """运行压测"""
    # 创建模板系统实例
    system = create_template_system()  # 假设函数
    
    benchmark = TemplateSystemBenchmark(system)
    
    # 测试不同并发级别
    concurrency_levels = [1, 10, 50, 100]
    for concurrency in concurrency_levels:
        stats = benchmark.benchmark_rendering(
            template_name="welcome",
            variables={"name": "测试用户", "date": "2024-01-01"},
            concurrency=concurrency,
            requests=1000
        )
        print(f"并发{concurrency}结果: {stats}")
    
    # 生成报告
    report = benchmark.generate_report()
    print(report)
```

**压测报告要点**:
1. **测试环境**: 硬件配置、软件版本、网络条件
2. **测试场景**: 渲染、加载、缓存等不同场景
3. **性能指标**: 延迟、吞吐量、错误率、资源使用率
4. **瓶颈分析**: 识别性能瓶颈和根本原因
5. **优化建议**: 具体的优化措施和实施优先级

### 5.2 模板系统安全审计方案

**安全审计要点**:

```text
1. 注入攻击防护
   - 风险: 模板变量可能包含恶意代码
   - 检查点: 变量过滤、转义处理、沙箱执行
   - 建议: 实现严格的输入验证和输出编码

2. 敏感信息泄露
   - 风险: 模板可能包含API密钥、密码等敏感信息
   - 检查点: 代码审查、配置管理、日志过滤
   - 建议: 使用环境变量、密钥管理服务、最小权限原则

3. 权限控制
   - 风险: 未授权访问模板或管理功能
   - 检查点: 认证授权、访问控制、API权限
   - 建议: 实现RBAC、API密钥轮换、审计日志

4. 拒绝服务攻击
   - 风险: 恶意模板导致资源耗尽
   - 检查点: 资源限制、请求限流、超时控制
   - 建议: 实现资源配额、速率限制、熔断机制

5. 数据完整性
   - 风险: 模板被篡改或注入恶意内容
   - 检查点: 数字签名、完整性校验、版本控制
   - 建议: 使用HMAC签名、定期校验、安全更新
```

**加固方案**:
1. **输入验证**: 对所有输入进行严格验证和过滤
2. **输出编码**: 根据上下文进行适当的输出编码
3. **最小权限**: 模板系统以最小必要权限运行
4. **安全配置**: 安全的默认配置和定期安全更新
5. **监控告警**: 实时监控和异常告警

### 5.3 模板系统监控告警设计

**监控指标体系**:

```yaml
# 业务指标
business_metrics:
  - name: template_rendering_success_rate
    description: 模板渲染成功率
    threshold: < 99.9%
    alert_level: warning
    
  - name: template_rendering_latency_p95
    description: 模板渲染P95延迟
    threshold: > 100ms
    alert_level: warning
    
  - name: template_cache_hit_rate
    description: 模板缓存命中率
    threshold: < 80%
    alert_level: info
    
  - name: multilingual_fallback_rate
    description: 多语言回退率
    threshold: > 10%
    alert_level: warning

# 技术指标
technical_metrics:
  - name: system_cpu_usage
    description: 系统CPU使用率
    threshold: > 80%
    alert_level: warning
    
  - name: system_memory_usage
    description: 系统内存使用率
    threshold: > 85%
    alert_level: warning
    
  - name: active_connections
    description: 活跃连接数
    threshold: > 1000
    alert_level: warning
    
  - name: error_rate
    description: 错误率
    threshold: > 1%
    alert_level: critical
```

**告警规则示例**:
```python
alert_rules = [
    {
        "name": "high_error_rate",
        "condition": "error_rate > 5% for 5m",
        "severity": "critical",
        "channels": ["slack", "pagerduty"],
        "message": "模板系统错误率超过5%，请立即检查"
    },
    {
        "name": "high_latency",
        "condition": "rendering_latency_p95 > 200ms for 10m",
        "severity": "warning",
        "channels": ["slack"],
        "message": "模板渲染延迟升高，可能需要扩容"
    },
    {
        "name": "low_cache_hit",
        "condition": "cache_hit_rate < 60% for 30m",
        "severity": "info",
        "channels": ["email"],
        "message": "缓存命中率较低，考虑优化缓存策略"
    }
]
```

**仪表板设计**:
```text
模板系统监控仪表板
├── 概览面板
│   ├── 当前状态（健康/警告/异常）
│   ├── 关键指标（成功率、延迟、QPS）
│   └── 系统资源（CPU、内存、磁盘）
├── 性能面板
│   ├── 渲染延迟趋势（P50/P95/P99）
│   ├── 吞吐量趋势（请求/秒）
│   └── 缓存效率（命中率、大小）
├── 业务面板
│   ├── 模板使用排行（热门模板）
│   ├── 多语言分布（语言使用统计）
│   └── 用户满意度（反馈评分）
└── 告警面板
    ├── 当前告警（活跃告警列表）
    ├── 历史告警（最近24小时）
    └── 告警统计（按严重程度）
```

---

## 📝 学习总结建议

**收获反思**:
1. **技术深度**: 深入理解了提示模板架构的各个层面
2. **实践能力**: 通过代码实现掌握了核心技术的应用
3. **设计思维**: 培养了系统化设计和架构思考能力
4. **问题解决**: 学会了分析和解决复杂问题的系统方法

**改进方向**:
1. **性能优化**: 进一步学习高并发系统的性能调优
2. **安全实践**: 加强安全意识和安全编码实践
3. **监控运维**: 掌握生产系统的监控和运维技能
4. **团队协作**: 学习大型项目的团队协作和代码管理

**下一步计划**:
1. **项目实践**: 在实际项目中应用所学知识
2. **深入阅读**: 阅读相关论文和开源项目代码
3. **社区贡献**: 参与开源项目，贡献代码和经验
4. **持续学习**: 关注AI Agent技术的最新发展

---

**恭喜完成Day 3第9节课的学习！通过本次练习，您已经掌握了提示模板架构的核心技术，为成为AI Agent架构师奠定了坚实基础。继续坚持，成功就在前方！** 🚀

---
*答案编制: 张老师*  
*编制日期: 2024年3月27日*  
*版本: v1.0*  
*适用对象: DeerFlow Python Agent架构师训练营学员*