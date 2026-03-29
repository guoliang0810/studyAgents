#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
职业发展路径 - 演示代码

本模块展示AI Agent工程师的职业发展路径规划工具。
包含：技能发展矩阵、职业规划框架、学习资源推荐、网络建设策略。

作者: DeerFlow架构师训练营
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json


# ============================================================================
# 第一部分：职业发展路径模型
# ============================================================================

class CareerLevel(Enum):
    """职业发展级别
    
    定义AI Agent工程师的职业发展阶段
    """
    JUNIOR = "junior"           # 初级工程师 (0-2年)
    MIDDLE = "middle"           # 中级工程师 (2-4年)
    SENIOR = "senior"           # 高级工程师 (4-6年)
    ARCHITECT = "architect"     # 架构师 (6-10年)
    EXPERT = "expert"           # 技术专家/管理者 (10年+)


@dataclass
class CareerStage:
    """职业发展阶段数据
    
    描述每个职业阶段的能力要求和特征
    """
    level: CareerLevel
    title: str
    years_experience: str
    salary_range: str
    core_abilities: List[str]
    typical_positions: List[str]
    key_milestones: List[str]


class CareerPathModel:
    """职业发展路径模型
    
    提供AI Agent工程师五级发展路径
    """
    
    def __init__(self):
        self.stages: Dict[CareerLevel, CareerStage] = {}
        self._init_career_stages()
    
    def _init_career_stages(self):
        """初始化职业发展阶段"""
        self.stages = {
            CareerLevel.JUNIOR: CareerStage(
                level=CareerLevel.JUNIOR,
                title="初级AI Agent工程师",
                years_experience="0-2年",
                salary_range="20-35万/年（一线城市）",
                core_abilities=[
                    "掌握DeerFlow基础使用",
                    "完成简单Agent开发",
                    "理解LangGraph状态机",
                    "掌握基础Python异步编程"
                ],
                typical_positions=[
                    "AI应用开发工程师",
                    "LLM应用工程师"
                ],
                key_milestones=[
                    "独立完成第一个Agent项目",
                    "掌握核心框架原理",
                    "建立代码规范意识"
                ]
            ),
            CareerLevel.MIDDLE: CareerStage(
                level=CareerLevel.MIDDLE,
                title="中级AI Agent工程师",
                years_experience="2-4年",
                salary_range="35-60万/年（一线城市）",
                core_abilities=[
                    "独立设计Agent系统",
                    "解决复杂业务问题",
                    "性能优化能力",
                    "基础架构设计"
                ],
                typical_positions=[
                    "AI Agent开发工程师",
                    "智能系统工程师"
                ],
                key_milestones=[
                    "主导中型Agent项目",
                    "建立技术影响力",
                    "培养新人能力"
                ]
            ),
            CareerLevel.SENIOR: CareerStage(
                level=CareerLevel.SENIOR,
                title="高级AI Agent工程师",
                years_experience="4-6年",
                salary_range="60-100万/年（一线城市）",
                core_abilities=[
                    "设计大规模Agent系统",
                    "领导技术项目",
                    "架构决策能力",
                    "团队技术指导"
                ],
                typical_positions=[
                    "高级AI工程师",
                    "技术负责人",
                    "架构师"
                ],
                key_milestones=[
                    "主导大型Agent平台",
                    "建立技术团队",
                    "推动技术创新"
                ]
            ),
            CareerLevel.ARCHITECT: CareerStage(
                level=CareerLevel.ARCHITECT,
                title="AI Agent架构师",
                years_experience="6-10年",
                salary_range="100-200万/年（一线城市）",
                core_abilities=[
                    "设计企业级Agent平台",
                    "制定技术战略",
                    "跨团队协调",
                    "行业技术洞察"
                ],
                typical_positions=[
                    "AI架构师",
                    "技术专家",
                    "首席工程师"
                ],
                key_milestones=[
                    "主导企业级Agent平台建设",
                    "建立行业技术影响力",
                    "培养技术团队"
                ]
            ),
            CareerLevel.EXPERT: CareerStage(
                level=CareerLevel.EXPERT,
                title="AI技术专家/管理者",
                years_experience="10年以上",
                salary_range="200万+/年（一线城市）",
                core_abilities=[
                    "引领技术方向",
                    "管理技术团队",
                    "影响行业发展",
                    "战略规划能力"
                ],
                typical_positions=[
                    "CTO",
                    "技术副总裁",
                    "技术合伙人",
                    "行业专家"
                ],
                key_milestones=[
                    "成为行业技术领袖",
                    "推动行业标准建立",
                    "创造商业价值"
                ]
            )
        }
    
    def get_stage(self, level: CareerLevel) -> CareerStage:
        """获取指定级别的职业阶段信息"""
        return self.stages.get(level)
    
    def get_all_stages(self) -> List[CareerStage]:
        """获取所有职业阶段"""
        return list(self.stages.values())
    
    def get_next_stage(self, current: CareerLevel) -> Optional[CareerStage]:
        """获取下一阶段"""
        stages_order = [
            CareerLevel.JUNIOR,
            CareerLevel.MIDDLE,
            CareerLevel.SENIOR,
            CareerLevel.ARCHITECT,
            CareerLevel.EXPERT
        ]
        
        try:
            current_idx = stages_order.index(current)
            if current_idx < len(stages_order) - 1:
                return self.stages[stages_order[current_idx + 1]]
        except ValueError:
            pass
        
        return None


# ============================================================================
# 第二部分：技能发展矩阵
# ============================================================================

class SkillMatrix:
    """技能发展矩阵
    
    定义技术技能和软技能的发展维度
    """
    
    TECHNICAL_SKILLS = {
        "基础技能": [
            "Python", "异步编程", "数据结构", "算法",
            "设计模式", "代码重构"
        ],
        "框架技能": [
            "LangChain", "LangGraph", "DeerFlow",
            "FastAPI", "Django", "Flask"
        ],
        "AI技术": [
            "LLM应用开发", "Prompt工程", "RAG",
            "向量数据库", "Embedding", "模型微调"
        ],
        "工程技能": [
            "单元测试", "集成测试", "CI/CD",
            "Docker", "Kubernetes", "监控"
        ],
        "架构技能": [
            "系统设计", "分布式系统", "微服务",
            "云原生", "高并发", "性能优化"
        ]
    }
    
    SOFT_SKILLS = {
        "沟通能力": [
            "技术表达", "文档写作", "演示展示",
            "跨团队沟通", "会议主持"
        ],
        "协作能力": [
            "团队合作", "代码审查", "知识分享",
            "冲突解决", "跨部门协作"
        ],
        "问题解决": [
            "分析思维", "创新思维", "决策能力",
            "风险管理", "系统思考"
        ],
        "领导能力": [
            "项目管理", "团队指导", "技术规划",
            "影响力建设", "人才培养"
        ],
        "学习能力": [
            "自主学习", "知识迁移", "趋势把握",
            "适应变化", "快速上手"
        ]
    }
    
    @classmethod
    def get_skill_level(
        cls,
        skill: str,
        current_skills: List[str]
    ) -> str:
        """评估技能等级
        
        根据当前技能列表评估某项技能的掌握程度
        """
        if skill in current_skills:
            return "熟练掌握"
        
        skill_category = cls._find_skill_category(skill)
        if skill_category:
            related_skills = cls.TECHNICAL_SKILLS.get(skill_category, [])
            if any(s in current_skills for s in related_skills):
                return "了解"
        
        return "未掌握"
    
    @classmethod
    def _find_skill_category(cls, skill: str) -> Optional[str]:
        """查找技能所属类别"""
        for category, skills in cls.TECHNICAL_SKILLS.items():
            if skill in skills:
                return category
        return None
    
    @classmethod
    def suggest_learning_path(
        cls,
        current_skills: List[str],
        target_level: CareerLevel
    ) -> List[str]:
        """建议学习路径
        
        根据当前技能和目标级别推荐学习路线
        """
        suggestions = []
        
        if target_level == CareerLevel.JUNIOR:
            suggestions.extend(cls.TECHNICAL_SKILLS["基础技能"][:4])
            suggestions.extend(cls.TECHNICAL_SKILLS["框架技能"][:2])
        
        elif target_level == CareerLevel.MIDDLE:
            suggestions.extend(cls.TECHNICAL_SKILLS["框架技能"])
            suggestions.extend(cls.TECHNICAL_SKILLS["AI技术"][:3])
            suggestions.extend(cls.TECHNICAL_SKILLS["工程技能"][:3])
        
        elif target_level == CareerLevel.SENIOR:
            suggestions.extend(cls.TECHNICAL_SKILLS["AI技术"])
            suggestions.extend(cls.TECHNICAL_SKILLS["工程技能"])
            suggestions.extend(cls.TECHNICAL_SKILLS["架构技能"][:3])
        
        elif target_level in [CareerLevel.ARCHITECT, CareerLevel.EXPERT]:
            suggestions.extend(cls.TECHNICAL_SKILLS["架构技能"])
            suggestions.extend(list(cls.SOFT_SKILLS["领导能力"]))
        
        return suggestions


# ============================================================================
# 第三部分：职业规划工具
# ============================================================================

@dataclass
class CareerGoal:
    """职业目标数据
    
    使用SMART原则定义职业目标
    """
    goal: str
    timeline: str
    metrics: str
    actions: List[str]


class CareerPlanner:
    """职业规划工具
    
    帮助制定和管理职业发展规划
    """
    
    def __init__(self, name: str):
        self.name = name
        self.goals: List[CareerGoal] = []
        self.learning_resources: List[Dict[str, str]] = []
        self.network_contacts: List[Dict[str, str]] = []
    
    def add_goal(
        self,
        goal: str,
        timeline: str,
        metrics: str,
        actions: List[str]
    ):
        """添加职业目标"""
        self.goals.append(CareerGoal(goal, timeline, metrics, actions))
    
    def add_learning_resource(
        self,
        name: str,
        url: str,
        category: str
    ):
        """添加学习资源"""
        self.learning_resources.append({
            "name": name,
            "url": url,
            "category": category
        })
    
    def add_network_contact(
        self,
        name: str,
        company: str,
        role: str,
        relationship: str
    ):
        """添加职业网络联系人"""
        self.network_contacts.append({
            "name": name,
            "company": company,
            "role": role,
            "relationship": relationship
        })
    
    def generate_plan(self) -> str:
        """生成职业发展规划"""
        output = [f"# {self.name} 职业发展规划\n"]
        
        output.append("## 职业目标")
        for i, goal in enumerate(self.goals, 1):
            output.append(f"\n### 目标 {i}")
            output.append(f"- **目标**: {goal.goal}")
            output.append(f"- **时间线**: {goal.timeline}")
            output.append(f"- **衡量指标**: {goal.metrics}")
            output.append("- **行动计划**:")
            for action in goal.actions:
                output.append(f"  - {action}")
        
        output.append("\n## 学习资源")
        for resource in self.learning_resources:
            output.append(
                f"- [{resource['name']}]({resource['url']}) "
                f"({resource['category']})"
            )
        
        output.append("\n## 职业网络")
        for contact in self.network_contacts:
            output.append(
                f"- {contact['name']} - {contact['role']} @ "
                f"{contact['company']} ({contact['relationship']})"
            )
        
        return "\n".join(output)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "goals": [
                {
                    "goal": g.goal,
                    "timeline": g.timeline,
                    "metrics": g.metrics,
                    "actions": g.actions
                }
                for g in self.goals
            ],
            "learning_resources": self.learning_resources,
            "network_contacts": self.network_contacts
        }


# ============================================================================
# 第四部分：学习资源推荐
# ============================================================================

class LearningResources:
    """学习资源推荐
    
    提供持续学习的资源列表
    """
    
    PLATFORMS = {
        "在线课程": [
            {"name": "Coursera", "url": "https://www.coursera.org"},
            {"name": "Udacity", "url": "https://www.udacity.com"},
            {"name": "edX", "url": "https://www.edx.org"},
            {"name": "极客时间", "url": "https://time.geekbang.org"}
        ],
        "技术社区": [
            {"name": "DeerFlow Discord", "url": "https://discord.gg/deerflow"},
            {"name": "LangChain社区", "url": "https://discuss.langchain.com"},
            {"name": "Reddit ML", "url": "https://reddit.com/r/MachineLearning"},
            {"name": "知乎AI", "url": "https://www.zhihu.com/topic/人工智能"}
        ],
        "技术博客": [
            {"name": "OpenAI Blog", "url": "https://openai.com/blog"},
            {"name": "Google AI", "url": "https://ai.googleblog.com"},
            {"name": "机器之心", "url": "https://jiqizhixin.com"},
            {"name": "AI科技评论", "url": "https://aitechtalk.com"}
        ],
        "开源项目": [
            {"name": "DeerFlow", "url": "https://github.com/bytedance/deer-flow"},
            {"name": "LangChain", "url": "https://github.com/langchain-ai/langchain"},
            {"name": "LangGraph", "url": "https://github.com/langchain-ai/langgraph"}
        ]
    }
    
    @classmethod
    def get_by_category(cls, category: str) -> List[Dict[str, str]]:
        """获取指定类别的资源"""
        return cls.PLATFORMS.get(category, [])
    
    @classmethod
    def get_all_resources(cls) -> Dict[str, List[Dict[str, str]]]:
        """获取所有资源"""
        return cls.PLATFORMS


# ============================================================================
# 第五部分：网络建设策略
# ============================================================================

class NetworkBuilder:
    """职业网络建设
    
    提供线上和线下网络建设策略
    """
    
    ONLINE_STRATEGIES = [
        ("LinkedIn优化", "完整资料、技能认证、项目展示"),
        ("GitHub建设", "高质量项目、活跃贡献、完整文档"),
        ("技术博客", "分享知识、展示思考、建立影响力"),
        ("社交媒体", "专业形象、有价值分享、积极互动")
    ]
    
    OFFLINE_STRATEGIES = [
        ("技术会议", "主动参与、积极提问、建立联系"),
        ("行业活动", "拓展视野、寻找机会、建立关系"),
        ("社区活动", "贡献社区、建立声誉、获得认可"),
        ("导师关系", "寻找导师、建立指导、学习经验")
    ]
    
    @classmethod
    def get_online_strategies(cls) -> List[tuple]:
        """获取线上网络建设策略"""
        return cls.ONLINE_STRATEGIES
    
    @classmethod
    def get_offline_strategies(cls) -> List[tuple]:
        """获取线下网络建设策略"""
        return cls.OFFLINE_STRATEGIES
    
    @classmethod
    def generate_linkedin_profile_tips(cls) -> List[str]:
        """生成LinkedIn资料优化建议"""
        return [
            "使用专业头像",
            "完善个人简介，突出AI Agent技能",
            "列出所有相关项目经验",
            "获取技能认证",
            "发布技术内容",
            "积极参与讨论",
            "连接行业人士",
            "定期更新动态"
        ]
    
    @classmethod
    def generate_github_tips(cls) -> List[str]:
        """生成GitHub优化建议"""
        return [
            "创建高质量的开源项目",
            "完善README文档",
            "添加详细的代码注释",
            "提供使用示例",
            "积极响应Issues",
            "参与其他开源项目",
            "维护项目更新日志",
            "获取Star和Fork"
        ]


# ============================================================================
# 第六部分：30天学习成长总结
# ============================================================================

class LearningSummary:
    """学习成长总结
    
    生成30天学习的成长总结
    """
    
    WEEKS_SUMMARY = {
        "第一周": {
            "topic": "Agent架构基础",
            "days": "Day 1-7",
            "achievements": [
                "掌握LangGraph状态机",
                "理解ThreadState管理",
                "学会中间件模式",
                "掌握工具系统"
            ]
        },
        "第二周": {
            "topic": "沙箱与子代理系统",
            "days": "Day 8-14",
            "achievements": [
                "理解沙箱安全设计",
                "掌握虚拟路径映射",
                "学会子代理执行引擎",
                "实现内存系统"
            ]
        },
        "第三周": {
            "topic": "配置与集成系统",
            "days": "Day 15-21",
            "achievements": [
                "掌握配置系统架构",
                "理解模型工厂",
                "学会MCP集成",
                "建立测试体系"
            ]
        },
        "第四周": {
            "topic": "生产部署与优化",
            "days": "Day 22-30",
            "achievements": [
                "掌握性能优化",
                "理解安全架构",
                "学会部署扩展",
                "实现高可用设计"
            ]
        }
    }
    
    CORE_SKILLS = [
        "Python异步编程能力",
        "LangChain/LangGraph深度使用",
        "Agent系统设计能力",
        "中间件架构理解",
        "安全沙箱设计",
        "云原生部署能力"
    ]
    
    @classmethod
    def generate_summary(cls) -> str:
        """生成学习成长总结"""
        output = ["# 30天学习成长总结\n"]
        
        output.append("## 各周学习成果")
        for week, details in cls.WEEKS_SUMMARY.items():
            output.append(f"\n### {week}: {details['topic']} ({details['days']})")
            for achievement in details['achievements']:
                output.append(f"- ✅ {achievement}")
        
        output.append("\n## 核心能力提升")
        for skill in cls.CORE_SKILLS:
            output.append(f"- • {skill}")
        
        output.append("\n## 职业准备完成")
        output.append("- 完整毕业项目作品")
        output.append("- 面试准备和技巧")
        output.append("- 职业发展规划")
        output.append("- 持续学习计划")
        
        return "\n".join(output)


# ============================================================================
# 测试代码
# ============================================================================

def test_career_path():
    """测试职业发展路径"""
    print("=== 测试职业发展路径 ===\n")
    
    model = CareerPathModel()
    
    print("职业发展五级路径:")
    for stage in model.get_all_stages():
        print(f"\n【{stage.title}】({stage.years_experience})")
        print(f"  薪资: {stage.salary_range}")
        print(f"  核心能力: {', '.join(stage.core_abilities[:2])}")
        print(f"  典型岗位: {', '.join(stage.typical_positions)}")
    
    print("\n--- 测试技能矩阵 ---")
    skills = ["Python", "LangChain", "Kubernetes"]
    for skill in skills:
        level = SkillMatrix.get_skill_level(skill, ["Python", "FastAPI"])
        print(f"  {skill}: {level}")
    
    learning_path = SkillMatrix.suggest_learning_path(
        ["Python"],
        CareerLevel.MIDDLE
    )
    print(f"\n中级工程师学习路径: {learning_path[:5]}")
    
    print("\n--- 测试职业规划 ---")
    planner = CareerPlanner("张三")
    planner.add_goal(
        goal="成为高级AI Agent工程师",
        timeline="2年",
        metrics="主导项目3个",
        actions=["深入学习LangGraph", "完成性能优化项目"]
    )
    planner.add_learning_resource(
        "LangChain进阶",
        "https://docs.langchain.com",
        "框架"
    )
    planner.add_network_contact(
        "李四",
        "字节跳动",
        "AI架构师",
        "导师"
    )
    
    plan = planner.generate_plan()
    print(plan)
    
    print("\n--- 测试学习资源 ---")
    resources = LearningResources.get_by_category("在线课程")
    print("在线课程平台:")
    for r in resources:
        print(f"  - {r['name']}: {r['url']}")
    
    print("\n--- 测试网络建设 ---")
    tips = NetworkBuilder.generate_linkedin_profile_tips()
    print("LinkedIn优化建议:")
    for tip in tips[:5]:
        print(f"  - {tip}")
    
    print("\n--- 测试学习成长总结 ---")
    summary = LearningSummary.generate_summary()
    print(summary)


if __name__ == "__main__":
    test_career_path()
