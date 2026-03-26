#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大厂技术选型对比 - 课堂演示代码
Day1 第2节课：大厂技术选型对比分析

本代码演示主流大厂AI Agent技术栈对比：
1. OpenAI: GPTs + Function Calling
2. Google: Vertex AI + Workflows
3. Anthropic: Claude + Tool Use
4. 字节跳动: DeerFlow + 云雀大模型

通过对比分析，理解不同技术栈的设计哲学和适用场景。
"""

import json
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from tabulate import tabulate


# ============================================================================
# 数据模型定义
# ============================================================================


class TechStack(Enum):
    """技术栈枚举"""

    OPENAI = "OpenAI"
    GOOGLE = "Google"
    ANTHROPIC = "Anthropic"
    BYTEDANCE = "字节跳动"


@dataclass
class VendorTechStack:
    """厂商技术栈信息"""

    vendor: TechStack
    core_model: str
    framework: str
    api_style: str
    pricing_model: str
    open_source: bool
    key_strengths: List[str]
    key_weaknesses: List[str]
    best_for: List[str]
    example_use_case: str


@dataclass
class ProjectRequirement:
    """项目需求"""

    project_type: str  # 项目类型: startup, enterprise, research, education
    team_size: str  # 团队规模: solo, small(2-5), medium(5-10), large(10+)
    budget: str  # 预算: low(<$100/m), medium($100-$1000/m), high(>$1000/m)
    timeline: str  # 时间线: urgent(<1m), normal(1-3m), flexible(>3m)
    customization_needs: str  # 定制需求: none, low, medium, high
    production_scale: str  # 生产规模: prototype, small_scale, large_scale


@dataclass
class TechEvaluation:
    """技术评估结果"""

    vendor: TechStack
    score: float  # 0-100
    fit_analysis: str
    recommendation_level: str  # strong_recommend, recommend, consider, avoid
    cost_estimate: Dict[str, Any]
    implementation_complexity: str  # low, medium, high


# ============================================================================
# 厂商技术栈数据
# ============================================================================


def load_vendor_tech_stacks() -> Dict[TechStack, VendorTechStack]:
    """加载厂商技术栈数据"""
    return {
        TechStack.OPENAI: VendorTechStack(
            vendor=TechStack.OPENAI,
            core_model="GPT-4/GPT-4o",
            framework="GPTs + Function Calling",
            api_style="REST API + Chat Completion",
            pricing_model="Token-based (输入/输出分别计费)",
            open_source=False,
            key_strengths=[
                "模型能力最强",
                "开发者生态丰富",
                "文档和教程完善",
                "响应速度快",
                "工具调用功能成熟",
            ],
            key_weaknesses=[
                "闭源，不可定制模型",
                "成本较高（特别是GPT-4）",
                "数据隐私担忧",
                "API调用有速率限制",
                "国内访问不稳定",
            ],
            best_for=[
                "快速原型开发",
                "需要最强模型能力的应用",
                "非数据敏感场景",
                "初创公司MVP",
                "教育和研究项目",
            ],
            example_use_case="智能客服机器人，需要理解复杂意图和上下文",
        ),
        TechStack.GOOGLE: VendorTechStack(
            vendor=TechStack.GOOGLE,
            core_model="Gemini Pro/Ultra",
            framework="Vertex AI + Workflows",
            api_style="Cloud-native API + Workflow orchestration",
            pricing_model="Token-based + 云服务集成",
            open_source=False,
            key_strengths=[
                "与Google云生态深度集成",
                "多模态能力突出（图像、视频）",
                "企业级安全合规",
                "工作流编排工具强大",
                "全球基础设施",
            ],
            key_weaknesses=[
                "学习曲线较陡",
                "文档分散在不同产品中",
                "成本结构复杂",
                "国内访问限制",
                "API变更可能较频繁",
            ],
            best_for=[
                "企业级应用",
                "需要多模态处理的应用",
                "已在Google Cloud上的项目",
                "需要工作流编排的复杂应用",
                "全球部署的应用",
            ],
            example_use_case="电商平台智能客服，需要分析用户上传的产品图片",
        ),
        TechStack.ANTHROPIC: VendorTechStack(
            vendor=TechStack.ANTHROPIC,
            core_model="Claude 3 (Opus, Sonnet, Haiku)",
            framework="Claude + Tool Use",
            api_style="Constitutional AI + Tool Calling",
            pricing_model="Token-based，长上下文优化",
            open_source=False,
            key_strengths=[
                "安全性设计突出（Constitutional AI）",
                "长上下文处理（200K tokens）",
                "工具调用设计优雅",
                "输出质量稳定可靠",
                "对复杂推理任务表现好",
            ],
            key_weaknesses=[
                "生态相对较小",
                "价格较高（特别是Claude 3 Opus）",
                "国内访问支持有限",
                "文档和示例相对较少",
                "API功能相对基础",
            ],
            best_for=[
                "对安全性和合规性要求高的应用",
                "需要处理长文档的应用",
                "法律、金融等专业领域",
                "需要复杂推理的任务",
                "对输出稳定性要求高的场景",
            ],
            example_use_case="法律文档分析助手，需要处理上百页合同文档",
        ),
        TechStack.BYTEDANCE: VendorTechStack(
            vendor=TechStack.BYTEDANCE,
            core_model="云雀大模型（Skylark）",
            framework="DeerFlow 2.0",
            api_style="开源框架 + 可定制部署",
            pricing_model="开源免费 + 云服务可选",
            open_source=True,
            key_strengths=[
                "完全开源，可定制性强",
                "模块化设计，易于扩展",
                "生产就绪的架构",
                "对中文场景优化好",
                "多Agent协作支持完善",
            ],
            key_weaknesses=[
                "生态相对较新",
                "企业级支持需要自建",
                "部署和维护成本",
                "文档和社区相对较小",
                "需要更强的技术能力",
            ],
            best_for=[
                "需要高度定制的应用",
                "对数据隐私和安全要求高",
                "技术能力较强的团队",
                "需要多Agent协作的复杂系统",
                "成本敏感但需要自主可控的项目",
            ],
            example_use_case="企业内部知识管理系统，需要定制工作流和严格数据隔离",
        ),
    }


# ============================================================================
# 技术选型评估引擎
# ============================================================================


class TechSelectionEngine:
    """技术选型评估引擎"""

    def __init__(self):
        self.vendor_stacks = load_vendor_tech_stacks()
        self.weight_factors = {
            "budget": 0.25,
            "timeline": 0.20,
            "customization_needs": 0.20,
            "production_scale": 0.15,
            "team_size": 0.10,
            "project_type": 0.10,
        }

    def evaluate_vendor_for_project(
        self, vendor: TechStack, requirement: ProjectRequirement
    ) -> TechEvaluation:
        """评估厂商对项目的适合度"""
        vendor_info = self.vendor_stacks[vendor]

        # 计算基础分数
        base_score = 70.0  # 起始分数

        # 根据需求调整分数
        adjustments = self._calculate_adjustments(vendor_info, requirement)

        # 应用调整
        final_score = base_score + adjustments
        final_score = max(0, min(100, final_score))  # 限制在0-100之间

        # 确定推荐等级
        recommendation = self._determine_recommendation(final_score)

        # 成本估算
        cost_estimate = self._estimate_cost(vendor_info, requirement)

        # 实施复杂度
        complexity = self._estimate_complexity(vendor_info, requirement)

        # 适合度分析
        fit_analysis = self._generate_fit_analysis(vendor_info, requirement)

        return TechEvaluation(
            vendor=vendor,
            score=final_score,
            fit_analysis=fit_analysis,
            recommendation_level=recommendation,
            cost_estimate=cost_estimate,
            implementation_complexity=complexity,
        )

    def _calculate_adjustments(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> float:
        """计算分数调整"""
        adjustments = 0.0

        # 预算匹配度
        if requirement.budget == "low":
            if vendor.vendor == TechStack.BYTEDANCE:
                adjustments += 15  # 开源免费
            elif vendor.vendor == TechStack.OPENAI and "GPT-3.5" in vendor.core_model:
                adjustments += 10  # GPT-3.5相对便宜
            else:
                adjustments -= 10  # 其他可能较贵
        elif requirement.budget == "high":
            adjustments += 5  # 预算充足，所有方案都可考虑

        # 时间线匹配度
        if requirement.timeline == "urgent":
            if vendor.vendor == TechStack.OPENAI:
                adjustments += 12  # 快速上手
            elif vendor.vendor == TechStack.GOOGLE:
                adjustments += 8  # 成熟平台
            else:
                adjustments -= 5  # 需要更多时间

        # 定制需求匹配度
        if requirement.customization_needs == "high":
            if vendor.vendor == TechStack.BYTEDANCE:
                adjustments += 20  # 开源可定制
            else:
                adjustments -= 15  # 闭源限制定制

        # 生产规模匹配度
        if requirement.production_scale == "large_scale":
            if vendor.vendor == TechStack.GOOGLE:
                adjustments += 10  # 企业级支持
            elif vendor.vendor == TechStack.BYTEDANCE:
                adjustments += 8  # 可自主扩展
            else:
                adjustments += 5  # 其他也支持

        # 团队规模匹配度
        if requirement.team_size == "solo":
            if vendor.vendor == TechStack.OPENAI:
                adjustments += 10  # 文档完善，易于上手
            else:
                adjustments -= 5

        # 项目类型匹配度
        if requirement.project_type == "enterprise":
            if vendor.vendor == TechStack.GOOGLE:
                adjustments += 15  # 企业级特性
            elif vendor.vendor == TechStack.ANTHROPIC:
                adjustments += 10  # 安全性好

        elif requirement.project_type == "research":
            if vendor.vendor == TechStack.BYTEDANCE:
                adjustments += 12  # 开源可研究
            elif vendor.vendor == TechStack.OPENAI:
                adjustments += 8  # 研究社区活跃

        return adjustments

    def _determine_recommendation(self, score: float) -> str:
        """确定推荐等级"""
        if score >= 85:
            return "strong_recommend"
        elif score >= 70:
            return "recommend"
        elif score >= 50:
            return "consider"
        else:
            return "avoid"

    def _estimate_cost(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> Dict[str, Any]:
        """估算成本"""
        base_costs = {
            TechStack.OPENAI: {
                "monthly_low": 50,
                "monthly_medium": 500,
                "monthly_high": 5000,
            },
            TechStack.GOOGLE: {
                "monthly_low": 100,
                "monthly_medium": 800,
                "monthly_high": 8000,
            },
            TechStack.ANTHROPIC: {
                "monthly_low": 80,
                "monthly_medium": 600,
                "monthly_high": 6000,
            },
            TechStack.BYTEDANCE: {
                "monthly_low": 0,
                "monthly_medium": 200,
                "monthly_high": 2000,
            },
        }

        # 根据项目规模调整
        scale_factor = {"prototype": 0.3, "small_scale": 1.0, "large_scale": 5.0}

        base = base_costs[vendor.vendor]
        scale = scale_factor.get(requirement.production_scale, 1.0)

        return {
            "low_estimate": base["monthly_low"] * scale,
            "medium_estimate": base["monthly_medium"] * scale,
            "high_estimate": base["monthly_high"] * scale,
            "cost_drivers": self._identify_cost_drivers(vendor, requirement),
            "cost_saving_tips": self._generate_cost_saving_tips(vendor, requirement),
        }

    def _identify_cost_drivers(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> List[str]:
        """识别成本驱动因素"""
        drivers = []

        if vendor.vendor in [TechStack.OPENAI, TechStack.ANTHROPIC]:
            drivers.append("API调用费用（按token计费）")

        if vendor.vendor == TechStack.GOOGLE:
            drivers.append("云服务集成费用")

        if (
            vendor.vendor == TechStack.BYTEDANCE
            and requirement.production_scale != "prototype"
        ):
            drivers.append("自建基础设施和维护成本")

        if requirement.production_scale == "large_scale":
            drivers.append("高并发处理成本")

        if requirement.customization_needs == "high":
            drivers.append("定制开发成本")

        return drivers

    def _generate_cost_saving_tips(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> List[str]:
        """生成成本节约建议"""
        tips = []

        if vendor.vendor in [TechStack.OPENAI, TechStack.ANTHROPIC]:
            tips.append("使用缓存减少重复API调用")
            tips.append("优化提示词减少token使用")
            tips.append("考虑使用较小模型（如GPT-3.5而不是GPT-4）")

        if vendor.vendor == TechStack.BYTEDANCE:
            tips.append("利用开源优势，社区贡献减少开发成本")
            tips.append("选择适合的部署规模，避免过度配置")

        if vendor.vendor == TechStack.GOOGLE:
            tips.append("利用Google Cloud的免费额度")
            tips.append("优化工作流设计减少不必要的调用")

        if requirement.production_scale == "prototype":
            tips.append("原型阶段使用免费额度或开发版")

        return tips

    def _estimate_complexity(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> str:
        """估算实施复杂度"""
        base_complexity = {
            TechStack.OPENAI: "low",
            TechStack.GOOGLE: "medium",
            TechStack.ANTHROPIC: "low",
            TechStack.BYTEDANCE: "high",
        }

        complexity = base_complexity[vendor.vendor]

        # 根据需求调整
        if requirement.customization_needs == "high":
            if complexity == "low":
                complexity = "medium"
            elif complexity == "medium":
                complexity = "high"

        if (
            requirement.production_scale == "large_scale"
            and vendor.vendor == TechStack.BYTEDANCE
        ):
            complexity = "high"  # 大规模自建部署复杂

        return complexity

    def _generate_fit_analysis(
        self, vendor: VendorTechStack, requirement: ProjectRequirement
    ) -> str:
        """生成适合度分析"""
        analysis_parts = []

        # 预算匹配分析
        if requirement.budget == "low":
            if vendor.vendor == TechStack.BYTEDANCE:
                analysis_parts.append("预算有限，开源方案可避免API费用")
            else:
                analysis_parts.append("预算有限，但API方案可能产生持续费用")

        # 时间线匹配分析
        if requirement.timeline == "urgent":
            if vendor.vendor == TechStack.OPENAI:
                analysis_parts.append("时间紧迫，OpenAI API可快速集成")
            elif vendor.vendor == TechStack.BYTEDANCE:
                analysis_parts.append("时间紧迫，但开源方案需要更多前期开发")

        # 定制需求分析
        if requirement.customization_needs == "high":
            if vendor.vendor == TechStack.BYTEDANCE:
                analysis_parts.append("高定制需求，开源方案提供完全控制")
            else:
                analysis_parts.append("高定制需求，但闭源方案可能有限制")

        # 项目类型分析
        if requirement.project_type == "enterprise":
            if vendor.vendor == TechStack.GOOGLE:
                analysis_parts.append("企业项目，Google Cloud提供完整企业级支持")
            elif vendor.vendor == TechStack.ANTHROPIC:
                analysis_parts.append("企业项目，Anthropic的安全特性符合企业要求")

        # 如果没有特定分析，生成一般分析
        if not analysis_parts:
            analysis_parts.append(f"{vendor.vendor.value}方案可满足基本需求")

        return " | ".join(analysis_parts)


# ============================================================================
# 演示工具函数
# ============================================================================


def print_vendor_comparison_table(vendor_stacks: Dict[TechStack, VendorTechStack]):
    """打印厂商对比表格"""
    print("=" * 100)
    print("主流大厂AI Agent技术栈对比")
    print("=" * 100)

    # 准备表格数据
    table_data = []
    for vendor, stack in vendor_stacks.items():
        row = [
            vendor.value,
            stack.core_model,
            stack.framework,
            "开源" if stack.open_source else "闭源",
            ", ".join(stack.key_strengths[:2]),
            ", ".join(stack.key_weaknesses[:2]),
            stack.best_for[0],
        ]
        table_data.append(row)

    # 打印表格
    headers = ["厂商", "核心模型", "框架", "开源", "主要优势", "主要劣势", "最适合场景"]
    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left"))
    print()


def print_evaluation_results(
    evaluations: List[TechEvaluation], requirement: ProjectRequirement
):
    """打印评估结果"""
    print("\n" + "=" * 100)
    print("技术选型评估结果")
    print("=" * 100)

    # 打印项目需求
    print(f"项目需求分析:")
    print(f"  项目类型: {requirement.project_type}")
    print(f"  团队规模: {requirement.team_size}")
    print(f"  预算水平: {requirement.budget}")
    print(f"  时间要求: {requirement.timeline}")
    print(f"  定制需求: {requirement.customization_needs}")
    print(f"  生产规模: {requirement.production_scale}")
    print()

    # 打印评估结果表格
    table_data = []
    for eval in evaluations:
        # 确定推荐等级显示
        rec_map = {
            "strong_recommend": "⭐️⭐️⭐️ 强烈推荐",
            "recommend": "⭐️⭐️ 推荐",
            "consider": "⭐️ 可考虑",
            "avoid": "❌ 不建议",
        }

        row = [
            eval.vendor.value,
            f"{eval.score:.1f}/100",
            rec_map[eval.recommendation_level],
            eval.implementation_complexity,
            f"${eval.cost_estimate['medium_estimate']:.0f}/月",
            eval.fit_analysis[:50] + "..."
            if len(eval.fit_analysis) > 50
            else eval.fit_analysis,
        ]
        table_data.append(row)

    # 按分数排序
    table_data.sort(key=lambda x: float(x[1].split("/")[0]), reverse=True)

    headers = ["厂商", "适合度", "推荐等级", "实施复杂度", "月成本估算", "适合度分析"]
    print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="left"))
    print()


def print_detailed_recommendation(evaluations: List[TechEvaluation]):
    """打印详细推荐"""
    print("\n" + "=" * 100)
    print("详细技术选型建议")
    print("=" * 100)

    # 找到最高分
    evaluations.sort(key=lambda x: x.score, reverse=True)
    best_eval = evaluations[0]

    print(f"🏆 最推荐方案: {best_eval.vendor.value}")
    print(f"   适合度分数: {best_eval.score:.1f}/100")
    print(f"   推荐理由: {best_eval.fit_analysis}")
    print()

    print("📊 成本估算:")
    print(f"   低成本场景: ${best_eval.cost_estimate['low_estimate']:.0f}/月")
    print(f"   中等场景: ${best_eval.cost_estimate['medium_estimate']:.0f}/月")
    print(f"   高成本场景: ${best_eval.cost_estimate['high_estimate']:.0f}/月")
    print()

    if best_eval.cost_estimate["cost_drivers"]:
        print("💰 主要成本驱动:")
        for driver in best_eval.cost_estimate["cost_drivers"]:
            print(f"   • {driver}")
        print()

    if best_eval.cost_estimate["cost_saving_tips"]:
        print("💡 成本节约建议:")
        for tip in best_eval.cost_estimate["cost_saving_tips"]:
            print(f"   • {tip}")
        print()

    print("⚙️ 实施建议:")
    print(f"   实施复杂度: {best_eval.implementation_complexity}")

    if best_eval.implementation_complexity == "high":
        print("   建议: 预留足够开发时间，考虑技术债务管理")
    elif best_eval.implementation_complexity == "medium":
        print("   建议: 中等难度，需要有经验的开发人员")
    else:
        print("   建议: 相对简单，适合快速启动")

    print()

    # 备选方案
    print("🔄 备选方案:")
    for i, eval in enumerate(evaluations[1:4], 2):
        if eval.recommendation_level in ["recommend", "consider"]:
            print(
                f"   {i}. {eval.vendor.value} ({eval.score:.1f}分): {eval.fit_analysis}"
            )


def simulate_api_calls():
    """模拟不同厂商API调用"""
    print("\n" + "=" * 100)
    print("模拟API调用示例")
    print("=" * 100)

    # 模拟OpenAI API调用
    print("1. OpenAI GPT API调用示例:")
    print("   ```python")
    print("   import openai")
    print("   ")
    print("   response = openai.ChatCompletion.create(")
    print("       model='gpt-4',")
    print("       messages=[{'role': 'user', 'content': '你好！'}],")
    print("       temperature=0.7")
    print("   )")
    print("   print(response.choices[0].message.content)")
    print("   ```")
    print()

    # 模拟Google Vertex AI调用
    print("2. Google Vertex AI调用示例:")
    print("   ```python")
    print("   import vertexai")
    print("   from vertexai.generative_models import GenerativeModel")
    print("   ")
    print("   model = GenerativeModel('gemini-pro')")
    print("   response = model.generate_content('分析这张图片中的产品')")
    print("   print(response.text)")
    print("   ```")
    print()

    # 模拟DeerFlow调用
    print("3. DeerFlow Agent调用示例:")
    print("   ```python")
    print("   from deerflow import Agent, Tool")
    print("   ")
    print("   # 定义工具")
    print("   calculator = Tool(")
    print("       name='calculator',")
    print("       description='数学计算',")
    print("       func=lambda expr: eval(expr)")
    print("   )")
    print("   ")
    print("   # 创建Agent")
    print("   agent = Agent(tools=[calculator])")
    print("   response = agent.run('计算15*8的值')")
    print("   print(response)")
    print("   ```")
    print()


def demonstrate_decision_tree():
    """演示技术选型决策树"""
    print("\n" + "=" * 100)
    print("技术选型决策树演示")
    print("=" * 100)

    print("决策树问题示例:")
    print()

    questions = [
        "1. 是否需要高度定制化的功能？",
        "   → 是: 考虑开源方案（DeerFlow）",
        "   → 否: 继续下一问题",
        "",
        "2. 是否有严格的数据隐私和安全要求？",
        "   → 是: 考虑本地部署方案（DeerFlow）或Anthropic",
        "   → 否: 继续下一问题",
        "",
        "3. 是否需要快速上线和验证想法？",
        "   → 是: 考虑OpenAI（API简单）",
        "   → 否: 继续下一问题",
        "",
        "4. 是否已经在特定云平台上？",
        "   → Google Cloud: 考虑Vertex AI",
        "   → AWS/Azure: 考虑相应平台的AI服务",
        "   → 无特定平台: 继续下一问题",
        "",
        "5. 预算限制如何？",
        "   → 有限: 考虑DeerFlow（开源免费）或GPT-3.5",
        "   → 充足: 根据其他需求选择",
        "",
        "6. 是否需要处理多模态（图像、视频）？",
        "   → 是: 优先考虑Google Gemini",
        "   → 否: 根据文本处理需求选择",
    ]

    for line in questions:
        print(line)

    print()
    print("💡 提示: DeerFlow特别适合以下场景:")
    print("   • 需要完全控制和定制")
    print("   • 数据隐私和安全是首要考虑")
    print("   • 需要多Agent协作的复杂系统")
    print("   • 长期项目，希望避免厂商锁定")


# ============================================================================
# 主演示函数
# ============================================================================


def main():
    """主演示函数"""
    print("大厂技术选型对比 - 课堂演示代码")
    print("=" * 100)
    print("演示主流AI Agent技术栈对比和选型决策")
    print("=" * 100)

    # 加载厂商数据
    vendor_stacks = load_vendor_tech_stacks()

    # 1. 显示厂商对比
    print_vendor_comparison_table(vendor_stacks)

    # 2. 模拟不同项目场景的选型评估
    print("模拟项目场景评估")
    print("-" * 100)

    # 场景1: 初创公司快速原型
    print("\n场景1: 初创公司AI助手原型")
    print("描述: 3人团队，预算有限，需要1个月内上线MVP验证想法")

    startup_req = ProjectRequirement(
        project_type="startup",
        team_size="small",
        budget="low",
        timeline="urgent",
        customization_needs="low",
        production_scale="prototype",
    )

    engine = TechSelectionEngine()
    startup_evals = [
        engine.evaluate_vendor_for_project(vendor, startup_req)
        for vendor in vendor_stacks.keys()
    ]

    print_evaluation_results(startup_evals, startup_req)
    print_detailed_recommendation(startup_evals)

    # 场景2: 企业级知识管理系统
    print("\n" + "=" * 100)
    print("场景2: 企业级知识管理系统")
    print("描述: 大型企业，有严格数据安全要求，需要高度定制，预算充足")

    enterprise_req = ProjectRequirement(
        project_type="enterprise",
        team_size="large",
        budget="high",
        timeline="normal",
        customization_needs="high",
        production_scale="large_scale",
    )

    enterprise_evals = [
        engine.evaluate_vendor_for_project(vendor, enterprise_req)
        for vendor in vendor_stacks.keys()
    ]

    print_evaluation_results(enterprise_evals, enterprise_req)
    print_detailed_recommendation(enterprise_evals)

    # 3. 模拟API调用
    simulate_api_calls()

    # 4. 决策树演示
    demonstrate_decision_tree()

    # 5. 总结
    print("\n" + "=" * 100)
    print("技术选型关键原则总结")
    print("=" * 100)

    principles = [
        "1. 没有'最好'的技术栈，只有'最适合'的技术栈",
        "2. 考虑全生命周期成本，不仅是初期开发成本",
        "3. 评估团队技术能力和学习曲线",
        "4. 考虑长期维护和扩展需求",
        "5. 数据隐私和安全要求可能是决定性因素",
        "6. 开源方案提供灵活性但需要更多投入",
        "7. 闭源方案提供便利性但可能有厂商锁定风险",
        "8. 原型阶段可快速验证，生产阶段需谨慎选择",
    ]

    for principle in principles:
        print(principle)

    print()
    print("DeerFlow的核心价值主张:")
    deerflow_value = [
        "✅ 开源可控: 避免厂商锁定，完全自主",
        "✅ 模块化设计: 易于扩展和定制",
        "✅ 生产就绪: 企业级架构设计",
        "✅ 中文优化: 针对中文场景深度优化",
        "✅ 多Agent协作: 支持复杂系统设计",
        "✅ 成本可控: 开源免费，部署灵活",
    ]

    for value in deerflow_value:
        print(value)


if __name__ == "__main__":
    main()
