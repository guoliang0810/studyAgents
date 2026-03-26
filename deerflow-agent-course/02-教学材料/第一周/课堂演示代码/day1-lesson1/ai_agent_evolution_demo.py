#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent演进史 - 课堂演示代码
Day1 第1节课：AI Agent演进史与大厂技术选型

本代码演示AI Agent四个发展阶段的特征和演进过程：
1. 规则系统阶段（1960s-1980s）
2. 机器学习阶段（1990s-2010s）
3. 深度学习阶段（2010s-2018）
4. 大语言模型阶段（2018至今）
"""

import re
import random
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json


# ============================================================================
# 第一阶段：规则系统（Rule-Based Systems）
# ============================================================================


class RuleBasedAgent:
    """规则系统Agent演示（第一阶段）"""

    def __init__(self):
        # 预定义规则库
        self.rules = {
            "greeting": {
                "patterns": [r"你好|嗨|hello|hi"],
                "response": "你好！我是基于规则的AI助手。",
            },
            "farewell": {
                "patterns": [r"再见|拜拜|goodbye|bye"],
                "response": "再见！期待下次为您服务。",
            },
            "time_query": {
                "patterns": [r"现在几点|当前时间|time"],
                "response": self.get_current_time,
            },
            "calculation": {
                "patterns": [r"计算 (\d+) [+] (\d+)", r"(\d+)加(\d+)"],
                "response": self.calculate_addition,
            },
            "knowledge": {
                "patterns": [r"什么是AI|AI是什么|人工智能定义"],
                "response": "人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。",
            },
        }

    def get_current_time(self, match=None) -> str:
        """获取当前时间"""
        now = datetime.now()
        return f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}"

    def calculate_addition(self, match) -> str:
        """加法计算"""
        try:
            # 提取数字
            nums = [int(g) for g in match.groups() if g.isdigit()]
            if len(nums) >= 2:
                result = sum(nums[:2])
                return f"{nums[0]} + {nums[1]} = {result}"
        except:
            pass
        return "计算失败，请检查输入格式。"

    def process(self, user_input: str) -> str:
        """处理用户输入"""
        user_input = user_input.strip().lower()

        # 遍历所有规则，寻找匹配
        for rule_name, rule_info in self.rules.items():
            for pattern in rule_info["patterns"]:
                match = re.match(pattern, user_input)
                if match:
                    response = rule_info["response"]
                    if callable(response):
                        return response(match)
                    else:
                        return response

        # 没有匹配规则
        return "抱歉，这个问题超出了我的知识范围。我只能回答预定义规则内的问题。"


def demo_rule_based_system():
    """演示规则系统"""
    print("=" * 60)
    print("第一阶段：规则系统演示")
    print("=" * 60)

    agent = RuleBasedAgent()

    test_cases = [
        "你好",
        "现在几点",
        "计算 15 + 23",
        "什么是AI",
        "今天天气怎么样",
    ]

    for query in test_cases:
        print(f"\n用户: {query}")
        response = agent.process(query)
        print(f"Agent: {response}")

    print("\n规则系统特点总结:")
    print("- 优点: 逻辑清晰，结果可解释，易于调试")
    print("- 缺点: 灵活性差，无法处理未知问题，知识获取困难")
    print("- 代表系统: ELIZA (1966), MYCIN (1972)")


# ============================================================================
# 第二阶段：机器学习系统（Machine Learning Systems）
# ============================================================================


@dataclass
class TrainingExample:
    """训练样本"""

    features: List[float]
    label: str


class MLAgent:
    """机器学习Agent演示（第二阶段）"""

    def __init__(self):
        # 模拟训练数据：垃圾邮件分类
        self.training_data = [
            TrainingExample([1.0, 0.8, 0.1], "spam"),  # 包含"免费"、"优惠"等词
            TrainingExample([0.9, 0.7, 0.2], "spam"),
            TrainingExample([0.1, 0.2, 0.9], "not_spam"),  # 正常邮件
            TrainingExample([0.2, 0.3, 0.8], "not_spam"),
            TrainingExample([0.8, 0.9, 0.3], "spam"),
            TrainingExample([0.3, 0.4, 0.7], "not_spam"),
        ]

        # 模拟简单模型（实际使用scikit-learn等库）
        self.model_weights = self.train_model()

    def train_model(self) -> List[float]:
        """模拟训练过程（简化版）"""
        # 简单线性模型：w0 + w1*x1 + w2*x2 + w3*x3 > 0.5 -> spam
        # 这里使用预设权重模拟训练结果
        return [0.1, 0.8, 0.6, -0.5]

    def predict(self, features: List[float]) -> str:
        """预测分类"""
        # 线性模型计算
        score = self.model_weights[0]
        for i, feat in enumerate(features, 1):
            score += self.model_weights[i] * feat

        return "spam" if score > 0.5 else "not_spam"

    def extract_features(self, email_text: str) -> List[float]:
        """提取特征（简化版）"""
        text_lower = email_text.lower()

        # 特征1: 包含"免费"、"优惠"等营销词的比例
        marketing_words = ["免费", "优惠", "折扣", "限时", "抢购", "点击"]
        feature1 = sum(1 for word in marketing_words if word in text_lower) / len(
            marketing_words
        )

        # 特征2: 包含链接或电话号码的指示
        has_link = 1.0 if ("http://" in text_lower or "www." in text_lower) else 0.0
        has_phone = 1.0 if re.search(r"\d{11}", text_lower) else 0.0
        feature2 = max(has_link, has_phone)

        # 特征3: 正常内容的指示（包含问候语等）
        normal_words = ["你好", "谢谢", "请问", "工作", "会议", "项目"]
        feature3 = sum(1 for word in normal_words if word in text_lower) / len(
            normal_words
        )

        return [feature1, feature2, feature3]

    def process_email(self, email_text: str) -> Dict[str, Any]:
        """处理邮件"""
        features = self.extract_features(email_text)
        prediction = self.predict(features)

        return {
            "email": email_text[:50] + "..." if len(email_text) > 50 else email_text,
            "features": features,
            "prediction": prediction,
            "confidence": random.uniform(0.7, 0.95),  # 模拟置信度
        }


def demo_machine_learning():
    """演示机器学习系统"""
    print("\n" + "=" * 60)
    print("第二阶段：机器学习系统演示")
    print("=" * 60)

    agent = MLAgent()

    test_emails = [
        "免费获取最新优惠！点击链接立即领取折扣券！限时抢购！",
        "你好，关于下周的项目会议，请确认时间和地点。谢谢！",
        "恭喜您获得特价优惠！立即拨打13800138000领取大奖！",
        "张经理，附件是上周会议纪要，请查收。有问题随时联系。",
    ]

    print("垃圾邮件分类演示:")
    print("-" * 40)

    for i, email in enumerate(test_emails, 1):
        result = agent.process_email(email)
        print(f"\n邮件{i}: {result['email']}")
        print(f"特征值: {result['features']}")
        print(f"预测: {result['prediction']} (置信度: {result['confidence']:.2f})")

    print("\n机器学习系统特点总结:")
    print("- 优点: 数据驱动，适应性强，可处理未知模式")
    print("- 缺点: 需要大量标注数据，特征工程复杂，可解释性差")
    print("- 代表应用: 垃圾邮件过滤，推荐系统，搜索引擎")


# ============================================================================
# 第三阶段：深度学习系统（Deep Learning Systems）
# ============================================================================


class NeuralNetwork:
    """简单的神经网络演示（第三阶段）"""

    def __init__(self, input_size=3, hidden_size=4, output_size=2):
        # 模拟神经网络权重（简化版）
        self.W1 = np.random.randn(input_size, hidden_size) * 0.1
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, output_size) * 0.1
        self.b2 = np.zeros((1, output_size))

    def forward(self, X):
        """前向传播"""
        # 隐藏层
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = np.tanh(self.z1)  # 激活函数

        # 输出层
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        exp_scores = np.exp(self.z2)
        self.probs = exp_scores / np.sum(exp_scores, axis=1, keepdims=True)

        return self.probs

    def predict(self, X):
        """预测"""
        probs = self.forward(X)
        return np.argmax(probs, axis=1)


class DeepLearningAgent:
    """深度学习Agent演示（第三阶段）"""

    def __init__(self):
        # 模拟一个简单的图像分类器
        self.categories = ["猫", "狗", "汽车", "人脸"]
        self.nn = NeuralNetwork(input_size=256, hidden_size=128, output_size=4)

        # 模拟特征提取（实际使用CNN）
        print("初始化深度学习模型...")
        print("加载预训练权重...")
        print("模型准备就绪！")

    def extract_image_features(self, image_description: str) -> np.ndarray:
        """模拟图像特征提取（实际使用CNN）"""
        # 这里用文本描述模拟图像特征
        features = np.zeros(256)

        # 根据描述生成模拟特征
        if "猫" in image_description:
            features[:64] = np.random.randn(64) * 0.5 + 1.0
        if "狗" in image_description:
            features[64:128] = np.random.randn(64) * 0.5 + 0.8
        if "汽车" in image_description:
            features[128:192] = np.random.randn(64) * 0.5 + 0.6
        if "人脸" in image_description:
            features[192:] = np.random.randn(64) * 0.5 + 0.9

        # 添加噪声
        features += np.random.randn(256) * 0.1

        return features.reshape(1, -1)

    def classify_image(self, image_description: str) -> Dict[str, Any]:
        """图像分类"""
        # 提取特征
        features = self.extract_image_features(image_description)

        # 前向传播
        probs = self.nn.forward(features)

        # 获取预测结果
        pred_idx = np.argmax(probs)
        confidence = probs[0, pred_idx]

        return {
            "description": image_description,
            "predicted_category": self.categories[pred_idx],
            "confidence": float(confidence),
            "all_probabilities": {
                cat: float(prob) for cat, prob in zip(self.categories, probs[0])
            },
        }


def demo_deep_learning():
    """演示深度学习系统"""
    print("\n" + "=" * 60)
    print("第三阶段：深度学习系统演示")
    print("=" * 60)

    agent = DeepLearningAgent()

    test_images = [
        "一只橘猫在沙发上睡觉",
        "黑色的拉布拉多犬在草地上奔跑",
        "红色的跑车在高速公路上行驶",
        "年轻女性微笑的人脸照片",
        "猫和狗在一起的图片",
    ]

    print("图像分类演示:")
    print("-" * 40)

    for i, img_desc in enumerate(test_images, 1):
        result = agent.classify_image(img_desc)
        print(f"\n图像{i}: {result['description']}")
        print(f"预测类别: {result['predicted_category']}")
        print(f"置信度: {result['confidence']:.2f}")

        # 显示所有类别概率
        print("所有类别概率:")
        for cat, prob in result["all_probabilities"].items():
            print(f"  {cat}: {prob:.3f}")

    print("\n深度学习系统特点总结:")
    print("- 优点: 自动特征学习，处理复杂模式，性能优越")
    print("- 缺点: 需要大量数据，计算资源高，黑盒问题，可解释性差")
    print("- 代表应用: 图像识别，语音识别，AlphaGo")


# ============================================================================
# 第四阶段：大语言模型系统（Large Language Model Systems）
# ============================================================================


@dataclass
class Tool:
    """工具定义"""

    name: str
    description: str
    func: callable


class LLMAgent:
    """大语言模型Agent演示（第四阶段）"""

    def __init__(self):
        # 模拟LLM的"知识"
        self.knowledge_base = {
            "ai_history": {
                "1956": "达特茅斯会议，AI诞生",
                "1997": "深蓝击败国际象棋冠军卡斯帕罗夫",
                "2012": "AlexNet在ImageNet竞赛中取得突破",
                "2016": "AlphaGo击败围棋冠军李世石",
                "2018": "GPT-1发布，开启大语言模型时代",
                "2020": "GPT-3发布，1750亿参数",
                "2022": "ChatGPT发布，引发AI热潮",
                "2023": "GPT-4发布，多模态能力",
                "2024": "AI Agent成为焦点，DeerFlow发布",
            },
            "companies": {
                "OpenAI": "GPT系列，ChatGPT，DALL-E",
                "Google": "PaLM，Gemini，Bard",
                "Anthropic": "Claude系列",
                "字节跳动": "云雀大模型，DeerFlow",
                "百度": "文心一言",
                "阿里": "通义千问",
            },
        }

        # 工具系统
        self.tools = self._register_tools()

        print("初始化大语言模型Agent...")
        print("加载预训练模型...")
        print("工具系统就绪...")
        print("Agent初始化完成！")

    def _register_tools(self) -> Dict[str, Tool]:
        """注册工具"""
        return {
            "calculator": Tool(
                name="calculator",
                description="执行数学计算",
                func=lambda expr: f"计算结果: {eval(expr)}",  # 简化版
            ),
            "search_knowledge": Tool(
                name="search_knowledge",
                description="搜索知识库",
                func=self.search_knowledge,
            ),
            "current_time": Tool(
                name="current_time",
                description="获取当前时间",
                func=lambda: (
                    f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ),
            ),
            "plan_task": Tool(
                name="plan_task", description="规划任务步骤", func=self.plan_task
            ),
        }

    def search_knowledge(self, query: str) -> str:
        """搜索知识库"""
        results = []

        # 在AI历史中搜索
        for year, event in self.knowledge_base["ai_history"].items():
            if query.lower() in event.lower():
                results.append(f"{year}: {event}")

        # 在公司信息中搜索
        for company, info in self.knowledge_base["companies"].items():
            if query.lower() in company.lower() or query.lower() in info.lower():
                results.append(f"{company}: {info}")

        if results:
            return "\n".join(results[:3])  # 返回前3个结果
        else:
            return f"未找到关于'{query}'的信息"

    def plan_task(self, task: str) -> str:
        """规划任务步骤"""
        steps = [
            "1. 理解任务要求和目标",
            "2. 分析可用资源和约束条件",
            "3. 拆解任务为子任务",
            "4. 为每个子任务分配工具或方法",
            "5. 制定执行时间表",
            "6. 设计验证和评估方法",
        ]

        return f"任务 '{task}' 的执行计划:\n" + "\n".join(steps)

    def process_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询"""
        print(f"\n用户查询: {query}")

        # 意图识别（简化版）
        if any(word in query.lower() for word in ["计算", "算", "+", "-", "*", "/"]):
            # 数学计算
            tool = self.tools["calculator"]
            result = tool.func(query)
            tool_used = "calculator"

        elif any(
            word in query.lower()
            for word in ["历史", "发展", "时间线", "company", "公司"]
        ):
            # 知识查询
            tool = self.tools["search_knowledge"]
            result = tool.func(query)
            tool_used = "search_knowledge"

        elif any(word in query.lower() for word in ["时间", "几点", "现在"]):
            # 时间查询
            tool = self.tools["current_time"]
            result = tool.func()
            tool_used = "current_time"

        elif any(word in query.lower() for word in ["计划", "规划", "步骤", "如何做"]):
            # 任务规划
            tool = self.tools["plan_task"]
            result = tool.func(query)
            tool_used = "plan_task"

        else:
            # 通用对话
            result = f"我理解您的问题是: '{query}'。\n"
            result += "作为现代AI Agent，我可以:\n"
            result += "1. 回答关于AI发展历史的问题\n"
            result += "2. 执行数学计算\n"
            result += "3. 规划任务步骤\n"
            result += "4. 提供当前时间信息\n"
            result += "请告诉我您需要哪方面的帮助？"
            tool_used = "dialogue"

        return {
            "query": query,
            "response": result,
            "tool_used": tool_used,
            "timestamp": datetime.now().isoformat(),
        }


def demo_llm_agent():
    """演示大语言模型Agent"""
    print("\n" + "=" * 60)
    print("第四阶段：大语言模型Agent演示")
    print("=" * 60)

    agent = LLMAgent()

    test_queries = [
        "计算 15 * 8 + 20",
        "AI在2016年有什么重要事件？",
        "现在是什么时间？",
        "如何学习AI Agent开发？",
        "介绍一下字节跳动的AI技术",
        "今天的天气怎么样？",
    ]

    print("现代AI Agent能力演示:")
    print("-" * 40)

    for i, query in enumerate(test_queries, 1):
        result = agent.process_query(query)
        print(f"\n查询{i}: {result['query']}")
        print(f"使用的工具: {result['tool_used']}")
        print(f"响应: {result['response']}")

    print("\n大语言模型Agent特点总结:")
    print("- 优点: 强大的语言理解，多任务处理，上下文学习，工具使用")
    print("- 缺点: 计算成本高，可能产生幻觉，需要安全机制")
    print("- 代表系统: ChatGPT, Claude, DeerFlow Agent")
    print("- 核心特征: 自主性，交互性，工具使用，记忆学习，多模态")


# ============================================================================
# 演进总结与对比
# ============================================================================


def evolution_summary():
    """AI Agent演进总结"""
    print("\n" + "=" * 60)
    print("AI Agent演进总结与对比")
    print("=" * 60)

    stages = [
        {
            "stage": "规则系统",
            "period": "1960s-1980s",
            "core_tech": "预定义规则，逻辑推理",
            "strengths": ["逻辑清晰", "结果可解释", "易于调试"],
            "weaknesses": ["灵活性差", "无法处理未知问题", "知识获取困难"],
            "example": "ELIZA, MYCIN",
        },
        {
            "stage": "机器学习",
            "period": "1990s-2010s",
            "core_tech": "统计学习，特征工程",
            "strengths": ["数据驱动", "适应性强", "可处理模式"],
            "weaknesses": ["需要大量标注数据", "特征工程复杂", "可解释性差"],
            "example": "垃圾邮件过滤，推荐系统",
        },
        {
            "stage": "深度学习",
            "period": "2010s-2018",
            "core_tech": "神经网络，表示学习",
            "strengths": ["自动特征学习", "处理复杂模式", "性能优越"],
            "weaknesses": ["需要大量数据", "计算资源高", "黑盒问题"],
            "example": "图像识别，AlphaGo",
        },
        {
            "stage": "大语言模型",
            "period": "2018至今",
            "core_tech": "Transformer，预训练+微调",
            "strengths": ["强大语言理解", "多任务处理", "上下文学习", "工具使用"],
            "weaknesses": ["计算成本高", "幻觉问题", "需要安全机制"],
            "example": "ChatGPT, Claude, DeerFlow",
        },
    ]

    print("四个发展阶段对比:")
    print("-" * 60)

    for i, stage in enumerate(stages, 1):
        print(f"\n{i}. {stage['stage']} ({stage['period']})")
        print(f"   核心技术: {stage['core_tech']}")
        print(f"   主要优势: {', '.join(stage['strengths'])}")
        print(f"   主要局限: {', '.join(stage['weaknesses'])}")
        print(f"   代表系统: {stage['example']}")

    print("\n" + "=" * 60)
    print("现代AI Agent的五个核心特征:")
    print("=" * 60)

    features = [
        ("自主性", "能够自主设定目标、规划步骤、执行行动"),
        ("交互性", "能够与人类或其他Agent进行自然、多轮对话"),
        ("工具使用", "能够调用外部工具和API扩展能力"),
        ("记忆与学习", "能够记住历史交互并从经验中学习"),
        ("多模态", "能够理解和生成文本、图像、音频等多种形式内容"),
    ]

    for name, description in features:
        print(f"• {name}: {description}")

    print("\n" + "=" * 60)
    print("学习建议:")
    print("=" * 60)
    print("1. 理解历史演进: 从规则系统到LLM的技术突破")
    print("2. 掌握核心特征: 现代AI Agent的五个关键能力")
    print("3. 学习实际框架: 如DeerFlow的开源实现")
    print("4. 动手实践: 从简单Agent开始，逐步增加复杂度")
    print("5. 关注发展趋势: 多模态、具身智能、神经符号等方向")


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主演示函数"""
    print("AI Agent演进史 - 课堂演示代码")
    print("=" * 60)
    print("演示AI Agent四个发展阶段的技术特征")
    print("=" * 60)

    # 演示四个阶段
    demo_rule_based_system()
    demo_machine_learning()
    demo_deep_learning()
    demo_llm_agent()

    # 总结对比
    evolution_summary()

    print("\n" + "=" * 60)
    print("演示结束")
    print("=" * 60)
    print("代码位置: day1-lesson1/ai_agent_evolution_demo.py")
    print("课后练习: Day1-第1节课-AI Agent演进史-课后练习.md")
    print("参考答案: Day1-第1节课-AI Agent演进史-答案与解析.md")


if __name__ == "__main__":
    main()
