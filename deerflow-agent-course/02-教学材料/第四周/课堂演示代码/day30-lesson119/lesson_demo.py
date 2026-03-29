#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大厂面试准备 - 演示代码

本模块展示AI Agent架构师面试中的核心技术问题及其解答框架。
包含：概念题、设计题、实践题、场景题的示例与回答策略。

作者: DeerFlow架构师训练营
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json


# ============================================================================
# 第一部分：面试题型分类与框架
# ============================================================================

class InterviewQuestionType(Enum):
    """面试问题类型枚举
    
    用于分类和准备不同类型的面试问题
    """
    CONCEPT = "concept"      # 概念题：考察基础知识和理解
    DESIGN = "design"        # 设计题：考察系统设计和架构能力
    PRACTICAL = "practical"  # 实践题：考察编码实现能力
    SCENARIO = "scenario"    # 场景题：考察问题解决和适应能力
    BEHAVIORAL = "behavioral"  # 行为题：考察软技能和价值观


@dataclass
class InterviewQuestion:
    """面试问题数据结构
    
    用于存储和组织面试问题及其答案
    """
    question: str
    question_type: InterviewQuestionType
    difficulty: str  # easy, medium, hard
    key_points: List[str]
    answer_framework: str
    sample_answer: str


class InterviewPrepSystem:
    """面试准备系统
    
    帮助AI Agent工程师系统性地准备面试
    """
    
    def __init__(self):
        self.questions: List[InterviewQuestion] = []
        self._init_question_bank()
    
    def _init_question_bank(self):
        """初始化问题库"""
        # 概念题示例
        self.questions.extend([
            InterviewQuestion(
                question="请解释LangGraph中的StateGraph是什么？",
                question_type=InterviewQuestionType.CONCEPT,
                difficulty="medium",
                key_points=[
                    "状态机的定义和作用",
                    "节点和边的概念",
                    "状态转换机制",
                    "条件边和并行执行"
                ],
                answer_framework="定义 + 核心概念 + 工作原理 + 示例",
                sample_answer="""StateGraph是LangGraph中用于构建有状态工作流的核心组件。

核心概念：
1. 节点(Node)：代表图中的一个处理步骤
2. 边(Edge)：定义节点之间的连接关系
3. 状态(State)：贯穿整个工作流的数据

工作原理：
- 从起始节点开始
- 根据边定义的条件决定下一个节点
- 状态在节点间传递和更新
- 支持条件分支和并行执行

示例代码：
```python
from langgraph.graph import StateGraph

graph = StateGraph(Dict)
graph.add_node("process", process_fn)
graph.add_edge("__start__", "process")
graph.add_edge("process", "__end__")
```"""
            ),
            InterviewQuestion(
                question="DeerFlow中的沙箱安全机制是如何设计的？",
                question_type=InterviewQuestionType.CONCEPT,
                difficulty="hard",
                key_points=[
                    "沙箱隔离原理",
                    "虚拟路径映射",
                    "资源限制机制",
                    "安全策略执行"
                ],
                answer_framework="背景 + 设计目标 + 架构组件 + 安全机制",
                sample_answer="""DeerFlow的沙箱安全机制是保障Agent系统安全执行的核心设计。

设计目标：
1. 防止恶意代码执行
2. 限制资源使用
3. 隔离文件系统访问
4. 控制网络访问

架构组件：
1. Sandbox抽象层：统一的沙箱接口
2. VirtualPathMapper：虚拟路径到实际路径的映射
3. ResourceLimiter：CPU、内存、执行时间限制
4. SecurityPolicy：安全策略执行器

安全机制：
- 白名单机制：只允许预定义的操作
- 路径验证：防止路径遍历攻击
- 资源配额：防止资源耗尽
- 执行超时：防止无限循环"""
            ),
        ])
        
        # 设计题示例
        self.questions.extend([
            InterviewQuestion(
                question="如何设计一个支持多租户的Agent平台？",
                question_type=InterviewQuestionType.DESIGN,
                difficulty="hard",
                key_points=[
                    "租户隔离策略",
                    "资源分配机制",
                    "数据隔离方案",
                    "认证授权体系"
                ],
                answer_framework="需求分析 + 架构设计 + 关键决策 + 权衡分析",
                sample_answer="""多租户Agent平台设计方案：

1. 需求分析
   - 功能需求：Agent创建、配置、执行、监控
   - 非功能需求：隔离性、安全性、性能、成本

2. 架构设计
   - 租户隔离层：TenantContext、Tenantaware组件
   - 数据层：Schema隔离 vs 数据库隔离
   - 计算层：共享池 vs 独享池
   - 网络层：VPC隔离 vs 应用层隔离

3. 关键决策
   - 隔离级别：严格隔离 vs 成本优先
   - 定价策略：按量 vs 按订阅
   - 资源配额：固定 vs 弹性

4. 权衡分析
   - 隔离 vs 成本：完全隔离成本高
   - 灵活 vs 安全：租户自定义带来风险
   - 性能 vs 隔离：共享资源有噪声问题"""
            ),
            InterviewQuestion(
                question="设计一个高可用的Agent任务调度系统",
                question_type=InterviewQuestionType.DESIGN,
                difficulty="hard",
                key_points=[
                    "任务队列设计",
                    "负载均衡策略",
                    "故障转移机制",
                    "状态管理方案"
                ],
                answer_framework="目标确定 + 架构设计 + 容错设计 + 扩展性",
                sample_answer="""高可用Agent任务调度系统设计：

1. 设计目标
   - 可用性：99.9%以上
   - 吞吐量：支持万级并发
   - 延迟：P99 < 1秒

2. 核心架构
   - API网关：统一入口、限流、路由
   - 调度器：任务分发、优先级队列
   - 执行器池：Worker管理、任务执行
   - 状态存储：Redis/数据库持久化

3. 容错设计
   - 多副本：主从复制
   - 健康检查：心跳检测
   - 自动故障转移：Leader Election
   - 任务重试：指数退避策略

4. 扩展性
   - 水平扩展：增加Worker节点
   - 分片：任务ID哈希分片
   - 异步处理：消息队列解耦"""
            ),
        ])
        
        # 实践题示例
        self.questions.extend([
            InterviewQuestion(
                question="实现一个带重试机制的Agent执行器",
                question_type=InterviewQuestionType.PRACTICAL,
                difficulty="medium",
                key_points=[
                    "重试策略设计",
                    "退避算法实现",
                    "状态追踪",
                    "异常处理"
                ],
                answer_framework="思路分析 + 代码实现 + 边界处理 + 测试用例",
                sample_answer="""带重试机制的Agent执行器实现：

```python
import asyncio
from typing import Any, Callable
from functools import wraps

class RetryExecutor:
    '''带重试机制的执行器'''
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute_with_retry(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        '''执行函数并支持重试'''
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        raise last_exception
```

关键点：
1. 指数退避：避免频繁重试
2. 最大重试次数：防止无限重试
3. 异常分类：区分可重试和不可重试异常
4. 日志记录：追踪重试历史"""
            ),
        ])
        
        # 场景题示例
        self.questions.extend([
            InterviewQuestion(
                question="Agent在处理长文本时遇到OOM问题，如何分析和解决？",
                question_type=InterviewQuestionType.SCENARIO,
                difficulty="hard",
                key_points=[
                    "问题定位",
                    "原因分析",
                    "解决方案",
                    "预防措施"
                ],
                answer_framework="问题确认 + 根因分析 + 解决方案 + 验证",
                sample_answer="""Agent长文本OOM问题分析：

1. 问题确认
   - 确认OOM发生位置：LLM调用？后处理？存储？
   - 查看错误堆栈和内存监控

2. 根因分析
   - 输入截断不当：未限制输入长度
   - 中间结果累积：对话历史全部保存
   - 向量数据库膨胀：嵌入向量未清理
   - 并发请求过多：内存峰值叠加

3. 解决方案
   - 输入长度限制：设置max_tokens
   - 会话摘要：保留关键信息
   - 流式处理：边读边处理
   - 内存优化：使用生成器代替列表
   - 资源隔离：限制并发数

4. 预防措施
   - 内存监控告警
   - 资源限制配置
   - 定期内存分析"""
            ),
        ])
    
    def get_questions_by_type(
        self, 
        qtype: InterviewQuestionType
    ) -> List[InterviewQuestion]:
        """获取指定类型的面试问题"""
        return [q for q in self.questions if q.question_type == qtype]
    
    def prepare_answer(
        self, 
        question: InterviewQuestion
    ) -> str:
        """准备问题的回答"""
        return f"""【问题类型】{question.question_type.value}
【难度】{question.difficulty}

【关键要点】
{chr(10).join(f"- {point}" for point in question.key_points)}

【回答框架】
{question.answer_framework}

【示例回答】
{question.sample_answer}"""


# ============================================================================
# 第二部分：简历优化工具
# ============================================================================

class ResumeOptimizer:
    """简历优化工具
    
    帮助AI Agent工程师优化简历，突出核心竞争力
    """
    
    # AI Agent工程师关键技能关键词
    KEY_SKILLS = {
        "编程语言": ["Python", "TypeScript", "Go", "Rust"],
        "框架工具": [
            "LangChain", "LangGraph", "DeerFlow", 
            "FastAPI", "FastGPT", "LangChain"
        ],
        "AI技术": [
            "LLM", "Prompt Engineering", "RAG",
            "向量数据库", "Embedding", "模型微调"
        ],
        "云原生": [
            "Docker", "Kubernetes", "AWS", "GCP",
            "Prometheus", "Grafana"
        ],
        "工程能力": [
            "系统设计", "性能优化", "高并发",
            "微服务", "CI/CD", "测试"
        ]
    }
    
    @staticmethod
    def analyze_resume(content: str) -> Dict[str, Any]:
        """分析简历内容
        
        Args:
            content: 简历文本内容
            
        Returns:
            分析结果字典
        """
        analysis = {
            "skills_found": [],
            "skills_missing": [],
            "project_count": 0,
            "quantified_results": 0,
            "suggestions": []
        }
        
        # 检测关键技能
        for category, skills in ResumeOptimizer.KEY_SKILLS.items():
            for skill in skills:
                if skill.lower() in content.lower():
                    analysis["skills_found"].append(skill)
        
        # 建议添加的技能
        all_known_skills = set()
        for skills in ResumeOptimizer.KEY_SKILLS.values():
            all_known_skills.update(skills)
        
        analysis["skills_missing"] = list(
            all_known_skills - set(analysis["skills_found"])
        )
        
        # 统计项目数量（关键词检测）
        project_keywords = ["项目", "实现", "开发", "设计", "构建"]
        for keyword in project_keywords:
            analysis["project_count"] += content.count(keyword)
        
        # 量化成果统计
        quant_keywords = ["%", "倍", "提升", "增长", "减少", "万", "千"]
        for keyword in quant_keywords:
            analysis["quantified_results"] += content.count(keyword)
        
        # 生成建议
        if len(analysis["skills_found"]) < 10:
            analysis["suggestions"].append(
                "建议增加更多技术栈关键词"
            )
        if analysis["quantified_results"] < 3:
            analysis["suggestions"].append(
                "建议在项目描述中添加更多量化指标"
            )
        
        return analysis
    
    @staticmethod
    def generate_project_description(
        project_name: str,
        tech_stack: List[str],
        achievements: List[str]
    ) -> str:
        """生成项目描述
        
        使用STAR原则生成专业的项目描述
        """
        tech_str = " + ".join(tech_stack)
        
        lines = [
            f"**{project_name}**",
            f"- 技术栈：{tech_str}",
            "",
            "**成果亮点：**"
        ]
        
        for achievement in achievements:
            lines.append(f"- {achievement}")
        
        return "\n".join(lines)


# ============================================================================
# 第三部分：系统设计面试框架
# ============================================================================

class SystemDesignFramework:
    """系统设计面试四步法框架
    
    帮助结构化地回答系统设计问题
    """
    
    @staticmethod
    def step1_clarify_requirements(
        features: List[str],
        constraints: Dict[str, Any]
    ) -> str:
        """第一步：需求澄清
        
        明确功能需求和非功能需求
        """
        output = ["## 第一步：需求澄清\n"]
        
        output.append("### 功能需求")
        for i, feature in enumerate(features, 1):
            output.append(f"{i}. {feature}")
        
        output.append("\n### 非功能需求")
        constraints_formatted = {
            "性能": constraints.get("performance", "待定"),
            "可用性": constraints.get("availability", "待定"),
            "安全性": constraints.get("security", "待定"),
            "扩展性": constraints.get("scalability", "待定"),
        }
        for key, value in constraints_formatted.items():
            output.append(f"- {key}: {value}")
        
        return "\n".join(output)
    
    @staticmethod
    def step2_high_level_design(
        components: List[Dict[str, str]]
    ) -> str:
        """第二步：高层设计
        
        定义系统组件和数据流
        """
        output = ["## 第二步：高层设计\n"]
        
        output.append("### 系统架构")
        for comp in components:
            output.append(
                f"- **{comp['name']}**: {comp['description']}"
            )
        
        output.append("\n### 数据流")
        output.append("1. 请求 → API网关")
        output.append("2. 网关 → 负载均衡")
        output.append("3. 负载均衡 → 服务集群")
        output.append("4. 服务 → 数据存储")
        
        return "\n".join(output)
    
    @staticmethod
    def step3_deep_dive(
        key_technologies: Dict[str, str],
        failure_scenarios: List[str]
    ) -> str:
        """第三步：深度设计
        
        关键技术选型和容错设计
        """
        output = ["## 第三步：深度设计\n"]
        
        output.append("### 关键技术选型")
        for tech, reason in key_technologies.items():
            output.append(f"- **{tech}**: {reason}")
        
        output.append("\n### 容错设计")
        for scenario in failure_scenarios:
            output.append(f"- {scenario}")
        
        return "\n".join(output)
    
    @staticmethod
    def step4_wrap_up(
        tradeoffs: List[str],
        improvements: List[str]
    ) -> str:
        """第四步：总结优化
        
        权衡分析和改进方向
        """
        output = ["## 第四步：总结优化\n"]
        
        output.append("### 权衡分析")
        for tradeoff in tradeoffs:
            output.append(f"- {tradeoff}")
        
        output.append("\n### 改进方向")
        for improvement in improvements:
            output.append(f"- {improvement}")
        
        return "\n".join(output)
    
    @classmethod
    def full_design(
        cls,
        features: List[str],
        constraints: Dict[str, Any],
        components: List[Dict[str, str]],
        key_technologies: Dict[str, str],
        failure_scenarios: List[str],
        tradeoffs: List[str],
        improvements: List[str]
    ) -> str:
        """完整设计流程"""
        return "\n\n".join([
            cls.step1_clarify_requirements(features, constraints),
            cls.step2_high_level_design(components),
            cls.step3_deep_dive(key_technologies, failure_scenarios),
            cls.step4_wrap_up(tradeoffs, improvements)
        ])


# ============================================================================
# 第四部分：行为面试STAR准备
# ============================================================================

class BehavioralPrep:
    """行为面试准备工具
    
    帮助准备STAR格式的行为面试答案
    """
    
    COMMON_TOPICS = [
        "团队合作冲突",
        "技术难题解决",
        "项目失败经历",
        "领导力展示",
        "创新思维体现",
        "压力下工作",
        "快速学习",
        "错误和反思"
    ]
    
    @staticmethod
    def star_template(
        situation: str,
        task: str,
        action: List[str],
        result: str
    ) -> str:
        """STAR回答模板
        
        Args:
            situation: 情境背景
            task: 任务和目标
            action: 采取的行动（列表，可包含多步）
            result: 结果和收获
            
        Returns:
            STAR格式的回答
        """
        sections = [
            "**S (情境)**",
            situation,
            "",
            "**T (任务)**",
            task,
            "",
            "**A (行动)**",
        ]
        
        for i, action_step in enumerate(action, 1):
            sections.append(f"{i}. {action_step}")
        
        sections.extend([
            "",
            "**R (结果)**",
            result
        ])
        
        return "\n".join(sections)
    
    @staticmethod
    def prepare_story(
        topic: str,
        story_data: Dict[str, Any]
    ) -> str:
        """准备完整的故事
        
        Args:
            topic: 故事主题
            story_data: 包含situation, task, action, result的字典
            
        Returns:
            完整的STAR故事
        """
        return BehavioralPrep.star_template(
            situation=story_data.get("situation", ""),
            task=story_data.get("task", ""),
            action=story_data.get("action", []),
            result=story_data.get("result", "")
        )


# ============================================================================
# 第五部分：面试评估模拟
# ============================================================================

class InterviewSimulator:
    """面试模拟器
    
    模拟面试过程，提供反馈
    """
    
    def __init__(self):
        self.eval_criteria = {
            "技术深度": {
                "权重": 0.3,
                "描述": "对技术概念的理解深度"
            },
            "系统思维": {
                "权重": 0.25,
                "描述": "系统设计和架构能力"
            },
            "沟通能力": {
                "权重": 0.2,
                "描述": "表达清晰度和逻辑性"
            },
            "问题解决": {
                "权重": 0.15,
                "描述": "分析和解决问题能力"
            },
            "文化匹配": {
                "权重": 0.1,
                "描述": "价值观和团队匹配度"
            }
        }
    
    def evaluate_answer(
        self,
        answer: str,
        key_points: List[str]
    ) -> Dict[str, Any]:
        """评估回答质量
        
        Args:
            answer: 回答内容
            key_points: 关键要点列表
            
        Returns:
            评估结果
        """
        score = 0
        feedback = []
        
        # 检查关键要点覆盖
        covered_points = []
        for point in key_points:
            if any(keyword in answer.lower() for keyword in point.lower().split()):
                covered_points.append(point)
                score += 20
        
        # 长度评估
        word_count = len(answer.split())
        if 100 <= word_count <= 500:
            score += 10
            feedback.append("回答长度适中")
        elif word_count < 100:
            feedback.append("回答过于简短，建议扩展")
        else:
            feedback.append("回答过于冗长，建议精简")
        
        # 结构评估
        if any(marker in answer for marker in ["1.", "2.", "•", "-", "**"]):
            score += 10
            feedback.append("结构清晰")
        
        return {
            "total_score": min(score, 100),
            "key_points_covered": len(covered_points),
            "total_key_points": len(key_points),
            "feedback": feedback
        }


# ============================================================================
# 测试代码
# ============================================================================

def test_interview_prep():
    """测试面试准备系统"""
    print("=== 测试面试准备系统 ===\n")
    
    # 初始化系统
    prep_system = InterviewPrepSystem()
    
    # 测试获取概念题
    concept_questions = prep_system.get_questions_by_type(
        InterviewQuestionType.CONCEPT
    )
    print(f"概念题数量: {len(concept_questions)}")
    
    # 测试准备答案
    if concept_questions:
        answer = prep_system.prepare_answer(concept_questions[0])
        print(f"\n示例答案预览:\n{answer[:200]}...")
    
    print("\n--- 测试简历分析 ---")
    sample_resume = """
    Python开发工程师
    技能: LangChain, FastAPI, Docker
    项目: 智能问答系统，使用RAG技术，日活1000+
    """
    analysis = ResumeOptimizer.analyze_resume(sample_resume)
    print(f"发现技能: {analysis['skills_found']}")
    print(f"缺失技能: {analysis['skills_missing'][:5]}")
    
    print("\n--- 测试系统设计框架 ---")
    design = SystemDesignFramework.full_design(
        features=["用户认证", "任务创建", "任务执行"],
        constraints={"performance": "100 QPS", "availability": "99.9%"},
        components=[
            {"name": "API网关", "description": "请求入口"},
            {"name": "任务服务", "description": "任务管理"}
        ],
        key_technologies={"Redis": "缓存和队列"},
        failure_scenarios=["服务宕机", "网络分区"],
        tradeoffs=["一致性 vs 可用性"],
        improvements=["增加监控", "优化缓存"]
    )
    print(design)
    
    print("\n--- 测试行为面试 ---")
    story = BehavioralPrep.star_template(
        situation="在项目开发中遇到技术难题",
        task="需要在 deadline 前解决性能问题",
        action=["分析性能瓶颈", "优化数据库查询", "增加缓存"],
        result="性能提升 50%，按时交付"
    )
    print(story)
    
    print("\n--- 测试面试评估 ---")
    simulator = InterviewSimulator()
    sample_answer = """
    StateGraph 是 LangGraph 的核心组件，用于构建有状态的工作流。
    它包含节点（Node）和边（Edge），节点是处理步骤，边定义转换关系。
    支持条件分支，可以根据状态决定下一个执行的节点。
    """
    result = simulator.evaluate_answer(
        sample_answer,
        ["状态机", "节点", "边", "条件分支"]
    )
    print(f"评估得分: {result['total_score']}")
    print(f"反馈: {result['feedback']}")


if __name__ == "__main__":
    test_interview_prep()
