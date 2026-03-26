# 🎓 Day 3 第9节课：提示模板架构 - 课后练习

## 📋 练习说明

**目标**: 通过本练习，巩固提示模板架构的核心概念，掌握五大设计原则、模板继承体系、模板渲染技术和模块化设计方法。

**建议时间**: 60-90分钟
**难度**: 中等
**提交方式**: 完成代码实现和设计文档，提交到GitHub仓库

---

## 🧠 第一部分：概念理解与选择

### 1.1 多项选择题

**1. 提示模板五大设计原则中，哪一项负责定义AI的角色和专业领域？**
A) 任务描述  
B) 角色定义  
C) 约束条件  
D) 输出格式  
E) 示例演示

**2. 在模板继承体系中，SystemPrompt、UserPrompt、ToolPrompt的主要区别是什么？**
A) 颜色和样式不同  
B) 使用场景和目标不同  
C) 编程语言不同  
D) 文件大小不同  
E) 没有区别

**3. 模板渲染状态机中，哪个状态负责处理变量替换？**
A) IDLE  
B) PARSING  
C) VARIABLE_SUBSTITUTION  
D) CONDITIONAL_PROCESSING  
E) MULTILINGUAL_SWITCHING

**4. 多语言模板系统的回退机制主要解决什么问题？**
A) 性能优化  
B) 内存管理  
C) 模板缺失时的优雅降级  
D) 安全验证  
E) 代码压缩

**5. 模块化模板设计中，PromptTemplate基类使用哪种设计模式？**
A) 单例模式  
B) 观察者模式  
C) 模板方法模式  
D) 代理模式  
E) 装饰器模式

### 1.2 判断题

判断以下说法是否正确，并简要说明理由：

**1. "好的提示模板应该尽可能长，包含所有可能的细节。"**
- [ ] 正确  
- [ ] 错误  
**理由**: 

**2. "模板继承层次越深越好，可以最大化代码复用。"**
- [ ] 正确  
- [ ] 错误  
**理由**: 

**3. "多语言模板系统中，每个语言版本必须完全独立，不能共享任何代码。"**
- [ ] 正确  
- [ ] 错误  
**理由**: 

**4. "模板渲染状态机必须严格按照顺序执行所有状态，不能跳过任何步骤。"**
- [ ] 正确  
- [ ] 错误  
**理由**: 

**5. "验证五大设计原则只能通过人工检查，无法自动化实现。"**
- [ ] 正确  
- [ ] 错误  
**理由**: 

### 1.3 填空题

**1. 五大设计原则的英文缩写是: ______、______、______、______、______。**

**2. 模板渲染状态机的三个核心状态是: ______ → ______ → ______。**

**3. 多语言模板系统的两个关键配置是: ______ 和 ______。**

**4. PromptTemplate基类的两个抽象方法是: ______ 和 ______。**

**5. 模板质量评估的四个维度是: ______、______、______、______。**

---

## 💻 第二部分：代码实现

### 2.1 实现五大原则验证器

**任务**: 完善以下`PrincipleValidator`类，实现完整的五大原则验证逻辑。

```python
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
        # TODO: 实现验证逻辑
        # 要求: 检查模板是否包含角色定义关键词
        pass
    
    @staticmethod
    def validate_task_description(template: str) -> bool:
        """验证任务描述原则"""
        # TODO: 实现验证逻辑
        # 要求: 检查模板是否清晰描述任务
        pass
    
    @staticmethod
    def validate_constraints(template: str) -> bool:
        """验证约束条件原则"""
        # TODO: 实现验证逻辑
        # 要求: 检查模板是否明确约束条件
        pass
    
    @staticmethod
    def validate_output_format(template: str) -> bool:
        """验证输出格式原则"""
        # TODO: 实现验证逻辑
        # 要求: 检查模板是否定义输出格式
        pass
    
    @staticmethod
    def validate_examples(template: str) -> bool:
        """验证示例演示原则"""
        # TODO: 实现验证逻辑
        # 要求: 检查模板是否提供示例
        pass
    
    @classmethod
    def validate_all(cls, template: str) -> Dict[DesignPrinciple, bool]:
        """验证所有五大原则"""
        # TODO: 调用上述方法，返回验证结果字典
        pass
```

**要求**:
1. 为每个方法实现具体的验证逻辑
2. 考虑边缘情况（如大小写、空格等）
3. 添加适当的注释说明验证逻辑
4. 编写至少3个测试用例验证实现正确性

### 2.2 实现模板渲染状态机

**任务**: 完善以下`TemplateRenderStateMachine`类的`_get_next_state`方法，实现完整的状态转移逻辑。

```python
class TemplateRenderStateMachine:
    """模板渲染状态机"""
    
    def _get_next_state(self, state: TemplateRenderState, event: TemplateRenderEvent) -> TemplateRenderState:
        """获取下一个状态（状态转移表）"""
        # TODO: 实现状态转移表
        # 要求: 根据当前状态和事件返回下一个状态
        # 状态转移规则:
        # 1. IDLE + START → PARSING
        # 2. PARSING + PARSE_COMPLETE → VARIABLE_SUBSTITUTION
        # 3. VARIABLE_SUBSTITUTION + VARIABLES_READY → CONDITIONAL_PROCESSING
        # 4. CONDITIONAL_PROCESSING + CONDITION_EVALUATED → MULTILINGUAL_SWITCHING
        # 5. MULTILINGUAL_SWITCHING + LANGUAGE_SELECTED → VALIDATION
        # 6. VALIDATION + VALIDATION_PASSED → COMPLETED
        # 7. VALIDATION + VALIDATION_FAILED → ERROR
        # 8. COMPLETED + COMPLETE → IDLE
        # 9. ERROR + ERROR → IDLE
        # 其他情况保持当前状态
        pass
```

**要求**:
1. 实现完整的状态转移表
2. 处理所有可能的状态-事件组合
3. 添加错误处理（如无效的状态转移）
4. 编写状态机测试，模拟完整的渲染流程

### 2.3 实现多语言模板系统

**任务**: 完善以下`MultilingualTemplateSystem`类的`get_template`方法，实现模板查找和回退机制。

```python
class MultilingualTemplateSystem:
    """多语言模板系统"""
    
    def get_template(self, name: str, language: str = None) -> str:
        """获取模板（支持回退）"""
        # TODO: 实现模板查找逻辑
        # 要求:
        # 1. 如果指定语言存在模板，返回该模板
        # 2. 否则，尝试回退语言（self.fallback_language）
        # 3. 如果回退语言也没有，尝试任何可用的语言
        # 4. 如果所有语言都没有，抛出ValueError
        # 5. 在查找过程中输出适当的日志信息
        pass
```

**要求**:
1. 实现三级回退机制（目标语言 → 回退语言 → 任何语言）
2. 添加详细的日志输出，便于调试
3. 处理边界情况（如语言参数为None）
4. 编写测试用例验证回退逻辑

---

## 🏗️ 第三部分：架构设计

### 3.1 设计电商客服Agent提示模板系统

**背景**: 某电商公司需要为客服Agent设计提示模板系统，支持以下功能：
- 多场景：售前咨询、售后服务、投诉处理、退货退款
- 多语言：中文、英文、日文
- 个性化：根据用户等级（普通、VIP）调整服务语气
- 质量控制：确保所有模板符合五大设计原则

**任务**: 设计完整的提示模板系统架构，包括：
1. **模板分类体系**: 如何组织不同场景的模板？
2. **继承关系设计**: 设计模板类的继承层次
3. **多语言支持**: 如何实现多语言模板管理？
4. **个性化机制**: 如何根据用户等级动态调整模板？
5. **质量保障**: 如何确保模板质量？

**输出要求**:
- 绘制系统架构图（文字描述或ASCII图）
- 定义核心类和接口
- 描述关键设计决策和权衡
- 预估性能和扩展性考虑

### 3.2 设计模板性能优化方案

**问题**: 当模板数量达到1000+，多语言版本达到5种时，模板系统的性能出现瓶颈：
1. 模板加载速度慢
2. 内存占用高
3. 渲染延迟明显

**任务**: 设计性能优化方案，包括：
1. **缓存策略**: 哪些内容可以缓存？缓存失效策略？
2. **懒加载机制**: 如何实现按需加载？
3. **预编译优化**: 如何预编译常用模板？
4. **内存管理**: 如何减少内存占用？
5. **并发处理**: 如何支持高并发渲染？

**输出要求**:
- 列出具体的优化措施
- 分析每项措施的性能收益和成本
- 设计监控指标和告警机制
- 提供实施路线图（短期/中期/长期）

### 3.3 设计模板版本管理和A/B测试系统

**需求**: 团队需要能够：
1. 管理模板的不同版本
2. 进行A/B测试对比不同模板效果
3. 灰度发布新模板
4. 快速回滚有问题的模板

**任务**: 设计版本管理和A/B测试系统，包括：
1. **版本控制**: 如何存储和管理模板版本？
2. **实验管理**: 如何设计和管理A/B测试实验？
3. **流量分配**: 如何分配用户到不同实验组？
4. **效果评估**: 如何评估模板效果？
5. **发布流程**: 设计安全的发布和回滚流程

**输出要求**:
- 设计数据库表结构或存储方案
- 定义实验配置格式
- 描述流量分配算法
- 设计效果评估指标体系
- 绘制发布流程图

---

## 🎯 第四部分：场景应用

### 4.1 翻译助手模板设计

**场景**: 设计一个专业的翻译助手提示模板，支持中英互译，特别关注：
- 文化适应性（避免直译导致的歧义）
- 专业术语统一
- 格式保持（如Markdown、代码块）
- 语气适应（正式/非正式）

**任务**:
1. 设计符合五大原则的翻译助手模板
2. 实现多语言版本（至少中、英文）
3. 添加术语库支持接口
4. 设计质量评估方法

**代码要求**:
```python
class TranslationAssistantPrompt(PromptTemplate):
    """翻译助手提示模板"""
    
    def __init__(self, source_lang: str, target_lang: str, formality: str = "neutral"):
        # TODO: 初始化方法
        pass
    
    def get_template(self) -> str:
        # TODO: 生成专业翻译模板
        pass
    
    def add_terminology(self, term: str, translation: str):
        # TODO: 添加术语映射
        pass
    
    def evaluate_translation_quality(self, source: str, translation: str) -> float:
        # TODO: 评估翻译质量（简化实现）
        pass
```

### 4.2 代码审查助手模板设计

**场景**: 设计代码审查助手模板，帮助开发者：
- 识别代码质量问题
- 提供改进建议
- 遵循编码规范
- 学习最佳实践

**任务**:
1. 设计针对不同编程语言（Python/Java/JavaScript）的审查模板
2. 实现可配置的审查规则（如严格模式、宽松模式）
3. 添加示例代码和修正建议
4. 设计输出格式（如分级报告、具体建议）

**代码要求**:
```python
class CodeReviewPrompt(PromptTemplate):
    """代码审查助手提示模板"""
    
    def __init__(self, language: str, strict_mode: bool = True):
        # TODO: 初始化方法
        pass
    
    def get_template(self) -> str:
        # TODO: 生成代码审查模板
        pass
    
    def add_custom_rule(self, rule_name: str, rule_description: str):
        # TODO: 添加自定义审查规则
        pass
    
    def generate_report(self, code: str, issues: List[Dict]) -> str:
        # TODO: 生成审查报告
        pass
```

### 4.3 客服Agent动态模板选择系统

**场景**: 电商客服Agent需要根据用户情绪、问题类型、历史记录动态选择最合适的模板。

**任务**: 设计动态模板选择系统，包括：
1. **特征提取**: 从用户输入中提取关键特征
2. **模板匹配**: 根据特征选择最合适的模板
3. **个性化调整**: 基于用户画像调整模板内容
4. **效果反馈**: 收集用户满意度，优化选择算法

**设计要求**:
- 设计特征提取算法
- 设计模板匹配算法（如规则引擎、机器学习）
- 设计A/B测试框架验证效果
- 设计反馈收集和优化流程

**代码框架**:
```python
class DynamicTemplateSelector:
    """动态模板选择器"""
    
    def extract_features(self, user_input: str, user_profile: Dict) -> Dict:
        # TODO: 提取特征
        pass
    
    def select_template(self, features: Dict) -> str:
        # TODO: 选择模板
        pass
    
    def adjust_template(self, template: str, user_profile: Dict) -> str:
        # TODO: 个性化调整
        pass
    
    def collect_feedback(self, conversation_id: str, satisfaction_score: float):
        # TODO: 收集反馈
        pass
```

---

## 📊 第五部分：综合挑战

### 5.1 模板系统性能压测

**任务**: 设计并实施模板系统性能压测方案：
1. 设计压测场景（高并发渲染、大模板加载等）
2. 实现压测脚本
3. 收集性能指标（响应时间、吞吐量、错误率）
4. 分析瓶颈并提出优化建议

**输出**: 压测报告，包括：
- 测试环境配置
- 测试场景描述
- 性能指标数据
- 瓶颈分析
- 优化建议

### 5.2 模板系统安全审计

**任务**: 对模板系统进行安全审计，识别潜在风险：
1. **注入攻击**: 模板变量是否可能被注入恶意代码？
2. **敏感信息泄露**: 模板是否可能泄露敏感信息？
3. **权限控制**: 模板访问是否有适当的权限控制？
4. **拒绝服务**: 是否可能通过恶意模板导致DoS？

**输出**: 安全审计报告，包括：
- 识别出的安全风险
- 风险等级评估
- 修复建议
- 安全加固方案

### 5.3 模板系统监控告警设计

**任务**: 设计完整的监控告警系统：
1. **监控指标**: 定义关键业务和技术指标
2. **数据采集**: 设计数据采集方案
3. **告警规则**: 设计告警规则和阈值
4. **可视化**: 设计监控仪表板

**输出**: 监控告警设计方案，包括：
- 监控指标列表
- 数据采集架构
- 告警规则配置
- 仪表板设计图

---

## 📝 提交要求

1. **代码文件**: 所有实现的Python代码文件
2. **设计文档**: 架构设计、方案设计等文档
3. **测试报告**: 测试用例和测试结果
4. **学习总结**: 本次练习的收获和反思

**评分标准**:
- 概念理解正确性: 20%
- 代码实现完整性: 30%
- 架构设计合理性: 30%
- 场景应用创新性: 20%

---

## 🔧 学习资源

1. **参考代码**: 课堂演示代码 `/课堂演示代码/day3-lesson9/`
2. **官方文档**: DeerFlow提示模板模块文档
3. **扩展阅读**: 
   - [OpenAI提示工程最佳实践](https://platform.openai.com/docs/guides/prompt-engineering)
   - [LangChain提示模板设计](https://python.langchain.com/docs/modules/model_io/prompts/)
   - [微软提示模式库](https://github.com/microsoft/prompt-engineering)

4. **工具推荐**:
   - 模板语法检查工具
   - 多语言翻译API
   - 代码质量分析工具

---

**祝您学习愉快，通过实践深入掌握提示模板架构的核心技术！** 🚀

---
*练习设计: 张老师*  
*设计日期: 2024年3月27日*  
*版本: v1.0*  
*适用对象: DeerFlow Python Agent架构师训练营学员*