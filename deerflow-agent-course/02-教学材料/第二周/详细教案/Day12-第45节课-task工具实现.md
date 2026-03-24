# 🎓 详细教案 - Day 12 第45节课：task工具实现

## 📋 课程基本信息
- **课程名称**: task工具实现
- **授课日期**: 2024年4月5日（周五）
- **上课时间**: 上午9:00-9:45（第45节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: Python基础一般，完成了Day 11学习，掌握了子代理配置与注册
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. 理解任务工具在AI Agent系统中的作用和设计目标
2. 掌握task工具的定义、参数设计和返回格式
3. 理解任务工具与子代理执行器的集成方式

### 技能目标（学生将能够）
1. 使用@tool装饰器定义任务工具
2. 实现任务创建和提交到执行器的完整流程
3. 配置任务工具的异步执行和回调机制

### 情感/态度目标
1. 培养学生对工具化设计的理解和应用能力
2. 增强对API设计和用户体验的重视
3. 提高对系统集成和接口设计的重视

## 📚 教学重点与难点
- **教学重点**: task工具的定义、参数设计、与执行器集成
- **教学难点**: 异步执行流程、错误处理、工具发现机制
- **突破方法**: 通过逐步代码演示、流程图展示、错误案例分析

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（16GB+ RAM，支持AVX指令集）
- **软件**: Python 3.12.0、VS Code、Git、LangChain库
- **账户**: GitHub账户（访问DeerFlow代码库）
- **代码**: DeerFlow 2.0代码库（提前克隆到本地）
- **演示材料**: PPT幻灯片第12天第45节、工具架构图
- **学生材料**: 练习手册、工具模板、API设计指南

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员<br>2. 回顾上节课子代理配置与注册要点<br>3. 介绍本节课目标："今天我们学习如何将子代理能力封装成工具" | 1. 登录课堂<br>2. 准备学习材料<br>3. 思考预习问题 | PPT幻灯片第1-3页 |
| 2-5分钟 | 知识激活 | 1. 提问激活已有知识："大家觉得什么时候应该用子代理，什么时候应该用工具？"<br>2. 引导思考工具化设计的价值<br>3. 连接新旧知识："工具是子代理能力的对外接口" | 1. 回答问题："简单任务用工具，复杂任务用子代理？"<br>2. 参与讨论<br>3. 提出疑问 | 白板、互动问答工具 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-10分钟 | 概念讲解 | 1. 讲解任务工具的设计哲学：简化调用、统一接口、异步支持<br>2. 展示task工具架构图：工具装饰器、参数解析、执行器集成<br>3. 举例说明应用场景：代码生成、数据分析、系统操作 | 1. 听讲记录要点<br>2. 观看演示<br>3. 思考理解 | PPT幻灯片第4-8页，架构图 |
| 10-15分钟 | 深入分析 | 1. 分析task工具的核心组件：参数定义、任务创建、执行提交<br>2. 对比工具与直接调用的优劣<br>3. 解释设计决策：为什么需要统一的任务抽象 | 1. 跟随分析<br>2. 记录关键点<br>3. 提出问题 | 代码示例，对比表格 |
| 15-20分钟 | 代码演示 | 1. 演示task_tool基础实现<br>2. 解释@tool装饰器的作用和参数<br>3. 运行展示任务工具执行效果 | 1. 观察代码实现<br>2. 理解运行流程<br>3. 记录代码要点 | VS Code Live Share，终端输出 |

**task工具基础实现：**
```python
from typing import Optional
from langchain.tools import tool
import asyncio

@tool
def task_tool(
    description: str,
    subagent: str = "generic",
    priority: int = 1,
    timeout: float = 300
) -> str:
    """
    将任务委派给子代理执行
    
    Args:
        description: 任务描述，需要清晰明确
        subagent: 子代理类型（generic, bash, python, sql等）
        priority: 任务优先级（1-5，5最高）
        timeout: 超时时间（秒）
    
    Returns:
        任务执行结果
    """
    # 创建任务对象
    task = SubagentTask(
        description=description,
        subagent_type=subagent,
        priority=priority,
        timeout=timeout
    )
    
    # 获取执行器实例
    executor = get_executor()
    
    # 提交任务到执行器（异步）
    try:
        result = await executor.submit(task)
        return result.output
    except asyncio.TimeoutError:
        return f"任务执行超时：{timeout}秒"
    except Exception as e:
        return f"任务执行失败：{str(e)}"

# 工具注册和发现机制
class TaskToolRegistry:
    """任务工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, callable] = {}
    
    def register(self, name: str, tool_func: callable):
        """注册任务工具"""
        self.tools[name] = tool_func
        print(f"✅ 注册工具: {name}")
    
    def get(self, name: str) -> Optional[callable]:
        """获取任务工具"""
        return self.tools.get(name)
    
    def list(self) -> List[str]:
        """列出所有可用工具"""
        return list(self.tools.keys())
    
    def discover_from_subagents(self, registry: SubagentRegistry):
        """从子代理注册表自动发现并创建工具"""
        for name in registry.list():
            subagent = registry.get(name)
            # 为每个子代理创建对应的任务工具
            tool_func = self.create_tool_for_subagent(name, subagent)
            self.register(f"{name}_task", tool_func)
    
    def create_tool_for_subagent(self, name: str, subagent: Subagent) -> callable:
        """为子代理创建任务工具"""
        @tool
        def subagent_task_tool(description: str, priority: int = 1, timeout: float = 300) -> str:
            """子代理专用任务工具"""
            task = SubagentTask(
                description=description,
                subagent_type=name,
                priority=priority,
                timeout=timeout
            )
            return asyncio.run(subagent.execute(task))
        
        return subagent_task_tool
```

### 阶段3：实践练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 指导练习 | 1. 发布练习任务："为Bash子代理创建专用任务工具"<br>2. 提供步骤指导：使用create_tool_for_subagent方法<br>3. 巡视个别指导 | 1. 理解练习要求<br>2. 动手实践<br>3. 寻求帮助 | 练习任务卡，代码模板 |
| 25-30分钟 | 独立实践 | 1. 观察学生进展<br>2. 收集常见问题<br>3. 准备集中讲解 | 1. 独立完成任务<br>2. 调试解决问题<br>3. 记录遇到困难 | 开发环境，在线文档 |
| 30-35分钟 | 成果展示 | 1. 邀请学生分享工具实现<br>2. 点评学生作品<br>3. 总结最佳实践 | 1. 展示完成成果<br>2. 分享学习心得<br>3. 听取反馈建议 | 屏幕共享，代码仓库 |

**练习任务：创建Bash子代理专用工具**
```python
# 学生练习：创建Bash子代理专用任务工具
def create_bash_task_tool(bash_agent: BashSubagent) -> callable:
    """创建Bash子代理专用任务工具"""
    @tool
    def bash_task_tool(
        command: str,  # Bash命令
        workdir: str = "/tmp",  # 工作目录
        timeout: float = 60  # 超时时间
    ) -> str:
        """执行Bash命令工具"""
        task = SubagentTask(
            description=f"执行Bash命令: {command}",
            subagent_type="bash_expert",
            priority=2,
            timeout=timeout,
            params={"command": command, "workdir": workdir}
        )
        return asyncio.run(bash_agent.execute(task))
    
    return bash_task_tool

# 使用示例
# bash_tool = create_bash_task_tool(bash_agent)
# result = bash_tool("ls -la", workdir="/home", timeout=30)
```

### 阶段4：总结与延伸（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 回顾本节课重点：task工具定义、参数设计、工具注册表<br>2. 强调关键概念：工具装饰器、异步执行、自动发现<br>3. 梳理知识结构 | 1. 参与总结<br>2. 完善笔记<br>3. 提问澄清 | 思维导图，总结PPT |
| 38-41分钟 | 拓展延伸 | 1. 介绍工具集成和发现机制<br>2. 展示自动从子代理注册表创建工具的完整流程<br>3. 激发对工具生态系统的兴趣 | 1. 了解前沿技术<br>2. 思考应用场景<br>3. 规划深入学习 | 技术博客，项目案例 |

**工具集成完整流程演示：**
```python
def setup_task_tools() -> Dict[str, callable]:
    """设置完整的任务工具系统"""
    # 1. 初始化注册表
    subagent_registry = SubagentRegistry()
    tool_registry = TaskToolRegistry()
    
    # 2. 注册默认子代理
    subagent_registry.register("generic_expert", GenericSubagent())
    subagent_registry.register("bash_expert", BashSubagent())
    subagent_registry.register("python_expert", PythonSubagent())
    
    # 3. 自动从子代理创建工具
    tool_registry.discover_from_subagents(subagent_registry)
    
    # 4. 添加特殊工具
    tool_registry.register("multi_task", multi_task_tool)
    tool_registry.register("task_status", task_status_tool)
    
    print(f"✅ 工具系统初始化完成，共 {len(tool_registry.list())} 个工具")
    return tool_registry.tools

# 测试
tools = setup_task_tools()
print("可用工具:", tools.keys())
```

| 41-43分钟 | 作业布置 | 1. 说明作业要求：实现任务工具的错误处理和重试机制<br>2. 提供完成建议：使用指数退避重试策略<br>3. 明确提交方式：GitHub仓库 | 1. 记录作业要求<br>2. 理解评价标准<br>3. 规划完成时间 | 作业说明文档 |
| 43-45分钟 | 反馈收集 | 1. 收集课堂反馈<br>2. 解答剩余问题<br>3. 预告下节课内容："下一节学习任务委派决策算法" | 1. 提供学习反馈<br>2. 提出改进建议<br>3. 预习下节内容 | 反馈表，课程日历 |

## 🎭 师生互动设计

### 提问策略
1. **导入提问**: "大家觉得什么时候应该用子代理，什么时候应该用工具？" - 激活已有经验，建立连接
2. **引导提问**: "task工具的参数设计需要考虑哪些因素？" - 引导学生思考API设计
3. **挑战提问**: "如何确保工具调用的安全性和稳定性？" - 激发深度思考
4. **应用提问**: "在实际项目中，如何管理大量的任务工具？" - 联系实际场景，促进知识迁移

### 讨论活动
1. **小组讨论**: 3-4人小组，讨论"任务工具的最佳参数设计实践"
2. **头脑风暴**: 集体创意，"设计支持版本管理的工具系统"
3. **案例分析**: 分析知名AI平台（如LangChain、AutoGPT）的工具设计
4. **代码审查**: 互相review工具实现，提高代码质量

### 反馈机制
1. **即时反馈**: 课堂问答，及时纠正设计误解
2. **过程反馈**: 练习指导，持续改进工具实现
3. **成果反馈**: 作业批改，总结提升错误处理能力
4. **同伴反馈**: 学生互评工具设计，互相学习

## 🔧 差异化教学

### 针对基础薄弱学生
1. **简化任务**: 提供完整的工具框架，只需修改参数和返回值
2. **额外支持**: 一对一辅导，解释装饰器和异步概念
3. **资源推荐**: 提供Python装饰器入门教程
4. **成功体验**: 设计简单的工具创建任务，确保能够完成

### 针对进阶学生
1. **扩展挑战**: 实现工具的动态加载和热更新
2. **创新空间**: 设计支持工具组合和流水线的系统
3. **研究任务**: 对比不同工具框架（LangChain vs LlamaIndex vs Haystack）
4. **领导机会**: 带领小组完成企业级工具管理系统

## 📊 评估方式

### 形成性评估（课堂内）
1. **观察评估**: 观察学生练习过程，记录工具设计理解程度
2. **问答评估**: 通过提问检查工具知识掌握情况
3. **作品评估**: 评估学生完成的任务工具实现质量

### 总结性评估（课后）
1. **作业评估**: 错误处理机制的完整性和健壮性
2. **测验评估**: 下节课前的小测验，考察工具知识
3. **项目评估**: 周项目中工具系统的实现质量

## 🚨 应急预案

### 技术问题
1. **装饰器语法错误**: 提供简化版本，避免复杂装饰器用法
2. **异步编程困难**: 提供同步版本简化实现
3. **工具注册失败**: 准备备用的手动注册方案

### 学习困难
1. **不理解装饰器**: 使用函数包装的简单示例逐步引入
2. **异步概念困惑**: 先实现同步版本，再添加异步支持
3. **工具发现机制复杂**: 分步骤讲解，每步单独测试

### 时间控制
1. **讲解超时**: 压缩理论讲解，保证实践时间
2. **练习超时**: 提供部分完成代码，让学生补充关键部分
3. **总结仓促**: 提前准备总结要点卡片，快速回顾

## 💭 教学反思（课后填写）
- **学生掌握情况**: 
- **教学效果评估**: 
- **改进建议**: 
- **成功经验**: 

## 📝 课后任务

### 必做作业
1. **错误处理增强**: 为task_tool添加完整的错误处理和重试机制
2. **工具发现优化**: 改进工具自动发现机制，支持基于配置的过滤
3. **性能监控**: 为工具添加执行时间监控和性能统计

### 选做挑战
1. **工具组合**: 实现多个工具的组合调用和结果合并
2. **工具版本管理**: 设计支持多版本工具并存的系统
3. **工具市场**: 设计支持第三方工具上传和分享的平台

### 预习任务
1. **预习下一节**: 阅读任务委派决策算法相关代码
2. **思考问题**: "如何智能选择最适合的子代理执行任务？"
3. **准备问题**: 记录预习中遇到的问题，下节课提问

## 📎 附录

### 附录1：PPT幻灯片要点
1. **幻灯片1**: 课程标题、教师介绍、学习目标
2. **幻灯片2**: 任务工具设计哲学
3. **幻灯片3**: task工具架构图
4. **幻灯片4**: @tool装饰器详解
5. **幻灯片5**: 工具注册表设计
6. **幻灯片6**: 自动工具发现机制
7. **幻灯片7**: 总结与作业布置

### 附录2：task工具参数设计参考表
| 参数名 | 类型 | 必填 | 默认值 | 描述 | 验证规则 |
|--------|------|------|--------|------|----------|
| description | string | 是 | 无 | 任务描述 | 非空，长度1-1000字符 |
| subagent | string | 否 | "generic" | 子代理类型 | 必须在可用子代理列表中 |
| priority | int | 否 | 1 | 任务优先级 | 1-5，1最低，5最高 |
| timeout | float | 否 | 300 | 超时时间（秒） | 1-3600秒 |
| callback_url | string | 否 | 无 | 回调URL | 有效的URL格式 |
| metadata | dict | 否 | {} | 元数据 | JSON可序列化 |

### 附录3：任务工具设计检查清单
- [ ] 使用@tool装饰器正确装饰函数
- [ ] 提供完整的docstring文档
- [ ] 参数设计合理，有默认值
- [ ] 包含必要的参数验证
- [ ] 错误处理机制完善
- [ ] 支持异步执行
- [ ] 返回格式统一
- [ ] 性能监控和日志记录

### 附录4：常见错误及解决方法
| 错误现象 | 可能原因 | 解决方法 |
|----------|----------|----------|
| 装饰器不生效 | 函数签名不正确 | 检查@tool装饰器位置和参数 |
| 异步调用错误 | 未正确使用await | 确保在异步上下文中调用 |
| 工具注册失败 | 名称冲突 | 检查工具名称唯一性 |
| 执行超时 | 任务复杂度过高 | 调整timeout参数或优化任务 |
| 内存泄漏 | 未正确清理资源 | 使用上下文管理器确保资源释放 |

### 附录5：课堂观察记录表
| 学生姓名 | 参与讨论 | 练习完成 | 问题提出 | 掌握程度 | 备注 |
|----------|----------|----------|----------|----------|------|
| 小王 | ✓ | ✓ | ✓ | 良好 | 对工具设计感兴趣 |
| 小李 | ✓ | ✓ |  | 中等 | 异步概念需要加强 |
| 小张 | ✓ | ✓ | ✓ | 优秀 | 完成工具组合挑战 |

### 附录6：教学资源链接
1. **LangChain工具文档**: `https://python.langchain.com/docs/modules/agents/tools/`
2. **Python装饰器指南**: `https://realpython.com/primer-on-python-decorators/`
3. **异步编程教程**: `https://docs.python.org/3/library/asyncio.html`
4. **API设计最佳实践**: `https://github.com/microsoft/api-guidelines`

---

**教学提示**: 本节课的关键是帮助学生理解工具化设计的思想和实现方法。通过实际工具创建和集成演示，让学生掌握将子代理能力封装成易用工具的技能。注意观察学生对装饰器和异步编程的理解，及时提供辅助材料。

**张老师寄语**: "好的工具让复杂能力变得简单易用。今天你学会了如何将子代理封装成任务工具，这是构建用户友好AI Agent系统的重要一步！"