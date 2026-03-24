# 🎓 详细教案 - Day 10 第37节课：SubagentExecutor架构

## 📋 课程基本信息
- **课程名称**: SubagentExecutor架构
- **授课日期**: 2024年4月3日（周三）
- **上课时间**: 9:00-9:45（第1节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: Python基础一般，已完成虚拟路径系统和沙箱安全机制课程
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. 理解子代理系统的核心概念和多Agent协作架构
2. 掌握SubagentExecutor的组件设计和执行流程
3. 了解子代理配置、任务和结果的数据模型定义

### 技能目标（学生将能够）
1. 设计和实现符合DeerFlow规范的子代理基类
2. 编写SubagentExecutor核心执行逻辑
3. 创建专用的子代理（如代码专家子代理）并注册到执行引擎

### 情感/态度目标
1. 培养模块化设计和关注点分离的架构思维
2. 增强对多任务并发执行和资源管理的理解
3. 提升系统可扩展性和可维护性的设计意识

## 📚 教学重点与难点
- **教学重点**: 子代理系统架构、SubagentExecutor设计、异步任务执行
- **教学难点**: 异步编程模型、任务状态管理、错误处理机制
- **突破方法**: 通过类比（如公司部门结构）、代码演示、分步骤实现降低理解难度

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（16GB+ RAM，支持AVX指令集）
- **软件**: Python 3.12.0、VS Code、Git、Docker Desktop
- **工具**: asyncio调试工具、性能监控工具
- **代码**: DeerFlow 2.0代码库、子代理系统示例代码
- **演示材料**: PPT幻灯片、架构图、执行流程图
- **学生材料**: 练习手册、代码模板、评估表

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员<br>2. 回顾上节课沙箱安全机制<br>3. 介绍本节课子代理系统主题 | 1. 登录课堂<br>2. 准备学习材料<br>3. 思考预习问题 | PPT幻灯片第1-3页 |
| 2-5分钟 | 知识激活 | 1. 提问："什么是子代理？为什么需要子代理系统？"<br>2. 引导思考多Agent协作的优势<br>3. 连接沙箱安全与子代理执行的关系 | 1. 回答问题<br>2. 参与讨论<br>3. 提出疑问 | 白板、互动问答工具 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-8分钟 | 子代理系统架构 | 1. 讲解子代理系统整体架构<br>2. 展示架构图（主代理与子代理关系）<br>3. 解释子代理的特点和优势 | 1. 观看演示<br>2. 记录架构要点<br>3. 思考实际应用场景 | PPT第4-6页，架构图 |
| 8-12分钟 | 数据模型定义 | 1. 讲解SubagentConfig和SubagentResult<br>2. 演示数据类定义和字段说明<br>3. 强调配置验证的重要性 | 1. 跟随代码讲解<br>2. 理解配置参数含义<br>3. 记录关键数据结构 | VS Code演示，代码示例1 |
| 12-15分钟 | 子代理基类设计 | 1. 讲解BaseSubagent抽象基类<br>2. 演示抽象方法和属性定义<br>3. 讲解任务验证机制 | 1. 学习抽象基类设计<br>2. 理解接口约定<br>3. 记录基类实现要点 | PPT第7-9页，代码示例2 |
| 15-20分钟 | 专用子代理实现 | 1. 讲解CodeExpertSubagent实现<br>2. 演示配置定义和执行逻辑<br>3. 展示子代理测试方法 | 1. 学习具体子代理实现<br>2. 理解任务执行流程<br>3. 记录实现模式 | 代码示例3，测试脚本 |

### 阶段3：互动练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 练习1：创建子代理配置 | 1. 布置配置创建任务<br>2. 巡视并提供指导<br>3. 解答学生疑问 | 1. 设计自己的子代理配置<br>2. 编写SubagentConfig数据类<br>3. 验证配置合理性 | 练习指导文档，配置模板 |
| 25-30分钟 | 练习2：实现子代理基类 | 1. 指导学生实现BaseSubagent<br>2. 检查常见实现错误<br>3. 演示正确实现方法 | 1. 实现抽象基类<br>2. 添加任务验证方法<br>3. 测试基类功能 | 代码编辑器，测试框架 |
| 30-35分钟 | 练习3：创建专用子代理 | 1. 指导学生创建具体子代理<br>2. 演示完整实现流程<br>3. 讲解测试方法 | 1. 创建专用子代理类<br>2. 实现配置和执行方法<br>3. 编写单元测试 | 子代理模板，测试用例 |

### 阶段4：总结与评估（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 总结本节课核心知识点<br>2. 强调子代理系统设计要点<br>3. 连接下节课任务调度内容 | 1. 回顾学习内容<br>2. 整理笔记<br>3. 准备提问 | PPT总结页 |
| 38-42分钟 | 问题解答 | 1. 回答学生疑问<br>2. 澄清常见概念误解<br>3. 提供额外学习资源 | 1. 提出问题<br>2. 参与讨论<br>3. 记录解答 | 问题收集工具 |
| 42-45分钟 | 课后任务布置 | 1. 布置课后作业<br>2. 说明作业要求<br>3. 预告下节课内容 | 1. 记录作业要求<br>2. 明确完成标准<br>3. 准备课后学习 | 作业说明文档 |

## 🗣️ 师生互动设计

### 提问设计（关键问题）
1. **导入问题**："在一个大项目中，如何分工协作？子代理系统和项目团队有什么相似之处？"
2. **探究问题**："为什么需要抽象基类？直接实现具体子代理有什么问题？"
3. **应用问题**："如果你要设计一个数据分析子代理，应该有哪些配置参数？"
4. **反思问题**："子代理系统中，错误处理应该在哪一层实现？为什么？"

### 互动活动
1. **小组讨论**：2人一组，讨论子代理系统的应用场景（3分钟）
2. **设计评审**：互相评审对方的子代理配置设计（5分钟）
3. **头脑风暴**：设计一个支持多种类型子代理的注册系统（4分钟）

### 反馈机制
1. **实时反馈**：通过在线工具收集学生理解程度（绿色/黄色/红色）
2. **代码反馈**：教师实时查看学生代码并提供建议
3. **设计反馈**：学生互相评价子代理设计合理性

## 👥 差异化教学

### 针对基础薄弱学生
1. **简化任务**：提供完整的代码模板，只需填写关键部分
2. **额外指导**：安排助教一对一指导抽象基类概念
3. **分步演示**：将复杂实现分解为更小的步骤，逐步完成

### 针对进阶学生
1. **扩展挑战**：实现子代理的依赖注入和动态配置
2. **深度研究**：研究asyncio在子代理系统中的高级应用
3. **创新设计**：设计支持插件化的子代理扩展系统

### 共同支持策略
1. **合作学习**：混合分组，让不同水平学生互相帮助
2. **分层资源**：提供基础、标准、高级三种难度的练习材料
3. **弹性时间**：允许学生在课后继续完成未完成的练习

## 📊 评估方式

### 形成性评估（课堂内）
1. **观察记录**：教师观察学生练习完成情况（权重30%）
2. **代码检查**：检查学生编写的子代理实现代码（权重40%）
3. **问答参与**：记录学生提问和回答质量（权重30%）

### 评估标准
- **优秀（85-100分）**：完整实现所有功能，代码规范，设计合理，理解深入
- **良好（70-84分）**：基本实现功能，代码规范，设计合理，理解正确
- **合格（60-69分）**：部分实现功能，需要指导完成，基本理解概念
- **待改进（<60分）**：未能完成核心功能，需要额外辅导

### 反馈方式
1. **即时反馈**：课堂练习时直接提供指导
2. **书面反馈**：课后提供详细的代码评语
3. **一对一反馈**：针对困难学生安排单独辅导

## 🚨 应急预案

### 技术故障
1. **Python环境问题**：准备Docker容器镜像，可快速切换环境
2. **异步编程问题**：提供同步版本的简化示例，降低理解难度
3. **工具故障**：准备备用开发环境和代码编辑器

### 学生困难
1. **无法理解抽象基类**：使用具体示例逐步引入抽象概念
2. **异步编程困惑**：提供同步实现的对比示例，理解异步优势
3. **时间不足**：提供课后扩展练习和补充视频教程

### 内容调整
1. **进度过快**：增加基础练习，放慢抽象概念讲解
2. **进度过慢**：跳过扩展内容，保证核心概念和实现完成
3. **兴趣不足**：增加实际应用案例，展示子代理系统的威力

## 💭 教学反思（课后填写）

### 学生表现
- 理解程度：
- 参与程度：
- 困难点：

### 教学效果
- 目标达成：
- 时间控制：
- 资源使用：

### 改进建议
- 内容调整：
- 方法优化：
- 资源补充：

## 📝 课后任务

### 必做任务
1. **基础练习**：创建一个数学计算子代理，支持加、减、乘、除运算
2. **代码实现**：实现BaseSubagent抽象基类和MathExpertSubagent具体类
3. **集成测试**：编写测试脚本，验证数学子代理功能正常

### 选做任务（挑战）
1. **配置扩展**：为子代理添加更多配置参数，如内存限制、并发限制等
2. **性能监控**：为子代理执行添加性能监控和统计功能
3. **插件化设计**：设计支持动态加载子代理的插件系统

### 预习任务
1. **阅读材料**：预习下一节"任务调度算法"的学生讲义
2. **思考问题**："当有多个子代理任务需要执行时，如何决定执行顺序？"
3. **准备环境**：确保asyncio环境可用，用于下一课的任务调度实验

## 📎 附录

### 附录1：PPT幻灯片大纲
```
幻灯片1：课程标题与目标
幻灯片2：回顾与导入
幻灯片3：子代理系统架构图
幻灯片4：多Agent协作优势
幻灯片5：SubagentConfig数据结构
幻灯片6：SubagentResult数据结构
幻灯片7：BaseSubagent抽象基类
幻灯片8：CodeExpertSubagent实现
幻灯片9：执行引擎概述
幻灯片10：互动练习说明
幻灯片11：知识总结
幻灯片12：课后任务
幻灯片13：Q&A
```

### 附录2：子代理系统架构图
```python
"""
子代理系统架构：

┌─────────────────────────────────────────┐
│           Lead Agent (主代理)            │
│  • 任务分解                              │
│  • 结果整合                              │
│  • 流程协调                              │
└───────────────────┬─────────────────────┘
                    │
        ┌───────────┼───────────┬───────────────┐
        │           │           │               │
        ▼           ▼           ▼               ▼
    ┌───────┐  ┌───────┐  ┌─────────┐  ┌───────────┐
    │代码专家│  │搜索专家│  │数据专家 │  │写作专家  │
    │子代理  │  │子代理  │  │子代理   │  │子代理    │
    └───────┘  └───────┘  └─────────┘  └───────────┘

子代理特点：
• 专门化：每个子代理专注特定领域
• 并行：多个子代理同时工作
• 隔离：子代理之间相互独立
• 协作：结果汇总给主代理
"""
```

### 附录3：子代理数据模型代码示例
```python
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional

@dataclass
class SubagentConfig:
    """子代理配置"""
    name: str                    # 子代理名称，如 "code_expert"
    role: str                    # 角色描述，如 "代码专家"
    capabilities: List[str]      # 能力列表，如 ["代码生成", "代码审查"]
    max_execution_time: float = 60.0    # 最大执行时间（秒）
    max_retries: int = 3                 # 最大重试次数
    timeout: float = 30.0                # 超时时间（秒）
    memory_limit: Optional[str] = None   # 内存限制，如 "1GB"
    sandbox_enabled: bool = True         # 是否启用沙箱
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        if not self.name:
            errors.append("子代理名称不能为空")
        
        if not self.role:
            errors.append("角色描述不能为空")
        
        if not self.capabilities:
            errors.append("能力列表不能为空")
        
        if self.max_execution_time <= 0:
            errors.append("最大执行时间必须大于0")
        
        if self.max_retries < 0:
            errors.append("最大重试次数不能为负数")
        
        return errors

@dataclass
class SubagentResult:
    """子代理执行结果"""
    subagent_name: str          # 子代理名称
    success: bool               # 是否成功
    output: Any                 # 输出结果
    error: Optional[str] = None # 错误信息
    execution_time: float = 0.0 # 执行时间（秒）
    metadata: Dict = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "subagent_name": self.subagent_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


@dataclass
class SubagentTask:
    """子代理任务"""
    id: str                     # 任务ID
    subagent_name: str          # 目标子代理名称
    description: str            # 任务描述
    parameters: Dict = field(default_factory=dict)  # 任务参数
    priority: int = 1           # 优先级（1-10，越高越优先）
    created_at: float = field(default_factory=time.time)  # 创建时间
    
    def validate(self) -> tuple[bool, str]:
        """验证任务"""
        if not self.id:
            return False, "任务ID不能为空"
        
        if not self.subagent_name:
            return False, "子代理名称不能为空"
        
        if not self.description:
            return False, "任务描述不能为空"
        
        if self.priority < 1 or self.priority > 10:
            return False, "优先级必须在1-10之间"
        
        return True, "验证通过"
```

### 附录4：子代理基类实现示例
```python
from abc import ABC, abstractmethod
import asyncio
import time
from typing import Dict, Any, Optional, Tuple

class BaseSubagent(ABC):
    """子代理抽象基类"""
    
    @property
    @abstractmethod
    def config(self) -> SubagentConfig:
        """返回子代理配置
        
        子类必须实现此属性，返回自己的配置对象
        """
        pass
    
    @abstractmethod
    async def execute(self, task: Dict) -> SubagentResult:
        """执行任务
        
        Args:
            task: 任务字典，包含任务描述和参数
            
        Returns:
            SubagentResult: 执行结果
        """
        pass
    
    async def validate_task(self, task: Dict) -> Tuple[bool, str]:
        """验证任务参数
        
        Args:
            task: 任务字典
            
        Returns:
            (是否有效, 错误信息)
        """
        # 基础验证：检查必需字段
        required_fields = ["description"]
        
        for field in required_fields:
            if field not in task:
                return False, f"缺少必需字段: {field}"
        
        # 调用子类的自定义验证
        if hasattr(self, "_custom_validate"):
            return await self._custom_validate(task)
        
        return True, "验证通过"
    
    async def execute_with_retry(
        self,
        task: Dict,
        max_retries: int = None,
        retry_delay: float = 1.0
    ) -> SubagentResult:
        """带重试的执行
        
        Args:
            task: 任务字典
            max_retries: 最大重试次数，默认为配置中的值
            retry_delay: 重试延迟（秒）
            
        Returns:
            SubagentResult: 最终执行结果
        """
        max_retries = max_retries or self.config.max_retries
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                result = await self.execute(task)
                
                if result.success:
                    return result
                
                # 执行失败但非异常，记录日志
                print(f"子代理 {self.config.name} 执行失败: {result.error}")
                retry_count += 1
                
            except Exception as e:
                # 执行异常，记录日志
                print(f"子代理 {self.config.name} 执行异常: {e}")
                retry_count += 1
            
            # 最后一次重试后直接返回
            if retry_count > max_retries:
                break
            
            # 等待后重试
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # 指数退避
        
        # 所有重试都失败
        return SubagentResult(
            subagent_name=self.config.name,
            success=False,
            output=None,
            error=f"任务执行失败，重试{max_retries}次后仍未成功",
            execution_time=0.0
        )


class CodeExpertSubagent(BaseSubagent):
    """代码专家子代理"""
    
    @property
    def config(self) -> SubagentConfig:
        return SubagentConfig(
            name="code_expert",
            role="代码专家",
            capabilities=["代码生成", "代码审查", "代码优化", "调试帮助"],
            max_execution_time=120.0,
            max_retries=2,
            timeout=60.0,
            memory_limit="2GB",
            sandbox_enabled=True
        )
    
    async def execute(self, task: Dict) -> SubagentResult:
        """执行代码相关任务"""
        import time
        start_time = time.time()
        
        # 验证任务
        is_valid, msg = await self.validate_task(task)
        if not is_valid:
            return SubagentResult(
                subagent_name=self.config.name,
                success=False,
                output=None,
                error=f"任务验证失败: {msg}",
                execution_time=time.time() - start_time
            )
        
        description = task["description"]
        language = task.get("language", "python")
        code = task.get("code", "")
        
        try:
            # 根据任务类型执行不同操作
            if "生成" in description or "写" in description:
                output = self._generate_code(description, language)
                result_msg = f"成功生成{language}代码"
                
            elif "审查" in description or "检查" in description:
                output = self._review_code(code, language)
                result_msg = f"成功审查{language}代码"
                
            elif "优化" in description or "改进" in description:
                output = self._optimize_code(code, language)
                result_msg = f"成功优化{language}代码"
                
            elif "调试" in description or "修复" in description:
                output = self._debug_code(code, language)
                result_msg = f"成功调试{language}代码"
                
            else:
                output = f"执行{language}任务: {description}"
                result_msg = "任务执行完成"
            
            execution_time = time.time() - start_time
            
            return SubagentResult(
                subagent_name=self.config.name,
                success=True,
                output=output,
                error=None,
                execution_time=execution_time,
                metadata={
                    "language": language,
                    "task_type": self._detect_task_type(description),
                    "execution_time": execution_time
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return SubagentResult(
                subagent_name=self.config.name,
                success=False,
                output=None,
                error=f"执行过程中发生错误: {str(e)}",
                execution_time=execution_time
            )
    
    def _generate_code(self, description: str, language: str) -> str:
        """生成代码"""
        # 简化实现，实际中会调用代码生成模型
        return f"""
# 自动生成的{language}代码
# 任务描述: {description}

def main():
    print("Hello from generated code!")
    
if __name__ == "__main__":
    main()
"""
    
    def _review_code(self, code: str, language: str) -> str:
        """审查代码"""
        # 简化实现
        issues = []
        
        if "print(" in code and language == "python":
            issues.append("建议使用logging替代print进行日志记录")
        
        if len(code.split('\n')) > 100:
            issues.append("代码过长，建议拆分为多个函数")
        
        if issues:
            return f"代码审查发现{len(issues)}个问题:\\n" + "\\n".join(f"- {issue}" for issue in issues)
        else:
            return "代码审查完成，未发现重大问题"
    
    def _optimize_code(self, code: str, language: str) -> str:
        """优化代码"""
        # 简化实现
        optimized = code.replace("for i in range", "for idx in range")
        optimized = optimized.replace("  ", "    ")  # 统一缩进
        
        return f"""
# 优化后的代码
{optimized}

# 优化说明:
# 1. 变量名更改为更有意义的名称
# 2. 统一了缩进格式
"""
    
    def _debug_code(self, code: str, language: str) -> str:
        """调试代码"""
        # 简化实现
        common_errors = {
            "python": [
                "检查缩进是否正确",
                "确认导入的模块是否存在",
                "检查变量作用域",
                "确认函数参数类型"
            ],
            "javascript": [
                "检查console.log输出",
                "确认异步函数是否正确处理",
                "检查变量声明（let/const/var）",
                "确认回调函数作用域"
            ]
        }
        
        tips = common_errors.get(language, ["检查语法错误", "确认逻辑正确性"])
        
        return f"""
{language}代码调试建议:

{code}

潜在问题:
""" + "\\n".join(f"- {tip}" for tip in tips)
    
    def _detect_task_type(self, description: str) -> str:
        """检测任务类型"""
        if "生成" in description or "写" in description:
            return "generation"
        elif "审查" in description or "检查" in description:
            return "review"
        elif "优化" in description or "改进" in description:
            return "optimization"
        elif "调试" in description or "修复" in description:
            return "debugging"
        else:
            return "general"


# 测试代码
async def test_code_expert():
    """测试代码专家子代理"""
    subagent = CodeExpertSubagent()
    
    # 测试代码生成
    task1 = {
        "description": "生成一个快速排序算法",
        "language": "python"
    }
    
    result1 = await subagent.execute(task1)
    print(f"测试1 - 代码生成:")
    print(f"  成功: {result1.success}")
    print(f"  输出: {result1.output[:100]}...")
    print(f"  耗时: {result1.execution_time:.3f}s")
    
    # 测试代码审查
    task2 = {
        "description": "审查这段Python代码",
        "language": "python",
        "code": "for i in range(10): print(i)"
    }
    
    result2 = await subagent.execute(task2)
    print(f"\\n测试2 - 代码审查:")
    print(f"  成功: {result2.success}")
    print(f"  输出: {result2.output}")
    
    # 测试带重试的执行
    print(f"\\n测试3 - 带重试执行:")
    result3 = await subagent.execute_with_retry(task1, max_retries=1)
    print(f"  最终结果: {result3.success}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_code_expert())
```

### 附录5：课堂练习检查表
```
学生姓名: ___________    日期: ___________

□ 1. 理解了子代理系统的基本概念和架构
□ 2. 成功创建了SubagentConfig数据类
□ 3. 正确实现了BaseSubagent抽象基类
□ 4. 创建了至少一个专用子代理类
□ 5. 实现了子代理的配置属性
□ 6. 实现了子代理的execute方法
□ 7. 添加了任务验证逻辑
□ 8. 编写了子代理的测试代码

教师评语: ____________________________________
评分: ______/100
```

### 附录6：学生反馈表
```
课程名称: SubagentExecutor架构
日期: 2024年4月3日

1. 本节课最难理解的部分是？
   [ ] 抽象基类概念
   [ ] 异步执行模型
   [ ] 数据类设计
   [ ] 其他: ________

2. 练习时间是否充足？
   [ ] 非常充足
   [ ] 基本足够
   [ ] 有点紧张
   [ ] 完全不够

3. 架构讲解是否清晰？
   [ ] 非常清晰
   [ ] 比较清晰
   [ ] 一般
   [ ] 不够清晰

4. 你对子代理系统的理解程度（1-5分）？
   1 [ ] 2 [ ] 3 [ ] 4 [ ] 5 [ ]

5. 有什么建议或问题？
   _________________________________________
   _________________________________________
```

### 附录7：教学观察记录表
```
观察项目              | 观察要点                     | 记录
---------------------|----------------------------|-----------
学生参与度           | 是否积极讨论架构设计         | 
概念理解度           | 能否解释子代理系统原理       | 
代码实现能力         | 能否独立完成子代理实现       | 
设计思维能力         | 能否设计合理的子代理接口     | 
合作学习表现         | 是否愿意分享设计思路         | 
特殊需求             | 需要额外架构指导的学生       | 

总体评价: ____________________________________
跟进建议: ____________________________________
观察教师: ___________    时间: ___________
```

---
**教学提示**: 
1. 抽象基类概念对初学者可能较难，建议先用具体示例引入，再抽象化
2. 异步编程是本节课难点，可先讲解同步版本，再引入异步优势
3. 子代理配置设计要强调可扩展性，为后续课程做铺垫
4. 错误处理是生产系统关键，要引导学生思考各种异常情况

**关联知识**:
- 设计模式：策略模式、模板方法模式
- 软件架构：微服务架构、插件化架构
- Python高级特性：抽象基类、异步编程、数据类
- 系统设计：关注点分离、单一职责原则

**延伸阅读**:
1. Python官方文档：abc模块（抽象基类）
2. DeerFlow子代理系统设计文档
3. 微服务架构设计模式（Martin Fowler）
4. 异步编程最佳实践（Python asyncio）

---
*教案版本: v1.0*
*最后更新: 2024年3月26日*
*教案编写: 张老师（DeerFlow架构师培训团队）*