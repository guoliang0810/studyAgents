# 🎓 详细教案 - Day 21 第83节课：Mock策略

## 📋 课程基本信息
- **课程名称**: Mock测试策略与模拟技术
- **授课日期**: 2024年4月14日（周日）
- **上课时间**: 上午11:00-11:45（第83节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: Python基础一般，完成了Day 21第82节课学习，掌握了Pytest夹具系统
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. **理解Mock测试的核心概念**，包括模拟、存根、假对象、测试替身等模式
2. **掌握AI模型Mock的设计原则**，包括响应模拟、调用历史记录、断言验证
3. **了解外部服务Mock的实现机制**，包括HTTP API、数据库、文件系统、MCP服务的模拟

### 技能目标（学生将能够）
1. **设计智能的AI模型Mock**，支持复杂对话场景和动态响应
2. **实现完整的外部服务Mock系统**，隔离测试依赖，提高测试稳定性
3. **使用pytest-mock等工具进行高级Mock测试**，验证系统行为符合预期

### 情感/态度目标
1. **培养隔离测试思维**，理解Mock对测试稳定性和可重复性的重要性
2. **建立依赖管理意识**，认识到外部服务模拟是生产级测试的必备技能
3. **增强测试设计信心**，通过掌握Mock策略提升复杂系统的测试能力

## 📚 教学重点与难点
- **教学重点**: 
  1. AI模型Mock的设计模式和实现技巧
  2. 外部服务Mock的架构和接口模拟
  3. pytest-mock工具的高级用法和最佳实践
  
- **教学难点**: 
  1. 动态响应的AI Mock设计（基于输入内容返回不同响应）
  2. 异步服务的Mock实现和时序控制
  3. Mock状态验证和行为断言的设计
  
- **突破方法**: 
  1. 使用模式匹配实现智能响应
  2. 通过状态机设计复杂Mock行为
  3. 采用录制-回放模式验证Mock调用

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（16GB+ RAM，支持AVX指令集）
- **软件**: Python 3.12.0、pytest 7.4.0、pytest-mock 3.11.1、unittest.mock、VS Code、Git
- **账户**: GitHub账户、OpenAI API密钥（用于对比真实响应）
- **代码**: DeerFlow 2.0代码库，重点关注`tests/mocks/`目录和`tests/test_mocking.py`
- **演示材料**: PPT幻灯片（Mock分类图、AI Mock架构图、服务Mock示意图）
- **学生材料**: 练习手册、Mock模板、响应模式示例
- **在线工具**: 代码共享平台、Mock模式库、API模拟工具

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员，检查设备状态<br>2. 回顾第82节课夹具系统<br>3. 介绍本节课Mock策略主题 | 1. 登录课堂，打开开发环境<br>2. 回忆夹具设计要点<br>3. 了解今日学习目标 | PPT幻灯片第1-3页：课程标题、复习要点、学习目标 |
| 2-5分钟 | 知识激活 | 1. 提问："大家测试时遇到过哪些外部依赖问题？"<br>2. 引导思考："为什么AI Agent测试特别需要Mock？"<br>3. 连接已有知识："Mock和夹具有什么关系？" | 1. 回答问题，分享经验<br>2. 参与讨论，提出观点<br>3. 建立知识连接 | 白板记录学生问题，互动问答工具收集痛点 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-10分钟 | 概念讲解 | 1. 讲解Mock测试核心概念：模拟、存根、假对象、间谍<br>2. 展示AI模型Mock的特殊性：动态响应、上下文感知<br>3. 举例说明外部服务Mock的类型：HTTP、DB、FS、MCP | 1. 听讲记录要点<br>2. 观看Mock分类图<br>3. 思考AI测试需求 | PPT幻灯片第4-8页：Mock分类图、AI Mock特殊性、服务Mock类型 |
| 10-15分钟 | 深入分析 | 1. 分析MockChatModel类设计：响应映射、调用历史、断言方法<br>2. 对比不同Mock模式的适用场景<br>3. 解释pytest-mock的patch机制和mock对象创建 | 1. 跟随代码分析<br>2. 记录设计模式<br>3. 理解Mock生命周期 | 代码编辑器展示MockChatModel实现，对比表格说明Mock模式差异 |
| 15-20分钟 | 代码演示 | 1. 演示MockMCPServer完整实现<br>2. 解释MCP请求处理和工具模拟<br>3. 运行展示Mock服务的行为验证 | 1. 观察代码实现<br>2. 理解服务Mock架构<br>3. 记录最佳实践 | VS Code Live Share，终端展示Mock服务请求处理过程 |

### 阶段3：实践练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 指导练习 | 1. 发布练习任务：设计智能天气API Mock<br>2. 提供步骤指导：分析API接口，设计响应模式，实现验证逻辑<br>3. 巡视个别指导：检查Mock设计合理性 | 1. 理解练习要求<br>2. 分析天气API规范<br>3. 设计Mock响应逻辑 | 练习任务卡，API接口文档模板，Mock设计工作表 |
| 25-30分钟 | 独立实践 | 1. 观察学生进展，收集常见问题<br>2. 提供调试建议，解决动态响应问题<br>3. 准备集中讲解材料 | 1. 独立完成Mock实现<br>2. 调试遇到的问题<br>3. 记录实践心得 | 开发环境，Mock调试指南，动态响应参考资料 |
| 30-35分钟 | 成果展示 | 1. 邀请2名学生分享Mock设计<br>2. 点评设计优缺点<br>3. 总结Mock设计最佳实践 | 1. 展示设计成果<br>2. 分享设计思路<br>3. 听取反馈建议 | 屏幕共享展示Mock代码，白板记录设计原则 |

### 阶段4：总结与延伸（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 回顾Mock测试核心概念<br>2. 强调AI模型Mock设计要点<br>3. 梳理服务Mock实现原则 | 1. 参与总结<br>2. 完善笔记<br>3. 提问澄清疑惑 | 思维导图总结Mock策略，PPT回顾关键设计模式 |
| 38-41分钟 | 拓展延伸 | 1. 介绍企业级Mock服务架构<br>2. 展示Mock录制和回放工具<br>3. 对比不同Mock框架的优缺点 | 1. 了解行业实践<br>2. 思考架构设计<br>3. 规划深入学习 | 技术博客文章，企业项目案例，框架对比分析 |
| 41-43分钟 | 作业布置 | 1. 说明作业要求：实现OpenAI API完整Mock系统<br>2. 提供完成建议：参考真实API文档<br>3. 明确提交方式：GitHub仓库PR | 1. 记录作业要求<br>2. 理解评价标准<br>3. 规划完成时间 | 作业说明文档，API文档模板，提交指南 |
| 43-45分钟 | 反馈收集 | 1. 收集课堂反馈：理解程度、教学节奏<br>2. 解答剩余问题<br>3. 预告下节课：边界测试 | 1. 提供学习反馈<br>2. 提出改进建议<br>3. 预习下节内容 | 反馈表收集工具，课程日历展示进度 |

## 🎭 师生互动设计

### 提问策略
1. **导入提问**: "小王，你测试时遇到过API限流或网络问题吗？"（激活实际痛点）
2. **引导提问**: "为什么不能直接在生产环境测试AI模型调用？"（引导思考隔离必要性）
3. **挑战提问**: "如果Mock的行为和真实服务不一致怎么办？"（激发问题解决思维）
4. **应用提问**: "在你的项目中，哪些外部依赖最适合用Mock？"（促进知识迁移）

### 讨论活动
1. **小组讨论**: 3-4人小组，讨论不同Mock模式的适用场景（10分钟）
2. **头脑风暴**: 集体创意，设计智能Mock的响应策略（5分钟）
3. **案例分析**: 分析Mock实现失败的典型案例，学习教训（8分钟）
4. **代码审查**: 互相review Mock实现，验证行为正确性（7分钟）

### 反馈机制
1. **即时反馈**: 课堂问答，及时纠正理解偏差
2. **过程反馈**: 练习指导，持续改进Mock设计
3. **成果反馈**: 作业批改，总结提升测试隔离能力
4. **同伴反馈**: 学生互评Mock设计，互相学习最佳实践

## 🔧 差异化教学

### 针对基础薄弱学生
1. **简化任务**: 提供预实现的Mock模板，只需修改响应内容
2. **额外支持**: 一对一辅导Mock模式理解，延长练习时间
3. **资源推荐**: 提供Python unittest.mock基础教程链接
4. **成功体验**: 设计可达成的子目标：成功运行一个简单Mock

### 针对进阶学生
1. **扩展挑战**: 设计支持状态机和行为验证的智能Mock
2. **创新空间**: 探索Mock录制和自动生成机制
3. **领导机会**: 担任小组长，帮助其他同学理解复杂Mock模式
4. **项目实战**: 为真实外部服务设计完整Mock系统

### 针对中等水平学生
1. **渐进提升**: 从简单响应到复杂逻辑逐步增加难度
2. **榜样学习**: 学习优秀同学的Mock设计文档和代码
3. **目标引导**: 设定明确的Mock覆盖率和行为验证目标
4. **反馈激励**: 及时肯定Mock设计的进步和创新

## 📊 评估方式

### 形成性评估（课堂内）
1. **观察评估**: 观察学生参与讨论的积极性和思考深度
2. **提问评估**: 通过提问检验Mock概念理解程度
3. **练习评估**: 检查Mock设计的合理性和完整性
4. **自评互评**: 学生自我评估设计质量，互相评价方案优劣

### 总结性评估（课堂后）
1. **作业评估**: 批改OpenAI API Mock系统作业，评分反馈
2. **测验评估**: 单元测验检验Mock策略知识点掌握
3. **项目评估**: 在周项目中评估Mock设计质量和使用效果
4. **综合评估**: 结合课堂表现、作业质量、项目贡献综合评价

### 评估标准
- **优秀（90-100分）**: 全面掌握Mock策略原理，能设计复杂系统的完整Mock架构
- **良好（80-89分）**: 基本掌握Mock概念，能实现合理的测试Mock
- **合格（60-79分）**: 理解核心概念，需要指导完成Mock设计
- **需改进（<60分）**: 需要重新学习Mock基础和测试隔离概念

## 🚨 应急预案

### 技术故障
1. **网络中断**: 准备离线演示材料，录制视频备用，提供本地文档
2. **软件故障**: 准备备用开发环境（GitHub Codespaces），使用在线IDE
3. **电力中断**: 提前通知学员调整时间，提供录播课程链接
4. **平台故障**: 准备备用教学平台（Zoom、腾讯会议、Discord）

### 学生问题
1. **理解困难**: 放慢节奏，增加Mock可视化示例，一对一辅导
2. **设备问题**: 提供远程协助，共享屏幕指导实现，提供云开发环境
3. **时间不足**: 调整内容优先级，先掌握核心概念，提供课后补充材料
4. **兴趣不足**: 增加实际案例，联系大厂面试问题，展示Mock重要性

### 内容调整
1. **进度过快**: 增加练习时间，补充Mock基础概念讲解
2. **进度过慢**: 精简扩展内容，聚焦AI模型Mock和核心服务Mock
3. **内容过难**: 分解复杂概念，提供阶梯式学习材料和代码模板
4. **内容过易**: 增加深度挑战，探索分布式系统Mock设计

## 📝 教学反思

### 成功之处
1. **实用导向**: AI模型Mock示例贴近实际开发需求
2. **渐进设计**: 从简单到复杂的Mock实现示例合理
3. **互动充分**: Mock设计讨论环节学生参与度高
4. **案例丰富**: 结合真实API Mock需求增强学习实用性

### 改进之处
1. **时间分配**: 动态响应Mock讲解可更紧凑，留更多练习时间
2. **难度梯度**: Mock状态验证需要更多铺垫和示例
3. **资源准备**: 提前准备更多可运行的Mock代码示例
4. **差异化**: 需要更精细的进阶挑战任务设计

### 学生表现
- **优秀表现**: 部分学生能设计复杂的智能Mock响应系统
- **常见问题**: Mock行为验证理解有困难，动态响应设计不合理
- **学习障碍**: 测试替身概念理解不足影响Mock模式选择

### 调整建议
1. **内容调整**: 增加测试替身概念预备知识回顾环节
2. **方法改进**: 采用更多类比（如演员替身）解释Mock概念
3. **资源优化**: 制作Mock生成器工具降低入门门槛
4. **评估细化**: 增加阶段性检查点，及时发现理解偏差

## 🎯 课后任务

### 必做任务
1. **Mock设计**: 为OpenAI ChatCompletion API设计完整Mock系统
2. **功能实现**: 实现动态响应、调用历史、断言验证功能
3. **文档撰写**: 撰写Mock使用文档，说明配置选项和验证方法
4. **测试集成**: 将Mock集成到现有测试套件，替换真实API调用

### 选做任务（挑战）
1. **高级挑战**: 设计支持流式响应（streaming）的AI模型Mock
2. **创新探索**: 实现Mock行为录制和自动代码生成
3. **性能优化**: 优化Mock响应时间，支持高并发测试场景
4. **工具开发**: 开发Mock可视化配置和验证工具

### 预习任务
1. **阅读材料**: 预习第84节课学生讲义，了解边界测试策略
2. **环境准备**: 准备压力测试工具，学习性能监控方法
3. **代码查看**: 查看DeerFlow tests/boundary/目录，理解边界测试实现
4. **问题思考**: 思考如何为AI Agent系统设计有效的边界测试

### 资源推荐
1. **阅读材料**: 
   - 《测试驱动开发》第8章：Mock对象模式
   - Python官方文档：unittest.mock完整指南
   - OpenAI API文档：理解真实接口行为
2. **视频教程**:
   - "Mastering Python Mocks" (PyCon 2023)
   - "Testing External Services" (Real Python)
   - "AI System Testing Strategies" (DeerFlow官方频道)
3. **实践项目**:
   - GitHub: deer-flow/mocking-examples
   - GitLab: openai-api-mock-implementation
   - CodeSandbox: deerflow-mocking-playground
4. **社区讨论**:
   - Discord: #testing-mocking频道
   - 知乎专栏: Python Mock高级技巧
   - 掘金小册: 大厂Mock测试实践

---

## 📋 附录

### 附录A：PPT幻灯片要点
1. **封面页**: Mock测试策略 - 第83节课 - 张老师 - 2024.04.14
2. **目标页**: 知识目标×3、技能目标×3、情感目标×3
3. **导入页**: 第82节课复习、Mock重要性、今日学习路线
4. **概念页**: Mock分类图、测试替身类型、AI Mock特殊性
5. **示例页**: MockChatModel完整实现、MockMCPServer架构图
6. **练习页**: 天气API Mock设计任务、接口分析表、实现检查清单
7. **总结页**: 关键概念回顾、最佳实践总结、常见问题解答
8. **作业页**: 必做任务×4、选做挑战×4、预习要求×4
9. **资源页**: 推荐阅读×3、视频教程×3、实践项目×3、社区讨论×3

### 附录B：学生练习任务卡
```markdown
# 课堂练习：设计智能天气API Mock

## 任务描述
为天气查询API设计智能Mock系统，API接口规范如下：
- 端点: GET /api/weather
- 参数: city (城市名), date (日期，可选)
- 响应: JSON格式，包含temperature(温度)、condition(天气状况)、humidity(湿度)

Mock需要支持以下智能行为：
1. 根据城市名返回不同的基准天气（如北京：15°C/晴，上海：18°C/多云）
2. 根据日期调整温度（夏季温度高，冬季温度低）
3. 模拟异常情况：无效城市返回404，服务器错误返回500
4. 记录所有调用历史，支持断言验证

## 要求
- [ ] 实现完整的Mock服务器类
- [ ] 支持动态响应生成
- [ ] 实现调用历史记录和验证
- [ ] 支持异常情况模拟
- [ ] 提供简便的测试集成接口

## 步骤指导
1. **分析API规范**（5分钟）：
   - 理解请求参数和响应格式
   - 识别需要模拟的智能行为
   - 确定异常情况和错误处理

2. **设计Mock结构**（8分钟）：
   - 设计WeatherAPIMock类
   - 定义响应映射数据结构
   - 设计调用历史记录机制
   - 规划异常模拟策略

3. **实现Mock逻辑**（10分钟）：
   - 实现基础响应生成
   - 添加日期敏感的温度调整
   - 实现调用历史记录
   - 添加异常模拟功能
   - 实现断言验证方法

4. **验证与测试**（5分钟）：
   - 编写测试用例验证Mock行为
   - 测试正常情况和异常情况
   - 验证调用历史记录功能
   - 测试与真实测试的集成

## 提示与技巧
- **技巧1**: 使用字典映射城市到基准天气数据
- **技巧2**: 根据日期月份调整温度（夏季+5°C，冬季-5°C）
- **技巧3**: 使用列表记录调用历史，支持复杂查询
- **技巧4**: 设计清晰的异常模拟开关，便于测试不同场景

## 检查点
- [ ] Mock能正确处理正常天气查询
- [ ] 温度能根据日期智能调整
- [ ] 异常情况模拟正确
- [ ] 调用历史记录完整
- [ ] 断言验证功能可用

## 扩展挑战（可选）
- **挑战1**: 实现支持流式天气更新的Mock（WebSocket）
- **挑战2**: 设计地理位置到城市的自动解析
- **挑战3**: 实现天气预测算法的Mock（基于历史模式）
- **挑战4**: 开发天气Mock的可视化配置界面
```

### 附录C：课堂观察记录表
| 观察项目 | 观察要点 | 记录 |
|----------|----------|------|
| 学生参与度 | 积极发言、提问、讨论参与程度 | |
| 理解程度 | Mock概念掌握、AI Mock理解准确性 | |
| 合作交流 | 小组协作效果、知识分享意愿 | |
| 问题解决 | 遇到Mock设计问题时的调试策略 | |
| 学习兴趣 | 对Mock测试策略的兴趣表现 | |
| 实践能力 | 练习任务完成速度和质量 | |
| 创新思维 | 在Mock设计中展现的创新点 | |
| 反馈响应 | 对教师反馈的接受和改进 | |

### 附录D：学生反馈表
```markdown
# 课堂反馈 - 第83节课：Mock策略

## 学习收获
本节课我学到了：
1. 
2. 
3. 

## 理解程度（1-5分，5分为完全理解）
- Mock核心概念: □1 □2 □3 □4 □5
- AI模型Mock设计: □1 □2 □3 □4 □5  
- 外部服务Mock: □1 □2 □3 □4 □5

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

### 附录E：AI模型Mock完整代码示例
```python
"""
AI模型Mock - 完整实现示例
来自学生讲义第83节内容
"""
import time
from typing import Dict, List, Optional


class MockChatModel:
    """模拟聊天模型"""
    
    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.call_history = []
    
    async def invoke(self, prompt: str, **kwargs) -> str:
        """模拟模型调用"""
        self.call_history.append({
            "prompt": prompt,
            "kwargs": kwargs,
            "timestamp": time.time(),
        })
        
        # 查找匹配的响应
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return response
        
        # 默认响应
        return f"Mock response for: {prompt[:50]}..."
    
    def assert_called_with(self, expected_prompt: str):
        """断言被调用过"""
        for call in self.call_history:
            if expected_prompt in call["prompt"]:
                return
        
        raise AssertionError(f"Expected prompt not found: {expected_prompt}")
    
    def assert_called_times(self, expected_times: int):
        """断言调用次数"""
        actual_times = len(self.call_history)
        if actual_times != expected_times:
            raise AssertionError(
                f"Expected {expected_times} calls, got {actual_times}"
            )
    
    def get_call_history(self) -> List[Dict]:
        """获取调用历史"""
        return self.call_history.copy()
    
    def clear_history(self):
        """清空调用历史"""
        self.call_history.clear()


# 使用示例
@pytest.fixture
def mock_chat_model():
    """提供Mock聊天模型"""
    return MockChatModel({
        "hello": "Hello! How can I help you?",
        "calculate": "The result is 42.",
        "error": "I'm sorry, I can't do that.",
    })


async def test_agent_with_mock(mock_chat_model):
    """使用Mock模型测试Agent"""
    # 模拟Agent使用模型
    response1 = await mock_chat_model.invoke("Say hello")
    response2 = await mock_chat_model.invoke("Calculate 2+2")
    
    # 验证响应
    assert "hello" in response1.lower()
    assert "42" in response2
    
    # 验证调用历史
    mock_chat_model.assert_called_times(2)
    mock_chat_model.assert_called_with("Calculate")
    
    # 检查调用历史详情
    history = mock_chat_model.get_call_history()
    assert len(history) == 2
    assert history[0]["prompt"] == "Say hello"
```

### 附录F：外部服务Mock完整代码示例
```python
"""
外部服务Mock - 完整实现示例
来自学生讲义第83节内容
"""
import asyncio
from typing import Dict, List


class MockMCPServer:
    """模拟MCP服务器"""
    
    def __init__(self):
        self.tools = {
            "filesystem.read": self.mock_read_file,
            "filesystem.write": self.mock_write_file,
            "sql.query": self.mock_sql_query,
        }
        self.requests = []
    
    async def handle_request(self, request: Dict) -> Dict:
        """处理MCP请求"""
        self.requests.append(request)
        
        method = request.get("method")
        params = request.get("params", {})
        
        if method in self.tools:
            result = await self.tools[method](params)
            return {"result": result}
        else:
            return {"error": {"code": -32601, "message": "Method not found"}}
    
    async def mock_read_file(self, params: Dict) -> Dict:
        """模拟读取文件"""
        path = params.get("path", "")
        
        if "secret" in path:
            return {"error": "Access denied"}
        
        return {
            "content": f"Mock content of {path}",
            "size": len(path) * 10,
        }
    
    async def mock_write_file(self, params: Dict) -> Dict:
        """模拟写入文件"""
        return {"success": True, "bytes_written": len(params.get("content", ""))}
    
    async def mock_sql_query(self, params: Dict) -> Dict:
        """模拟SQL查询"""
        query = params.get("query", "")
        
        if "SELECT" in query.upper():
            return {
                "rows": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ],
                "count": 2,
            }
        else:
            return {"affected_rows": 1}
    
    def assert_request_received(self, expected_method: str):
        """断言收到特定请求"""
        for request in self.requests:
            if request.get("method") == expected_method:
                return
        
        raise AssertionError(f"Expected request not found: {expected_method}")
    
    def get_requests_by_method(self, method: str) -> List[Dict]:
        """按方法获取请求"""
        return [r for r in self.requests if r.get("method") == method]


# pytest-mock使用示例
def test_agent_with_mocks(mocker):
    """使用pytest-mock进行测试"""
    # Mock OpenAI API
    mock_openai = mocker.patch("openai.ChatCompletion.create")
    mock_openai.return_value = {
        "choices": [{
            "message": {"content": "Mock response"}
        }]
    }
    
    # Mock HTTP请求
    mock_requests = mocker.patch("httpx.AsyncClient.post")
    
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
        
        def json(self):
            return self.json_data
        
        @property
        def status_code(self):
            return 200
    
    mock_requests.return_value = MockResponse(json={"result": "success"})
    
    # Mock文件系统
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="test data"))
    
    # 创建并测试Agent
    agent = create_test_agent()
    result = agent.run("Test prompt")
    
    # 验证Mock调用
    mock_openai.assert_called_once()
    assert result == "Mock response"
    
    # 验证文件系统调用
    mock_open.assert_called_once()


# 集成测试示例
async def test_mcp_integration():
    """测试MCP集成"""
    server = MockMCPServer()
    
    # 测试读取文件
    response = await server.handle_request({
        "method": "filesystem.read",
        "params": {"path": "/home/test.txt"},
    })
    
    assert "result" in response
    assert "Mock content" in response["result"]["content"]
    
    # 测试写入文件
    response = await server.handle_request({
        "method": "filesystem.write",
        "params": {"path": "/home/test.txt", "content": "Hello"},
    })
    
    assert response["result"]["success"]
    assert response["result"]["bytes_written"] == 5
    
    # 验证请求历史
    server.assert_request_received("filesystem.read")
    server.assert_request_received("filesystem.write")
    
    read_requests = server.get_requests_by_method("filesystem.read")
    assert len(read_requests) == 1
```

---

**教案编制**: 张老师  
**编制日期**: 2024年3月24日  
**版本**: v1.0  
**适用对象**: DeerFlow Python Agent架构师训练营学员  

**教学备注**: 
- 本教案基于DeerFlow学生讲义Day 21第83节内容编写
- 整合了实际DeerFlow Mock测试实现代码
- 设计符合45分钟课堂实际教学需求
- 包含完整的教学资源和支持材料
1. **课程互动实录参考**:
   - 讲师引导："今天我们来学习如何模拟外部服务进行测试。"
   - 学生提问："Mock测试会不会导致测试和实际行为脱节？"
   - 讲师解答："好的Mock应该基于真实接口行为设计，并通过契约测试验证一致性。"

2. **大厂面试准备要点**:
   - 字节跳动：重视Mock设计和测试隔离能力
   - 阿里巴巴：关注Mock行为的真实性和可维护性
   - 腾讯：强调复杂场景的Mock策略设计
   - 华为：重视外部依赖管理和测试稳定性

3. **实际项目应用**:
   - AI模型Mock是成本控制和测试稳定的关键
   - 外部服务Mock支持离线开发和测试
   - 智能Mock能模拟复杂业务逻辑和异常情况
   - Mock验证能确保系统行为符合预期接口契约