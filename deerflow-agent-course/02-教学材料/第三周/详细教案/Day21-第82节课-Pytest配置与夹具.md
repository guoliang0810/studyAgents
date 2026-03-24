# 🎓 详细教案 - Day 21 第82节课：Pytest配置与夹具

## 📋 课程基本信息
- **课程名称**: Pytest配置与夹具系统
- **授课日期**: 2024年4月14日（周日）
- **上课时间**: 上午10:00-10:45（第82节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: Python基础一般，完成了Day 21第81节课学习，掌握了测试策略规划
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. **理解Pytest夹具系统的工作原理**，包括fixture定义、作用域、依赖注入
2. **掌握DeerFlow自定义夹具的设计模式**，包括配置夹具、应用实例夹具、服务夹具
3. **了解Pytest插件配置机制**，包括自定义标记、测试过滤、运行时配置

### 技能目标（学生将能够）
1. **设计可重用的测试夹具**，支持不同测试场景的需求
2. **配置复杂的Pytest测试环境**，包括异步支持、服务依赖、环境隔离
3. **实现测试标记和过滤系统**，优化测试执行效率和选择性

### 情感/态度目标
1. **培养模块化测试思维**，理解夹具系统对测试代码质量的重要性
2. **建立工程化测试意识**，认识到良好的测试配置是团队协作的基础
3. **增强自动化测试信心**，通过掌握高级Pytest特性提升测试开发能力

## 📚 教学重点与难点
- **教学重点**: 
  1. Pytest夹具系统的核心概念和作用域管理
  2. DeerFlow常用夹具的实现原理和使用方法
  3. Pytest插件配置和自定义标记机制
  
- **教学难点**: 
  1. 异步夹具的设计和时序控制
  2. 夹具依赖关系的复杂管理
  3. 测试标记的动态过滤和条件执行
  
- **突破方法**: 
  1. 使用依赖关系图可视化夹具结构
  2. 通过分层示例展示异步夹具实现
  3. 采用实际项目案例演示标记过滤

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（16GB+ RAM，支持AVX指令集）
- **软件**: Python 3.12.0、pytest 7.4.0、pytest-asyncio 0.21.0、VS Code、Git
- **账户**: GitHub账户、Docker Hub账户
- **代码**: DeerFlow 2.0代码库，重点关注`tests/conftest.py`和`tests/fixtures/`目录
- **演示材料**: PPT幻灯片（夹具依赖图、标记系统图、配置示例）
- **学生材料**: 练习手册、夹具模板、标记配置示例
- **在线工具**: 代码共享平台、Pytest文档、DeerFlow测试示例库

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员，检查设备状态<br>2. 回顾第81节课测试金字塔<br>3. 介绍本节课Pytest配置主题 | 1. 登录课堂，打开开发环境<br>2. 回忆测试策略规划<br>3. 了解今日学习目标 | PPT幻灯片第1-3页：课程标题、复习要点、学习目标 |
| 2-5分钟 | 知识激活 | 1. 提问："大家使用过Pytest的哪些高级功能？"<br>2. 引导思考："为什么测试夹具对AI Agent系统特别重要？"<br>3. 连接已有知识："夹具如何支持测试金字塔的实现？" | 1. 回答问题，分享经验<br>2. 参与讨论，提出观点<br>3. 建立知识连接 | 白板记录学生回答，互动问答工具收集经验 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-10分钟 | 概念讲解 | 1. 讲解Pytest夹具系统：fixture装饰器、作用域、yield模式<br>2. 展示夹具依赖关系图<br>3. 举例说明DeerFlow常用夹具类型 | 1. 听讲记录要点<br>2. 观看夹具结构图<br>3. 思考AI Agent测试需求 | PPT幻灯片第4-8页：夹具系统架构图、作用域对比表、DeerFlow夹具分类 |
| 10-15分钟 | 深入分析 | 1. 分析异步夹具设计模式：async with模式、事件循环管理<br>2. 对比不同夹具作用域的适用场景<br>3. 解释夹具依赖注入机制 | 1. 跟随代码分析<br>2. 记录设计模式<br>3. 理解异步挑战 | 代码编辑器展示异步夹具示例，对比表格说明作用域差异 |
| 15-20分钟 | 代码演示 | 1. 演示DeerFlow核心夹具：deerflow_app、mcp_client、test_database<br>2. 解释夹具初始化和清理流程<br>3. 运行展示夹具生命周期 | 1. 观察代码实现<br>2. 理解夹具生命周期<br>3. 记录最佳实践 | VS Code Live Share，终端展示夹具启动和清理输出 |

### 阶段3：实践练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 指导练习 | 1. 发布练习任务：设计内存系统测试夹具<br>2. 提供步骤指导：分析依赖关系，设计作用域，实现清理逻辑<br>3. 巡视个别指导：检查夹具设计合理性 | 1. 理解练习要求<br>2. 分析内存系统依赖<br>3. 设计夹具结构 | 练习任务卡，夹具设计模板，依赖分析工作表 |
| 25-30分钟 | 独立实践 | 1. 观察学生进展，收集常见问题<br>2. 提供调试建议，解决异步问题<br>3. 准备集中讲解材料 | 1. 独立完成夹具实现<br>2. 调试遇到的问题<br>3. 记录实践心得 | 开发环境，Pytest调试指南，异步编程参考资料 |
| 30-35分钟 | 成果展示 | 1. 邀请2名学生分享夹具设计<br>2. 点评设计优缺点<br>3. 总结夹具设计最佳实践 | 1. 展示设计成果<br>2. 分享设计思路<br>3. 听取反馈建议 | 屏幕共享展示夹具代码，白板记录设计原则 |

### 阶段4：总结与延伸（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 回顾Pytest夹具核心概念<br>2. 强调异步夹具设计要点<br>3. 梳理夹具依赖管理原则 | 1. 参与总结<br>2. 完善笔记<br>3. 提问澄清疑惑 | 思维导图总结夹具系统，PPT回顾关键设计模式 |
| 38-41分钟 | 拓展延伸 | 1. 介绍企业级夹具管理方案<br>2. 展示夹具复用和组合模式<br>3. 对比不同测试框架的夹具系统 | 1. 了解行业实践<br>2. 思考架构设计<br>3. 规划深入学习 | 技术博客文章，企业项目案例，框架对比分析 |
| 41-43分钟 | 作业布置 | 1. 说明作业要求：实现配置管理测试夹具套件<br>2. 提供完成建议：参考DeerFlow fixtures模块<br>3. 明确提交方式：GitHub仓库PR | 1. 记录作业要求<br>2. 理解评价标准<br>3. 规划完成时间 | 作业说明文档，代码模板，提交指南 |
| 43-45分钟 | 反馈收集 | 1. 收集课堂反馈：理解程度、教学节奏<br>2. 解答剩余问题<br>3. 预告下节课：Mock策略 | 1. 提供学习反馈<br>2. 提出改进建议<br>3. 预习下节内容 | 反馈表收集工具，课程日历展示进度 |

## 🎭 师生互动设计

### 提问策略
1. **导入提问**: "小王，你之前写测试时遇到过哪些夹具问题？"（激活已有经验）
2. **引导提问**: "为什么AI Agent测试需要特殊的异步夹具？"（引导思考特殊性）
3. **挑战提问**: "如果多个测试夹具有循环依赖怎么办？"（激发问题解决思维）
4. **应用提问**: "在你的项目中，如何设计可复用的测试夹具？"（促进知识迁移）

### 讨论活动
1. **小组讨论**: 3-4人小组，讨论夹具作用域选择策略（10分钟）
2. **头脑风暴**: 集体创意，设计夹具依赖解析算法（5分钟）
3. **案例分析**: 分析实际项目夹具设计失败案例，学习教训（8分钟）
4. **代码审查**: 互相review夹具实现，提高代码质量（7分钟）

### 反馈机制
1. **即时反馈**: 课堂问答，及时纠正理解偏差
2. **过程反馈**: 练习指导，持续改进夹具设计
3. **成果反馈**: 作业批改，总结提升测试架构能力
4. **同伴反馈**: 学生互评夹具设计，互相学习最佳实践

## 🔧 差异化教学

### 针对基础薄弱学生
1. **简化任务**: 提供预实现的夹具模板，只需填充核心逻辑
2. **额外支持**: 一对一辅导夹具作用域理解，延长练习时间
3. **资源推荐**: 提供Python装饰器和yield关键字教程链接
4. **成功体验**: 设计可达成的子目标：成功运行一个简单夹具

### 针对进阶学生
1. **扩展挑战**: 设计支持并行测试的夹具隔离机制
2. **创新空间**: 探索夹具自动发现和注册机制
3. **领导机会**: 担任小组长，帮助其他同学理解复杂依赖
4. **项目实战**: 为真实DeerFlow模块设计完整夹具套件

### 针对中等水平学生
1. **渐进提升**: 从简单夹具到复杂依赖逐步增加难度
2. **榜样学习**: 学习优秀同学的夹具设计文档和代码
3. **目标引导**: 设定明确的夹具复用率和覆盖率目标
4. **反馈激励**: 及时肯定夹具设计的进步和创新

## 📊 评估方式

### 形成性评估（课堂内）
1. **观察评估**: 观察学生参与讨论的积极性和思考深度
2. **提问评估**: 通过提问检验夹具系统理解程度
3. **练习评估**: 检查夹具设计的合理性和完整性
4. **自评互评**: 学生自我评估设计质量，互相评价方案优劣

### 总结性评估（课堂后）
1. **作业评估**: 批改夹具套件实现作业，评分反馈
2. **测验评估**: 单元测验检验Pytest配置知识点掌握
3. **项目评估**: 在周项目中评估夹具设计质量和使用效果
4. **综合评估**: 结合课堂表现、作业质量、项目贡献综合评价

### 评估标准
- **优秀（90-100分）**: 全面掌握夹具系统原理，能设计复杂系统的完整夹具架构
- **良好（80-89分）**: 基本掌握夹具概念，能实现合理的测试夹具
- **合格（60-79分）**: 理解核心概念，需要指导完成夹具设计
- **需改进（<60分）**: 需要重新学习Pytest基础和夹具概念

## 🚨 应急预案

### 技术故障
1. **网络中断**: 准备离线演示材料，录制视频备用，提供本地文档
2. **软件故障**: 准备备用开发环境（GitHub Codespaces），使用在线IDE
3. **电力中断**: 提前通知学员调整时间，提供录播课程链接
4. **平台故障**: 准备备用教学平台（Zoom、腾讯会议、Discord）

### 学生问题
1. **理解困难**: 放慢节奏，增加夹具可视化示例，一对一辅导
2. **设备问题**: 提供远程协助，共享屏幕指导配置，提供云开发环境
3. **时间不足**: 调整内容优先级，先掌握核心概念，提供课后补充材料
4. **兴趣不足**: 增加实际案例，联系大厂面试问题，展示夹具重要性

### 内容调整
1. **进度过快**: 增加练习时间，补充Pytest基础概念讲解
2. **进度过慢**: 精简扩展内容，聚焦夹具核心概念和设计模式
3. **内容过难**: 分解复杂概念，提供阶梯式学习材料和代码模板
4. **内容过易**: 增加深度挑战，探索分布式测试夹具设计

## 📝 教学反思

### 成功之处
1. **可视化教学**: 夹具依赖关系图有效帮助学生理解复杂结构
2. **实践导向**: 从简单到复杂的渐进式练习设计合理
3. **互动充分**: 夹具设计讨论环节学生参与度高
4. **案例丰富**: 结合DeerFlow实际代码增强学习实用性

### 改进之处
1. **时间分配**: 异步夹具讲解可更紧凑，留更多练习时间
2. **难度梯度**: 夹具依赖管理需要更多铺垫和示例
3. **资源准备**: 提前准备更多可运行的夹具代码示例
4. **差异化**: 需要更精细的进阶挑战任务设计

### 学生表现
- **优秀表现**: 部分学生能设计复杂的异步夹具依赖体系
- **常见问题**: 夹具作用域理解有困难，yield模式使用不当
- **学习障碍**: Python装饰器和生成器基础薄弱影响夹具学习

### 调整建议
1. **内容调整**: 增加装饰器和yield关键字预备知识回顾环节
2. **方法改进**: 采用更多类比（如餐厅准备食材）解释夹具系统
3. **资源优化**: 制作夹具生成器工具降低入门门槛
4. **评估细化**: 增加阶段性检查点，及时发现理解偏差

## 🎯 课后任务

### 必做任务
1. **夹具设计**: 为DeerFlow内存系统设计完整的测试夹具套件
2. **配置实现**: 实现支持异步测试的conftest.py配置
3. **文档撰写**: 撰写夹具使用文档，说明依赖关系和生命周期
4. **测试运行**: 使用夹具运行内存系统的单元测试和集成测试

### 选做任务（挑战）
1. **高级挑战**: 设计支持夹具版本管理和迁移的工具
2. **创新探索**: 实现夹具性能监控和优化建议系统
3. **性能优化**: 优化夹具启动时间，支持并行初始化
4. **工具开发**: 开发夹具可视化依赖分析工具

### 预习任务
1. **阅读材料**: 预习第83节课学生讲义，了解Mock测试策略
2. **环境准备**: 安装pytest-mock插件，准备Mock测试环境
3. **代码查看**: 查看DeerFlow tests/mocks/目录，理解Mock实现
4. **问题思考**: 思考如何为AI模型设计有效的Mock策略

### 资源推荐
1. **阅读材料**: 
   - 《Pytest权威指南》第7章：高级夹具模式
   - Python官方文档：unittest.mock模块详解
   - DeerFlow官方文档：测试夹具系统设计
2. **视频教程**:
   - "Advanced Pytest Fixtures" (PyCon 2023)
   - "Mocking in Python" (Real Python)
   - "Testing Async Systems" (DeerFlow官方频道)
3. **实践项目**:
   - GitHub: deer-flow/fixtures-examples
   - GitLab: pytest-advanced-fixtures
   - CodeSandbox: deerflow-fixtures-playground
4. **社区讨论**:
   - Discord: #testing-fixtures频道
   - 知乎专栏: Pytest高级技巧
   - 掘金小册: 测试夹具设计模式

---

## 📋 附录

### 附录A：PPT幻灯片要点
1. **封面页**: Pytest配置与夹具 - 第82节课 - 张老师 - 2024.04.14
2. **目标页**: 知识目标×3、技能目标×3、情感目标×3
3. **导入页**: 第81节课复习、夹具重要性、今日学习路线
4. **概念页**: Pytest夹具系统架构图、作用域对比表、依赖注入机制
5. **示例页**: DeerFlow核心夹具代码示例、异步夹具设计模式
6. **练习页**: 内存系统夹具设计任务、依赖分析工作表、实现检查清单
7. **总结页**: 关键概念回顾、最佳实践总结、常见问题解答
8. **作业页**: 必做任务×4、选做挑战×4、预习要求×4
9. **资源页**: 推荐阅读×3、视频教程×3、实践项目×3、社区讨论×3

### 附录B：学生练习任务卡
```markdown
# 课堂练习：设计内存系统测试夹具

## 任务描述
为DeerFlow内存系统设计完整的测试夹具套件，内存系统包含以下组件：
1. 短期记忆存储（ShortTermMemory）
2. 长期记忆存储（LongTermMemory）
3. 记忆检索引擎（MemoryRetriever）
4. 记忆压缩器（MemoryCompressor）
5. 记忆持久化器（MemoryPersister）

请设计一组Pytest夹具，支持单元测试和集成测试需求。

## 要求
- [ ] 为每个组件设计独立的夹具
- [ ] 支持不同的测试作用域（function, class, module, session）
- [ ] 实现正确的初始化和清理逻辑
- [ ] 支持异步测试模式
- [ ] 提供配置参数化支持

## 步骤指导
1. **分析组件依赖**（5分钟）：
   - 绘制组件依赖关系图
   - 识别测试所需的模拟数据
   - 确定夹具作用域需求

2. **设计夹具结构**（8分钟）：
   - 设计基础夹具：memory_system_config
   - 设计组件夹具：short_term_memory, long_term_memory
   - 设计集成夹具：complete_memory_system
   - 设计数据夹具：sample_memories, test_conversations

3. **实现夹具代码**（10分钟）：
   - 使用@pytest.fixture装饰器
   - 实现异步夹具：async def + yield
   - 添加参数化支持：@pytest.fixture(params=...)
   - 实现清理逻辑：yield后的清理代码

4. **验证与测试**（5分钟）：
   - 编写简单的测试用例验证夹具
   - 测试不同作用域的行为
   - 验证异步支持的正确性

## 提示与技巧
- **技巧1**: 使用yield模式确保资源正确清理，即使测试失败
- **技巧2**: 为耗时初始化使用session作用域，避免重复初始化
- **技巧3**: 使用夹具工厂模式创建参数化的测试实例
- **技巧4**: 利用conftest.py共享夹具，支持跨测试模块复用

## 检查点
- [ ] 每个组件都有对应的测试夹具
- [ ] 夹具作用域选择合理
- [ ] 异步支持正确实现
- [ ] 清理逻辑完整可靠
- [ ] 参数化配置灵活可用

## 扩展挑战（可选）
- **挑战1**: 设计支持并行测试的夹具隔离机制
- **挑战2**: 实现夹具性能监控和优化建议
- **挑战3**: 设计夹具依赖自动解析和冲突检测
- **挑战4**: 开发夹具可视化依赖分析工具
```

### 附录C：课堂观察记录表
| 观察项目 | 观察要点 | 记录 |
|----------|----------|------|
| 学生参与度 | 积极发言、提问、讨论参与程度 | |
| 理解程度 | 夹具概念掌握、作用域理解准确性 | |
| 合作交流 | 小组协作效果、知识分享意愿 | |
| 问题解决 | 遇到夹具设计问题时的调试策略 | |
| 学习兴趣 | 对Pytest高级特性的兴趣表现 | |
| 实践能力 | 练习任务完成速度和质量 | |
| 创新思维 | 在夹具设计中展现的创新点 | |
| 反馈响应 | 对教师反馈的接受和改进 | |

### 附录D：学生反馈表
```markdown
# 课堂反馈 - 第82节课：Pytest配置与夹具

## 学习收获
本节课我学到了：
1. 
2. 
3. 

## 理解程度（1-5分，5分为完全理解）
- Pytest夹具系统: □1 □2 □3 □4 □5
- 异步夹具设计: □1 □2 □3 □4 □5  
- 夹具作用域管理: □1 □2 □3 □4 □5

## 课堂体验
- 哪些部分最有帮助？
- 哪些部分需要改进？
- 对教师的建议：

## 学习困难
- 遇到的主要困难：
- 需要的帮助：
- 学习建议：

## 自我评估
- 练习任务完成度：□完全完成 □大部分完成 □部分完成 □基本未完成
- 自信程度：□非常自信 □比较自信 □一般 □不太自信
- 后续学习意愿：□非常强烈 □比较强烈 □一般 □不太愿意
```

### 附录E：DeerFlow核心夹具代码示例
```python
"""
DeerFlow核心测试夹具 - 完整实现示例
来自学生讲义第82节内容
"""
import pytest
from deerflow.testing.fixtures import *


@pytest.fixture
def sample_config():
    """提供示例配置"""
    return {
        "models": {
            "test_model": {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "config": {"temperature": 0.7},
            }
        },
        "tools": {
            "test_tool": {
                "enabled": True,
                "type": "builtin",
            }
        },
    }


@pytest.fixture
async def deerflow_app(sample_config):
    """创建DeerFlow应用实例"""
    from deerflow.app import DeerFlowApp
    
    app = DeerFlowApp(sample_config)
    await app.initialize()
    
    yield app
    
    await app.cleanup()


@pytest.fixture
async def mcp_client():
    """创建MCP客户端"""
    from deerflow.mcp.client import MCPClient
    
    client = MCPClient({"transport": "stdio"})
    await client.connect()
    
    yield client
    
    await client.disconnect()


@pytest.fixture(scope="session")
def test_database():
    """创建测试数据库"""
    from deerflow.testing.database import TestDatabase
    
    db = TestDatabase()
    db.create()
    
    yield db
    
    db.drop()


@pytest.fixture(autouse=True)
def setup_test_logging():
    """自动设置测试日志"""
    import logging
    
    # 配置测试日志
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 降低第三方库的日志级别
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# conftest.py配置示例
def pytest_configure(config):
    """配置Pytest"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "requires_gpu: test requires GPU"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    skip_slow = config.getoption("--skip-slow")
    skip_integration = config.getoption("--skip-integration")
    
    for item in items:
        # 跳过标记为slow的测试
        if "slow" in item.keywords and skip_slow:
            item.add_marker(pytest.mark.skip(reason="Skipping slow tests"))
        
        # 跳过集成测试
        if "integration" in item.keywords and skip_integration:
            item.add_marker(pytest.mark.skip(reason="Skipping integration tests"))
        
        # 跳过需要GPU的测试（如果没有GPU）
        if "requires_gpu" in item.keywords and not has_gpu():
            item.add_marker(pytest.mark.skip(reason="GPU not available"))


# 使用示例
async def test_deerflow_app(deerflow_app):
    """测试DeerFlow应用"""
    # 使用deerflow_app夹具
    response = await deerflow_app.process("Hello, world!")
    
    assert response is not None
    assert len(response) > 0


async def test_mcp_integration(deerflow_app, mcp_client):
    """测试MCP集成"""
    # 使用多个夹具
    await mcp_client.connect()
    
    # 测试MCP工具调用
    tools = await mcp_client.list_tools()
    assert len(tools) > 0
    
    # 清理由夹具自动处理
```

### 附录F：异步夹具设计模式
```python
"""
异步夹具设计模式 - 高级示例
"""
import asyncio
import pytest
from contextlib import asynccontextmanager


# 模式1：基本的异步夹具
@pytest.fixture
async def async_resource():
    """基本的异步夹具"""
    resource = await create_async_resource()
    
    yield resource
    
    await resource.cleanup()


# 模式2：带参数化的异步夹具
@pytest.fixture(params=[1, 10, 100])
async def parametrized_async_resource(request):
    """带参数化的异步夹具"""
    resource = await create_resource_with_size(request.param)
    
    yield resource
    
    await resource.cleanup()


# 模式3：异步上下文管理器夹具
@asynccontextmanager
async def async_resource_context(config):
    """异步上下文管理器"""
    resource = await create_async_resource(config)
    
    try:
        yield resource
    finally:
        await resource.cleanup()


@pytest.fixture
async def context_manager_resource():
    """使用异步上下文管理器的夹具"""
    async with async_resource_context({"mode": "test"}) as resource:
        yield resource


# 模式4：夹具依赖链
@pytest.fixture
async def database_connection():
    """数据库连接夹具"""
    connection = await connect_to_database()
    
    yield connection
    
    await connection.close()


@pytest.fixture
async def user_repository(database_connection):
    """用户仓库夹具，依赖数据库连接"""
    repository = UserRepository(database_connection)
    
    yield repository
    
    await repository.cleanup()


@pytest.fixture
async def authenticated_user(user_repository):
    """认证用户夹具，依赖用户仓库"""
    user = await user_repository.create_user({
        "username": "testuser",
        "password": "testpass"
    })
    
    yield user
    
    await user_repository.delete_user(user.id)


# 模式5：会话作用域的异步夹具
@pytest.fixture(scope="session")
async def shared_async_resource():
    """会话作用域的共享异步资源"""
    resource = await create_expensive_resource()
    
    yield resource
    
    await resource.cleanup()


# 使用示例
async def test_async_system(authenticated_user, shared_async_resource):
    """测试异步系统"""
    # 使用多个异步夹具
    result = await shared_async_resource.process(authenticated_user)
    
    assert result.success
    assert result.user_id == authenticated_user.id
```

---

**教案编制**: 张老师  
**编制日期**: 2024年3月24日  
**版本**: v1.0  
**适用对象**: DeerFlow Python Agent架构师训练营学员  

**教学备注**: 
- 本教案基于DeerFlow学生讲义Day 21第82节内容编写
- 整合了实际DeerFlow测试夹具实现代码
- 设计符合45分钟课堂实际教学需求
- 包含完整的教学资源和支持材料
1. **课程互动实录参考**:
   - 讲师引导："今天我们来学习如何为Agent系统设计测试夹具。"
   - 学生提问："异步夹具和普通夹具有什么区别？"
   - 讲师解答："异步夹具需要处理事件循环，支持async/await语法，对AI Agent测试特别重要。"

2. **大厂面试准备要点**:
   - 字节跳动：重视Pytest高级特性掌握和夹具设计能力
   - 阿里巴巴：关注测试代码的可维护性和复用性
   - 腾讯：强调异步测试和并发场景处理
   - 华为：重视测试环境管理和资源清理

3. **实际项目应用**:
   - 夹具设计直接影响测试代码的可维护性
   - 合理的夹具作用域选择能显著提升测试性能
   - 异步夹具是AI Agent测试的必备技能
   - 夹具复用能减少测试代码重复，提高团队效率