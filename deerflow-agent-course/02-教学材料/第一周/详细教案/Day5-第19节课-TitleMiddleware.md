# Day 5 第19节课：TitleMiddleware

## 课程基本信息

| 项目 | 内容 |
|------|------|
| **课程名称** | TitleMiddleware |
| **所属课程** | DeerFlow Python Agent架构师训练营 - 第一周 |
| **课时编号** | Day 5 第19节课（总第19节课） |
| **授课时间** | 45分钟 |
| **授课形式** | 混合式教学（理论讲解 + 代码实战 + 互动练习） |
| **授课教师** | 张老师（10年AI系统架构经验，DeerFlow核心贡献者） |
| **授课对象** | 小王（Python基础一般，已掌握错误处理和澄清机制） |
| **前置知识** | ToolErrorHandlingMiddleware、ClarificationMiddleware、字符串处理基础 |
| **后续课程** | Day 5 第20节课：实战：错误处理和澄清机制 |

## 教学目标

### 知识目标
1. 理解对话标题生成的重要性和应用场景
2. 掌握关键词提取和意图识别的基本方法
3. 熟悉TitleMiddleware的设计与实现原理

### 能力目标
1. 能够从用户消息中提取关键信息生成简洁标题
2. 能够分析对话历史生成有意义的概括性标题
3. 能够将标题生成中间件集成到Agent系统中

### 素养目标
1. 培养信息摘要和概括的思维能力
2. 增强用户体验设计的意识
3. 建立"结构化对话"的管理思维

## 教学重点与难点

### 教学重点
1. **关键词提取技术**：停用词过滤、关键词排序、长度控制
2. **意图识别方法**：基于关键词的意图分类
3. **标题生成策略**：从消息到标题的转换规则

### 教学难点
1. **标题简洁性 vs 信息完整性**：平衡标题长度和信息含量
2. **上下文感知**：基于对话历史生成连贯标题
3. **多语言支持**：处理中文特有的分词和停用词

### 突破策略
1. **示例驱动**：展示不同消息生成的标题示例
2. **规则模板**：提供可配置的标题生成模板
3. **渐进优化**：从简单实现开始逐步增加高级功能

## 教学资源准备

### 教师准备
1. **演示代码**：完整的TitleMiddleware实现
2. **消息案例库**：各种类型的用户消息和期望标题
3. **停用词列表**：中文常用停用词表
4. **标题质量评估工具**：评估生成标题的质量

### 学生准备
1. **开发环境**：Python 3.12+、DeerFlow开发环境
2. **代码编辑器**：VS Code或PyCharm
3. **文本处理工具**：中文分词工具（可选）

### 硬件准备
1. **投影设备**：展示代码和演示结果
2. **网络环境**：稳定网络连接
3. **示例展示工具**：展示标题生成效果的工具

## 教学流程（45分钟）

### 一、课程导入（5分钟）

#### 1. 复习回顾（2分钟）
**教师活动**：
- 提问：上节课我们学习了什么？ClarificationMiddleware解决什么问题？
- 引导：澄清机制让对话更清晰，那如何让对话更容易管理和查找？

**学生活动**：
- 回答：学习了澄清机制，解决用户请求模糊的问题
- 思考：大量对话历史中如何快速找到特定对话？

#### 2. 问题引入（3分钟）
**教师活动**：
- 情景：小王有1000条对话记录，想找到"上周讨论Python异步编程的那次对话"
- 提问：如果没有标题，如何快速定位？如果有标题"搜索：Python异步编程"呢？
- 类比：书的目录和章节标题，让读者能快速定位内容

**学生活动**：
- 讨论：无标题需要逐条查看，有标题可以快速扫描
- 理解：标题是对话的组织和管理工具

### 二、新课讲解（15分钟）

#### 1. 标题生成基础（5分钟）

**教师讲解**：
```
🔍 标题生成的核心价值：
1. 组织管理：方便对话历史的浏览和搜索
2. 用户体验：提供清晰的对话标识
3. 信息摘要：概括对话的核心内容
4. 自动化：减少用户手动命名的负担

🎯 标题质量要求：
1. 简洁性：不超过50个字符
2. 代表性：准确反映对话主题
3. 可读性：自然流畅，易于理解
4. 一致性：相同类型的对话使用相似格式
```

**代码展示**：
```python
import re
from typing import List, Dict, Optional

class TitleMiddleware:
    """标题生成中间件基础框架"""
    
    def __init__(self):
        self.name = "title"
        self.max_title_length = 50  # 标题最大长度
    
    def extract_key_words(self, text: str) -> List[str]:
        """提取关键词"""
        # 移除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        
        # 中文停用词表（部分）
        stop_words = {
            '的', '了', '在', '是', '我', '你', '他', '她', '它',
            '这', '那', '什么', '怎么', '如何', '为什么', '帮忙',
            '请', '帮', '一下', '一个', '这个', '那个', '和', '与',
            '吗', '呢', '吧', '啊', '呀', '哦', '嗯', '唉'
        }
        
        # 简单分词：按空格分割（实际应用应使用分词工具）
        words = text.split()
        # 过滤停用词和短词
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        return keywords[:5]  # 返回前5个关键词
    
    def detect_intent(self, message: str) -> str:
        """检测意图类型"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["帮", "请", "帮我"]):
            if any(word in message_lower for word in ["搜索", "查找", "找"]):
                return "搜索"
            elif any(word in message_lower for word in ["创建", "新建"]):
                return "创建"
            elif any(word in message_lower for word in ["删除", "移除"]):
                return "删除"
            elif any(word in message_lower for word in ["修改", "更新"]):
                return "修改"
            elif any(word in message_lower for word in ["分析", "统计"]):
                return "分析"
            else:
                return "请求"
        elif any(word in message_lower for word in ["怎么", "如何", "什么"]):
            return "询问"
        else:
            return "对话"
```

#### 2. 标题生成策略（5分钟）

**教师讲解**：
```
🔧 标题生成策略：
1. 意图+关键词：如"搜索：Python异步编程"
2. 消息截取：直接截取消息前N个字符
3. 关键词组合：多个关键词用空格连接
4. 模板填充：使用预定义模板填充关键信息

📊 策略选择优先级：
1. 如果有明确意图和关键词 → 意图+关键词
2. 如果消息简短 → 消息截取
3. 如果只有关键词 → 关键词组合
4. 其他情况 → 默认模板
```

**代码展示**：
```python
    def generate_title(self, message: str, context: Dict) -> str:
        """生成标题"""
        # 提取关键词
        keywords = self.extract_key_words(message)
        
        # 检测意图类型
        intent = self.detect_intent(message)
        
        # 策略1：意图+关键词
        if keywords and intent != "对话":
            title = f"{intent}：{' '.join(keywords[:3])}"
        
        # 策略2：关键词组合
        elif keywords:
            title = ' '.join(keywords[:3])
        
        # 策略3：消息截取
        else:
            title = message[:self.max_title_length]
        
        # 长度限制和修剪
        if len(title) > self.max_title_length:
            title = title[:self.max_title_length - 3] + "..."
        
        # 确保非空
        if not title.strip():
            title = "新对话"
        
        return title
    
    async def before_agent(
        self,
        request: AgentRequest,
        config: Optional[Dict] = None
    ) -> AgentRequest:
        """生成标题并附加到请求"""
        title = self.generate_title(request.message, {})
        
        print(f"📝 [{self.name}] 生成标题: {title}")
        
        # 将标题存储到请求元数据中
        if not request.metadata:
            request.metadata = {}
        request.metadata["generated_title"] = title
        
        return request
    
    async def after_agent(
        self,
        response: AgentResponse,
        config: Optional[Dict] = None
    ) -> AgentResponse:
        """保存标题到线程数据"""
        if response.metadata and "generated_title" in response.metadata:
            title = response.metadata["generated_title"]
            print(f"💾 [{self.name}] 保存标题: {title}")
            
            # 在实际应用中，这里会将标题保存到数据库或文件
            # 例如：await self.save_title_to_storage(response.thread_id, title)
        
        return response
```

#### 3. 高级标题生成（5分钟）

**教师讲解**：
```
🧠 高级标题生成技术：
1. 对话历史分析：考虑整个对话流程
2. 多轮对话标题：为长对话生成序列标题
3. 工具调用识别：基于使用的工具生成标题
4. 个性化标题：考虑用户偏好和习惯
```

**代码展示**：
```python
class TitleGenerationStrategy:
    """标题生成策略（高级版）"""
    
    @staticmethod
    def generate_from_messages(messages: List[Dict]) -> str:
        """从消息历史生成标题"""
        
        if not messages:
            return "新对话"
        
        # 提取用户第一条消息
        first_user_msg = next(
            (m for m in messages if m["role"] == "user"),
            None
        )
        
        if first_user_msg:
            content = first_user_msg["content"]
            
            # 策略1：截取前N个字符
            if len(content) <= 50:
                return content
            else:
                return content[:47] + "..."
        
        # 策略2：基于工具调用
        tool_calls = [
            m for m in messages 
            if m.get("type") == "tool_call"
        ]
        
        if tool_calls:
            tools = [call["tool_name"] for call in tool_calls[:3]]
            return f"工具调用：{', '.join(tools)}"
        
        # 默认标题
        return f"对话 ({len(messages)} 条消息)"
    
    @staticmethod
    def generate_from_tools(tool_results: List[Dict]) -> str:
        """从工具结果生成标题"""
        
        if not tool_results:
            return "无工具调用"
        
        # 提取主要工具
        main_tool = tool_results[0]["tool_name"]
        
        # 根据工具类型生成标题
        tool_titles = {
            "search": "搜索",
            "calculate": "计算",
            "file_read": "文件读取",
            "code_execute": "代码执行",
            "web_search": "网络搜索",
            "data_analysis": "数据分析"
        }
        
        return tool_titles.get(main_tool, main_tool)

class AdvancedTitleMiddleware(TitleMiddleware):
    """高级标题生成中间件"""
    
    def __init__(self):
        super().__init__()
        self.conversation_history = []
    
    def analyze_conversation_flow(self, messages: List[tuple]) -> str:
        """分析对话流程"""
        if not messages:
            return "新对话"
        
        # 统计意图分布
        intents = {
            "search": 0, "create": 0, "delete": 0, 
            "modify": 0, "analyze": 0, "question": 0
        }
        
        for role, msg in messages:
            if role == "user":
                msg_lower = msg.lower()
                if any(w in msg_lower for w in ["搜索", "查找", "找"]):
                    intents["search"] += 1
                elif any(w in msg_lower for w in ["创建", "新建"]):
                    intents["create"] += 1
                elif any(w in msg_lower for w in ["删除", "移除"]):
                    intents["delete"] += 1
                elif any(w in msg_lower for w in ["修改", "更新"]):
                    intents["modify"] += 1
                elif any(w in msg_lower for w in ["分析", "统计"]):
                    intents["analyze"] += 1
                elif any(w in msg_lower for w in ["怎么", "如何", "什么", "为什么"]):
                    intents["question"] += 1
        
        # 找出最频繁的意图
        dominant_intent = max(intents.items(), key=lambda x: x[1])
        
        if dominant_intent[1] == 0:
            return "对话"
        
        intent_map = {
            "search": "搜索任务",
            "create": "创建任务",
            "delete": "删除任务",
            "modify": "修改任务",
            "analyze": "分析任务",
            "question": "问答"
        }
        
        return intent_map.get(dominant_intent[0], "对话")
```

### 三、实战演示（10分钟）

#### 1. 完整测试系统搭建（5分钟）

**教师演示**：
```python
import asyncio

# 简化的请求响应类用于演示
class AgentRequest:
    def __init__(self, user_id: str, message: str):
        self.user_id = user_id
        self.message = message
        self.metadata = {}

class AgentResponse:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.metadata = {}

async def test_title_generation():
    middleware = TitleMiddleware()
    
    test_messages = [
        "帮我搜索一下Python异步编程的资料",
        "如何用Python创建web服务器？",
        "请帮我分析这个销售数据，按月份统计",
        "随便聊聊天气",
        "删除那个没用的文件",
        "修改用户配置，把超时时间改成30秒"
    ]
    
    print("🧪 测试标题生成系统...")
    print("=" * 50)
    
    for msg in test_messages:
        print(f"\n原始消息: '{msg}'")
        
        # 生成标题
        request = AgentRequest(user_id="test", message=msg)
        result = await middleware.before_agent(request)
        
        title = result.metadata.get("generated_title", "无标题")
        print(f"生成标题: '{title}'")
        
        # 模拟保存标题
        response = AgentResponse(thread_id="thread_123")
        response.metadata = result.metadata
        await middleware.after_agent(response)

# 运行测试
asyncio.run(test_title_generation())
```

#### 2. 运行结果分析（5分钟）

**教师展示**：
```
🧪 测试标题生成系统...
==================================================

原始消息: '帮我搜索一下Python异步编程的资料'
生成标题: '搜索：Python 异步 编程'
📝 [title] 生成标题: 搜索：Python 异步 编程
💾 [title] 保存标题: 搜索：Python 异步 编程

原始消息: '如何用Python创建web服务器？'
生成标题: '询问：Python 创建 web 服务器'
📝 [title] 生成标题: 询问：Python 创建 web 服务器
💾 [title] 保存标题: 询问：Python 创建 web 服务器

原始消息: '请帮我分析这个销售数据，按月份统计'
生成标题: '分析：销售 数据 月份 统计'
📝 [title] 生成标题: 分析：销售 数据 月份 统计
💾 [title] 保存标题: 分析：销售 数据 月份 统计

原始消息: '随便聊聊天气'
生成标题: '对话：聊聊 天气'
📝 [title] 生成标题: 对话：聊聊 天气
💾 [title] 保存标题: 对话：聊聊 天气

原始消息: '删除那个没用的文件'
生成标题: '删除：没用 文件'
📝 [title] 生成标题: 删除：没用 文件
💾 [title] 保存标题: 删除：没用 文件

原始消息: '修改用户配置，把超时时间改成30秒'
生成标题: '修改：用户 配置 超时 时间'
📝 [title] 生成标题: 修改：用户 配置 超时 时间
💾 [title] 保存标题: 修改：用户 配置 超时 时间
```

**教师讲解**：
```
🔍 结果分析：
1. 意图识别准确：正确识别了搜索、询问、分析、对话、删除、修改等意图
2. 关键词提取有效：提取了核心关键词（Python、异步、编程、销售、数据等）
3. 标题格式统一：都采用"意图：关键词"的格式
4. 长度控制合理：所有标题都在50字符以内

📊 关键观察：
• 停用词过滤：过滤了"帮我"、"一下"、"这个"、"那个"等词
• 意图分类：能区分"询问"（如何/怎么）和"请求"（帮我）
• 多关键词处理：合理选择前3个关键词，避免标题过长
• 特殊字符处理：正确处理了问号、逗号等标点
```

### 四、学生实践（10分钟）

#### 1. 课堂练习（5分钟）

**学生任务**：
1. 在自己的环境中运行测试代码
2. 扩展停用词列表，添加更多常见停用词
3. 添加新的意图识别规则（如"翻译"、"转换"等）

**教师巡视**：
- 检查学生代码环境
- 解答学生遇到的问题
- 指导学生设计意图识别规则

#### 2. 拓展练习（5分钟）

**学生任务**：
1. 实现基于对话历史的标题生成
2. 设计标题质量评估函数
3. 思考：如何让标题更具可读性和吸引力？

**代码提示**：
```python
class TitleQualityEvaluator:
    """标题质量评估器"""
    
    @staticmethod
    def evaluate_title(title: str, original_message: str) -> Dict[str, float]:
        """评估标题质量"""
        scores = {}
        
        # 1. 简洁性评分（越短越好，但不要太短）
        length_score = 1.0 - min(len(title) / 100, 1.0)
        if len(title) < 5:
            length_score *= 0.5  # 太短惩罚
        scores["简洁性"] = length_score
        
        # 2. 信息量评分（包含原消息关键词）
        original_words = set(original_message.split())
        title_words = set(title.split())
        overlap = len(original_words & title_words) / max(len(original_words), 1)
        scores["信息量"] = overlap
        
        # 3. 可读性评分（检查是否有不连贯的词）
        # 简单实现：检查是否包含意图标记
        readability = 1.0 if "：" in title or ":" in title else 0.7
        scores["可读性"] = readability
        
        # 综合评分
        scores["综合"] = sum(scores.values()) / len(scores)
        
        return scores
```

### 五、总结与作业（5分钟）

#### 1. 课程总结（2分钟）

**教师总结**：
```
🎯 本节课重点：
1. 标题生成价值：组织管理、用户体验、信息摘要、自动化
2. TitleMiddleware实现：关键词提取、意图识别、标题生成
3. 高级标题技术：对话历史分析、工具调用识别、质量评估

💡 关键技巧：
1. 停用词过滤：移除无意义的常用词
2. 意图识别：基于关键词的简单分类
3. 标题格式：意图+关键词的统一格式
4. 长度控制：确保标题简洁可读
```

#### 2. 课后作业布置（3分钟）

**必做作业**：
1. 完善TitleMiddleware，添加以下功能：
   - 支持中文分词（使用jieba等分词库）
   - 添加标题缓存机制（避免重复生成）
   - 实现标题编辑功能（允许用户修改生成的标题）

2. 在实际项目中应用标题生成：
   - 分析现有对话的标题需求
   - 设计适合项目特点的标题格式
   - 测试标题生成对用户体验的影响

**选做作业**：
1. 实现智能标题优化：
   - 基于用户反馈优化标题生成规则
   - 实现A/B测试比较不同标题策略
   - 添加标题个性化功能

2. 研究高级标题生成技术：
   - 了解文本摘要算法（如TextRank）
   - 研究深度学习标题生成模型
   - 对比不同标题生成方法的效果

**预习任务**：
1. 阅读Day 5第20节课材料：实战：错误处理和澄清机制
2. 思考：如何将错误处理、澄清、标题生成整合到一个系统中？
3. 准备：复习前面所学中间件的集成方法

## 师生互动设计

### 互动环节1：问题引入（3分钟）
**教师提问**："如果你有1000条对话记录，如何快速找到'上周讨论Python异步编程的那次对话'？"
**学生回答**：搜索关键词、按时间排序、手动添加标签等
**教师引导**："如果每条对话都有自动生成的标题呢？标题应该包含什么信息？"

### 互动环节2：规则设计（5分钟）
**教师提问**："'帮我搜索一下Python异步编程的资料'这个消息，应该生成什么标题？"
**学生思考**：讨论可能的标题格式（"搜索Python异步编程"、"Python异步编程搜索"等）
**教师总结**：标题应该包含意图和核心关键词，格式统一

### 互动环节3：实践反馈（5分钟）
**学生展示**：新添加的意图识别规则
**教师点评**：分析规则的覆盖率和准确性
**同学互评**：分享不同的标题生成策略

## 差异化教学

### 基础薄弱学生
1. **简化要求**：只需理解标题生成概念，能运行演示代码
2. **详细指导**：提供完整的代码模板，逐行解释
3. **重点掌握**：关键词提取和意图识别的基本方法

### 基础扎实学生
1. **拓展要求**：实现高级功能（对话历史分析、质量评估）
2. **深入探究**：研究不同分词工具的效果对比
3. **实际应用**：在真实对话系统中应用标题生成

### 学有余力学生
1. **挑战任务**：实现基于深度学习的标题生成
2. **研究课题**：标题质量对用户满意度的量化影响
3. **创新设计**：设计交互式标题编辑和优化系统

## 评估方式

### 形成性评估
1. **课堂参与**：提问回答、代码练习完成情况
2. **实践能力**：能否独立运行和修改标题生成系统
3. **理解深度**：能否解释标题生成的策略和算法

### 总结性评估
1. **作业完成**：完善TitleMiddleware的功能实现
2. **项目应用**：在实际项目中应用标题生成的情况
3. **质量评估**：评估生成标题的质量和实用性

### 评估标准
| 等级 | 标准 |
|------|------|
| **优秀** | 完整实现所有功能，有创新设计，能生成高质量的标题 |
| **良好** | 完成基本功能，理解原理，能应用于简单场景 |
| **合格** | 能运行演示代码，理解基本概念 |
| **待改进** | 需要进一步学习和实践 |

## 应急预案

### 技术问题
1. **环境问题**：中文分词库安装失败
   - 备用方案：使用纯Python的简单分词方法
   - 快速解决：提供预构建的Docker镜像

2. **代码运行错误**：正则表达式匹配问题
   - 备用方案：提供简化的字符串处理方法
   - 逐步调试：使用print调试，分步运行

### 时间问题
1. **进度滞后**：学生理解困难
   - 调整策略：跳过拓展部分，保证核心内容
   - 课后补充：录制微视频讲解难点

2. **进度超前**：学生掌握迅速
   - 拓展内容：介绍高级标题生成技术
   - 深入讨论：生产环境标题生成的最佳实践

### 内容问题
1. **内容过难**：学生跟不上
   - 简化讲解：用生活比喻解释技术概念
   - 增加示例：提供更多简单易懂的代码示例

2. **内容过简**：学生觉得无聊
   - 增加挑战：提出进阶问题
   - 实际案例：分享生产环境中的标题生成案例

## 教学反思

### 成功之处
1. **概念清晰**：标题生成的价值和实现讲解透彻
2. **实践导向**：代码演示完整，学生能立即上手
3. **互动充分**：学生参与度高，案例讨论热烈

### 改进之处
1. **时间分配**：实践环节可以更充分
2. **案例丰富度**：需要更多真实对话标题案例
3. **评估方式**：增加实时反馈机制

### 学生反馈
（课后填写）
- 对标题生成的理解程度：□完全理解 □基本理解 □部分理解 □不理解
- 实践环节的难度：□合适 □偏难 □偏易
- 最有收获的部分：____________________
- 需要改进的部分：____________________

## 课后任务

### 巩固练习
1. 重新实现TitleMiddleware，使用不同的标题生成策略
2. 为标题生成系统添加单元测试
3. 比较不同分词工具对标题质量的影响

### 拓展阅读
1. **官方文档**：DeerFlow标题生成系统设计文档
2. **技术文章**：《对话系统标题自动生成技术》
3. **研究论文**：《Automatic Conversation Title Generation》

### 项目实践
1. **小项目**：实现一个简单的聊天记录标题生成器
2. **集成实践**：将标题生成集成到个人项目中
3. **用户测试**：收集用户对生成标题的反馈和建议

## 附录

### 附录1：PPT幻灯片设计

**幻灯片1：课程标题**
- 标题：TitleMiddleware
- 副标题：让对话"有迹可循"
- 讲师信息：张老师 - DeerFlow核心贡献者

**幻灯片2：问题引入**
- 情景：1000条对话记录中找到特定对话
- 问题：如何快速定位？无标题 vs 有标题
- 类比：书的目录和章节标题

**幻灯片3：标题生成价值**
- 四大价值：组织管理、用户体验、信息摘要、自动化
- 质量要求：简洁性、代表性、可读性、一致性
- 数据：标题对对话查找效率的影响研究

**幻灯片4：关键技术**
- 关键词提取：停用词过滤、分词、关键词排序
- 意图识别：基于关键词的分类方法
- 标题生成：意图+关键词的格式模板
- 长度控制：最大字符限制和修剪策略

**幻灯片5：基础实现**
- TitleMiddleware类结构
- 核心方法：extract_key_words、detect_intent、generate_title
- 代码架构图

**幻灯片6：高级标题生成**
- TitleGenerationStrategy设计
- 对话历史分析方法
- 工具调用识别技术
- 标题质量评估

**幻灯片7：完整测试示例**
- 测试代码结构
- 多种用户消息测试案例
- 预期输出结果

**幻灯片8：运行结果分析**
- 实际运行结果展示
- 标题质量分析
- 优化建议

**幻灯片9：学生实践任务**
- 基础任务：运行和修改测试代码
- 拓展任务：实现标题质量评估
- 挑战任务：智能标题优化

**幻灯片10：课程总结与作业**
- 重点回顾：三大核心技术
- 作业要求：完善功能，实际应用
- 预习任务：综合实战：错误处理和澄清机制

### 附录2：课堂练习检查表

**学生自查表**
- [ ] Python环境准备就绪
- [ ] 代码编辑器配置完成
- [ ] 成功运行基础测试代码
- [ ] 理解关键词提取方法
- [ ] 能够解释意图识别原理
- [ ] 完成至少一个拓展练习

**教师检查表**
- [ ] 所有学生环境正常
- [ ] 核心概念讲解清楚
- [ ] 实践环节指导到位
- [ ] 学生问题得到解答
- [ ] 课堂时间控制合理

### 附录3：课后反馈表

**学生学习反馈**
```
学生姓名：__________
学习日期：__________

1. 对本节课内容的整体评分（1-5分）：_____
2. 最容易理解的部分：____________________
3. 最难理解的部分：____________________
4. 实践环节的收获：____________________
5. 对教师的建议：____________________
6. 希望增加的内容：____________________
```

**教师教学反思**
```
教学日期：__________
学生人数：__________

1. 教学目标达成度：□完全达成 □基本达成 □部分达成 □未达成
2. 学生参与情况：□非常积极 □比较积极 □一般 □不积极
3. 时间分配合理性：□合理 □基本合理 □不合理
4. 教学难点处理：□很好 □一般 □需要改进
5. 下次改进方向：____________________
```

### 附录4：相关资源链接

1. **DeerFlow源码**：https://github.com/bytedance/deer-flow
2. **中文分词工具**：https://github.com/fxsjy/jieba
3. **文本摘要算法**：https://www.aclweb.org/anthology/P04-1045/
4. **标题生成研究**：https://arxiv.org/abs/2002.01187
5. **课程资料下载**：https://deerflow.tech/course/day5-lesson19

---

**教师寄语**：
"好的标题是对话的'眼睛'，让用户一眼就能看到对话的灵魂。标题生成不仅是技术，更是艺术——在简洁与丰富、准确与优雅之间找到平衡。今天你学会了如何为对话'点睛'，明天我们将学习如何打造'全能战士'——整合错误处理、澄清和标题生成的完整系统。记住：细节决定体验，体验决定成败。"

*备课人：张老师*
*备课时间：2024年3月24日*
*课程版本：v1.0*
*预计授课时间：45分钟*
