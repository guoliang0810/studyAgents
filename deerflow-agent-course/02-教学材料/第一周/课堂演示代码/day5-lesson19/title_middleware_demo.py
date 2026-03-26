#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 5 Lesson 19: TitleMiddleware - 课堂演示代码

本文件提供完整的标题生成中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示标题生成机制的各个方面：
1. 标题生成基础与数据结构
2. TitleMiddleware核心实现
3. 高级标题生成策略
4. 完整测试系统与演示

教学目标：
1. 理解对话标题生成的重要性和应用场景
2. 掌握关键词提取和意图识别的基本方法
3. 熟悉TitleMiddleware的设计与实现原理
4. 掌握高级标题生成和质量评估技术

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json
可选依赖: pip install jieba (用于中文分词), pip install nltk (用于文本处理)

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月1日
"""

import asyncio
import re
import time
import json
import random
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter, defaultdict
import heapq

# ============================================================================
# 第一部分：标题生成基础与数据结构
# ============================================================================


class TitleGenerationStrategy(Enum):
    """标题生成策略枚举"""

    INTENT_KEYWORDS = "intent_keywords"  # 意图+关键词
    MESSAGE_TRUNCATION = "message_truncation"  # 消息截取
    KEYWORD_COMBINATION = "keyword_combination"  # 关键词组合
    TEMPLATE_FILLING = "template_filling"  # 模板填充
    CONVERSATION_ANALYSIS = "conversation_analysis"  # 对话分析
    TOOL_BASED = "tool_based"  # 基于工具调用


class IntentType(Enum):
    """意图类型枚举"""

    SEARCH = "搜索"
    CREATE = "创建"
    DELETE = "删除"
    MODIFY = "修改"
    ANALYZE = "分析"
    QUESTION = "询问"
    CONVERSATION = "对话"
    REQUEST = "请求"
    TRANSLATE = "翻译"
    CALCULATE = "计算"
    SCHEDULE = "安排"
    REMIND = "提醒"
    UNKNOWN = "未知"


@dataclass
class TitleGenerationConfig:
    """标题生成配置"""

    max_title_length: int = 50
    min_title_length: int = 5
    keyword_limit: int = 5
    default_title: str = "新对话"
    enable_intent_detection: bool = True
    enable_keyword_extraction: bool = True
    enable_history_analysis: bool = False
    prefer_intent_keywords: bool = True
    language: str = "zh"  # zh, en, ja, etc.

    # 停用词配置
    stop_words: Set[str] = field(
        default_factory=lambda: {
            # 中文停用词
            "的",
            "了",
            "在",
            "是",
            "我",
            "你",
            "他",
            "她",
            "它",
            "这",
            "那",
            "什么",
            "怎么",
            "如何",
            "为什么",
            "帮忙",
            "请",
            "帮",
            "一下",
            "一个",
            "这个",
            "那个",
            "和",
            "与",
            "吗",
            "呢",
            "吧",
            "啊",
            "呀",
            "哦",
            "嗯",
            "唉",
            "啦",
            "么",
            "都",
            "就",
            "也",
            "还",
            "又",
            "但",
            "而",
            "且",
            "虽",
            "然",
            "如果",
            "那么",
            "因为",
            "所以",
            "因此",
            "然后",
            "之后",
            "之前",
            "时候",
            "时间",
            "可以",
            "可能",
            "需要",
            "想要",
            "希望",
            "觉得",
            "认为",
            "知道",
            "了解",
            "明白",
            "理解",
            "清楚",
            "好的",
            "好吧",
            "好的吧",
            # 英文停用词
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "if",
            "because",
            "as",
            "what",
            "why",
            "how",
            "when",
            "where",
            "who",
            "which",
            "this",
            "that",
            "these",
            "those",
            "am",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "having",
            "do",
            "does",
            "did",
            "doing",
            "can",
            "could",
            "may",
            "might",
            "must",
            "shall",
            "should",
            "will",
            "would",
            "please",
            "help",
            "thanks",
            "thank",
        }
    )

    # 意图关键词映射
    intent_keywords: Dict[IntentType, Set[str]] = field(
        default_factory=lambda: {
            IntentType.SEARCH: {
                "搜索",
                "查找",
                "找",
                "查询",
                "search",
                "find",
                "look",
                "query",
            },
            IntentType.CREATE: {
                "创建",
                "新建",
                "建立",
                "制作",
                "create",
                "make",
                "build",
                "generate",
            },
            IntentType.DELETE: {
                "删除",
                "移除",
                "去掉",
                "清除",
                "delete",
                "remove",
                "erase",
                "clear",
            },
            IntentType.MODIFY: {
                "修改",
                "更改",
                "调整",
                "更新",
                "修改",
                "change",
                "modify",
                "update",
                "adjust",
            },
            IntentType.ANALYZE: {
                "分析",
                "统计",
                "计算",
                "评估",
                "analyze",
                "statistics",
                "calculate",
                "evaluate",
            },
            IntentType.QUESTION: {
                "怎么",
                "如何",
                "什么",
                "为什么",
                "何时",
                "哪里",
                "how",
                "what",
                "why",
                "when",
                "where",
            },
            IntentType.REQUEST: {
                "帮",
                "帮忙",
                "请",
                "帮我",
                "请求",
                "需要",
                "help",
                "please",
                "need",
                "request",
            },
            IntentType.TRANSLATE: {"翻译", "转译", "译", "translate", "translation"},
            IntentType.CALCULATE: {"计算", "算", "数", "calculate", "compute", "count"},
            IntentType.SCHEDULE: {
                "安排",
                "计划",
                "日程",
                "schedule",
                "plan",
                "arrange",
            },
            IntentType.REMIND: {"提醒", "记住", "记得", "remind", "remember", "recall"},
        }
    )

    # 标题模板
    title_templates: Dict[IntentType, str] = field(
        default_factory=lambda: {
            IntentType.SEARCH: "{intent}：{keywords}",
            IntentType.CREATE: "{intent}：{keywords}",
            IntentType.DELETE: "{intent}：{keywords}",
            IntentType.MODIFY: "{intent}：{keywords}",
            IntentType.ANALYZE: "{intent}：{keywords}",
            IntentType.QUESTION: "{intent}：{keywords}",
            IntentType.REQUEST: "{intent}：{keywords}",
            IntentType.TRANSLATE: "{intent}：{keywords}",
            IntentType.CALCULATE: "{intent}：{keywords}",
            IntentType.SCHEDULE: "{intent}：{keywords}",
            IntentType.REMIND: "{intent}：{keywords}",
            IntentType.CONVERSATION: "对话：{keywords}",
            IntentType.UNKNOWN: "{keywords}",
        }
    )


@dataclass
class GeneratedTitle:
    """生成的标题数据"""

    title: str
    intent: IntentType
    keywords: List[str]
    strategy: TitleGenerationStrategy
    confidence: float  # 0.0-1.0
    original_message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "intent": self.intent.value,
            "keywords": self.keywords,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "original_message": self.original_message,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"标题: {self.title} (意图: {self.intent.value}, 置信度: {self.confidence:.2f})"


# 简化的Agent请求和响应类（用于演示）
@dataclass
class AgentRequest:
    """Agent请求"""

    user_id: str
    session_id: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResponse:
    """Agent响应"""

    thread_id: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "thread_id": self.thread_id,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 第二部分：TitleMiddleware核心实现
# ============================================================================


class KeywordExtractor:
    """关键词提取器"""

    def __init__(self, config: TitleGenerationConfig):
        self.config = config
        self.cache = {}  # 简单的缓存机制

    def extract(self, text: str, use_cache: bool = True) -> List[str]:
        """提取关键词"""
        if use_cache and text in self.cache:
            return self.cache[text]

        # 预处理：移除标点符号，转换为小写（对英文）
        text_clean = self._preprocess_text(text)

        # 分词（简单版本：按空格分割）
        words = self._tokenize(text_clean)

        # 过滤停用词和短词
        keywords = self._filter_words(words)

        # 排序和选择（基于频率和长度）
        keywords = self._rank_keywords(keywords)

        # 限制数量
        keywords = keywords[: self.config.keyword_limit]

        # 缓存结果
        if use_cache:
            self.cache[text] = keywords

        return keywords

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除标点符号（保留中文和英文字母、数字）
        if self.config.language == "zh":
            # 中文：移除大部分标点
            text = re.sub(r"[^\w\u4e00-\u9fff\s]", "", text)
        else:
            # 英文：保留字母数字和空格
            text = re.sub(r"[^\w\s]", "", text)
            text = text.lower()

        return text

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单实现：按空格分割
        # 实际应用应该使用分词库（如jieba）
        words = text.split()

        # 中文特殊处理：如果没有空格，按字符分割
        if self.config.language == "zh" and len(words) == 1 and len(words[0]) > 5:
            # 简单的中文分词：按2-4字切分
            chinese_text = words[0]
            words = []
            i = 0
            while i < len(chinese_text):
                # 尝试2-4字切分
                for length in range(4, 1, -1):
                    if i + length <= len(chinese_text):
                        words.append(chinese_text[i : i + length])
                        i += length
                        break
                else:
                    i += 1

        return words

    def _filter_words(self, words: List[str]) -> List[str]:
        """过滤停用词和短词"""
        filtered = []
        for word in words:
            # 过滤停用词
            if word in self.config.stop_words:
                continue

            # 过滤过短的词（中文至少2字，英文至少3字符）
            if self.config.language == "zh":
                if len(word) < 2:
                    continue
            else:
                if len(word) < 3:
                    continue

            # 过滤纯数字
            if word.isdigit():
                continue

            filtered.append(word)

        return filtered

    def _rank_keywords(self, words: List[str]) -> List[str]:
        """关键词排序"""
        if not words:
            return []

        # 计算词频
        word_freq = Counter(words)

        # 排序：词频优先，然后长度
        ranked = sorted(
            word_freq.keys(), key=lambda w: (word_freq[w], len(w)), reverse=True
        )

        return ranked


class IntentDetector:
    """意图检测器"""

    def __init__(self, config: TitleGenerationConfig):
        self.config = config

    def detect(self, text: str) -> Tuple[IntentType, float]:
        """检测意图类型和置信度"""
        text_lower = text.lower() if self.config.language != "zh" else text

        # 初始化意图分数
        intent_scores = {intent: 0.0 for intent in IntentType}

        # 基于关键词匹配计分
        for intent_type, keywords in self.config.intent_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    intent_scores[intent_type] += 1.0

        # 特殊规则：问题意图
        if any(
            q_word in text_lower
            for q_word in ["怎么", "如何", "什么", "为什么", "how", "what", "why"]
        ):
            intent_scores[IntentType.QUESTION] += 2.0

        # 特殊规则：请求意图
        if any(
            req_word in text_lower
            for req_word in ["帮", "帮忙", "请", "帮我", "help", "please"]
        ):
            intent_scores[IntentType.REQUEST] += 2.0

        # 找出最高分意图
        if not any(score > 0 for score in intent_scores.values()):
            return IntentType.CONVERSATION, 0.5

        max_intent = max(intent_scores.items(), key=lambda x: x[1])

        # 计算置信度（归一化到0-1）
        total_score = sum(intent_scores.values())
        confidence = max_intent[1] / total_score if total_score > 0 else 0.5

        return max_intent[0], confidence


class BaseTitleGenerator:
    """基础标题生成器"""

    def __init__(self, config: Optional[TitleGenerationConfig] = None):
        self.config = config or TitleGenerationConfig()
        self.keyword_extractor = KeywordExtractor(self.config)
        self.intent_detector = IntentDetector(self.config)

    def generate(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> GeneratedTitle:
        """生成标题"""
        context = context or {}

        # 提取关键词
        keywords = []
        if self.config.enable_keyword_extraction:
            keywords = self.keyword_extractor.extract(message)

        # 检测意图
        intent = IntentType.CONVERSATION
        intent_confidence = 0.5
        if self.config.enable_intent_detection:
            intent, intent_confidence = self.intent_detector.detect(message)

        # 选择生成策略
        strategy = self._select_strategy(message, keywords, intent)

        # 生成标题
        title = self._generate_by_strategy(strategy, message, keywords, intent, context)

        # 长度限制
        title = self._enforce_length_limit(title)

        # 确保非空
        if not title.strip():
            title = self.config.default_title

        # 计算总体置信度
        confidence = self._calculate_confidence(
            intent_confidence, keywords, title, message
        )

        return GeneratedTitle(
            title=title,
            intent=intent,
            keywords=keywords,
            strategy=strategy,
            confidence=confidence,
            original_message=message,
            metadata={"language": self.config.language, "config": self.config.__dict__},
        )

    def _select_strategy(
        self, message: str, keywords: List[str], intent: IntentType
    ) -> TitleGenerationStrategy:
        """选择标题生成策略"""
        # 如果有明确意图和关键词，使用意图+关键词策略
        if (
            self.config.prefer_intent_keywords
            and intent != IntentType.CONVERSATION
            and intent != IntentType.UNKNOWN
            and keywords
        ):
            return TitleGenerationStrategy.INTENT_KEYWORDS

        # 如果有关键词但意图不明确，使用关键词组合
        if keywords:
            return TitleGenerationStrategy.KEYWORD_COMBINATION

        # 如果消息很短，使用消息截取
        if len(message) <= self.config.max_title_length:
            return TitleGenerationStrategy.MESSAGE_TRUNCATION

        # 默认使用模板填充
        return TitleGenerationStrategy.TEMPLATE_FILLING

    def _generate_by_strategy(
        self,
        strategy: TitleGenerationStrategy,
        message: str,
        keywords: List[str],
        intent: IntentType,
        context: Dict[str, Any],
    ) -> str:
        """根据策略生成标题"""
        if strategy == TitleGenerationStrategy.INTENT_KEYWORDS:
            # 意图+关键词
            keyword_str = " ".join(keywords[:3])
            template = self.config.title_templates.get(intent, "{intent}：{keywords}")
            title = template.format(intent=intent.value, keywords=keyword_str)

        elif strategy == TitleGenerationStrategy.KEYWORD_COMBINATION:
            # 关键词组合
            title = " ".join(keywords[:3])

        elif strategy == TitleGenerationStrategy.MESSAGE_TRUNCATION:
            # 消息截取
            title = message[: self.config.max_title_length]

        elif strategy == TitleGenerationStrategy.TEMPLATE_FILLING:
            # 模板填充
            keyword_str = " ".join(keywords[:3]) if keywords else "对话"
            title = f"对话：{keyword_str}"

        else:
            # 默认：直接使用消息（截取）
            title = message[: self.config.max_title_length]

        return title

    def _enforce_length_limit(self, title: str) -> str:
        """强制长度限制"""
        if len(title) > self.config.max_title_length:
            # 保留末尾的"..."
            max_len = self.config.max_title_length - 3
            title = title[:max_len] + "..."

        # 确保不低于最小长度
        if len(title) < self.config.min_title_length and len(title) > 0:
            # 如果标题太短但非空，保持原样
            pass

        return title

    def _calculate_confidence(
        self,
        intent_confidence: float,
        keywords: List[str],
        title: str,
        original_message: str,
    ) -> float:
        """计算总体置信度"""
        # 基础置信度：意图置信度
        confidence = intent_confidence

        # 关键词数量加成
        keyword_factor = min(len(keywords) / 5, 1.0)  # 最多5个关键词
        confidence = confidence * 0.7 + keyword_factor * 0.3

        # 标题长度合适性加成
        title_len = len(title)
        if self.config.min_title_length <= title_len <= self.config.max_title_length:
            length_factor = 1.0 - abs(title_len - 25) / 25  # 离25字符越近越好
            confidence = confidence * 0.8 + length_factor * 0.2

        # 确保在0-1范围内
        return max(0.0, min(1.0, confidence))


class TitleMiddleware:
    """标题生成中间件"""

    def __init__(self, config: Optional[TitleGenerationConfig] = None):
        self.config = config or TitleGenerationConfig()
        self.title_generator = BaseTitleGenerator(self.config)
        self.name = "title"
        self.storage = {}  # 简单的内存存储（生产环境应使用数据库）

    async def before_agent(
        self, request: AgentRequest, config: Optional[Dict] = None
    ) -> AgentRequest:
        """在处理请求前生成标题"""
        config = config or {}

        # 生成标题
        title_result = self.title_generator.generate(request.message)

        # 记录日志
        print(
            f"📝 [{self.name}] 生成标题: {title_result.title} "
            f"(意图: {title_result.intent.value}, 置信度: {title_result.confidence:.2f})"
        )

        # 将标题存储到请求元数据中
        if not request.metadata:
            request.metadata = {}
        request.metadata["generated_title"] = title_result.to_dict()
        request.metadata["title_generation_time"] = time.time()

        return request

    async def after_agent(
        self, response: AgentResponse, config: Optional[Dict] = None
    ) -> AgentResponse:
        """在处理响应后保存标题"""
        config = config or {}

        if response.metadata and "generated_title" in response.metadata:
            title_data = response.metadata["generated_title"]

            # 在实际应用中，这里会将标题保存到数据库或文件
            # 模拟保存到内存存储
            thread_id = response.thread_id
            self.storage[thread_id] = {
                "title": title_data["title"],
                "created_at": time.time(),
                "metadata": title_data,
            }

            print(f"💾 [{self.name}] 保存标题到对话 {thread_id}: {title_data['title']}")

            # 添加标题到响应元数据（用于后续处理）
            if not response.metadata:
                response.metadata = {}
            response.metadata["saved_title"] = title_data

        return response

    async def get_title(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取对话标题"""
        return self.storage.get(thread_id)

    async def update_title(self, thread_id: str, new_title: str) -> bool:
        """更新对话标题（允许用户编辑）"""
        if thread_id in self.storage:
            old_title = self.storage[thread_id]["title"]
            self.storage[thread_id]["title"] = new_title
            self.storage[thread_id]["updated_at"] = time.time()
            self.storage[thread_id]["user_modified"] = True

            print(
                f"✏️ [{self.name}] 更新标题 {thread_id}: '{old_title}' -> '{new_title}'"
            )
            return True
        return False

    async def list_titles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有标题"""
        titles = list(self.storage.values())
        titles.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return titles[:limit]


# ============================================================================
# 第三部分：高级标题生成策略
# ============================================================================


class AdvancedTitleGenerator(BaseTitleGenerator):
    """高级标题生成器"""

    def __init__(self, config: Optional[TitleGenerationConfig] = None):
        super().__init__(config)
        self.conversation_history = defaultdict(list)
        self.user_preferences = defaultdict(dict)

    def generate_from_conversation(
        self, messages: List[Dict[str, Any]], user_id: Optional[str] = None
    ) -> GeneratedTitle:
        """从对话历史生成标题"""
        if not messages:
            return self.generate("", {})

        # 提取所有用户消息
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]

        if not user_messages:
            # 如果没有用户消息，使用第一条消息
            first_msg = messages[0]["content"] if messages else ""
            return self.generate(first_msg, {})

        # 方法1：使用第一条用户消息
        first_user_msg = user_messages[0]
        base_result = self.generate(first_user_msg, {})

        # 方法2：分析整个对话
        conversation_analysis = self._analyze_conversation(messages)

        # 方法3：识别工具调用
        tool_based_title = self._generate_tool_based_title(messages)

        # 决策：选择最合适的标题
        final_title = self._select_best_title(
            [base_result.title, conversation_analysis, tool_based_title],
            user_messages[0],
        )

        # 更新结果
        base_result.title = final_title
        base_result.strategy = TitleGenerationStrategy.CONVERSATION_ANALYSIS
        base_result.metadata["conversation_message_count"] = len(messages)
        base_result.metadata["user_message_count"] = len(user_messages)

        return base_result

    def _analyze_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """分析对话内容"""
        if not messages:
            return self.config.default_title

        # 提取所有文本内容
        all_text = " ".join([m.get("content", "") for m in messages])

        # 提取关键词
        keywords = self.keyword_extractor.extract(all_text)

        if not keywords:
            # 如果没有关键词，返回消息数量
            msg_count = len(messages)
            return f"对话 ({msg_count} 条消息)"

        # 计算关键词频率
        keyword_freq = Counter(keywords)

        # 选择最重要的关键词
        top_keywords = [kw for kw, _ in keyword_freq.most_common(3)]

        # 生成标题
        if len(top_keywords) == 1:
            return f"关于 {top_keywords[0]} 的对话"
        else:
            return f"对话：{'、'.join(top_keywords[:2])}"

    def _generate_tool_based_title(self, messages: List[Dict[str, Any]]) -> str:
        """基于工具调用生成标题"""
        # 提取工具调用
        tool_calls = []
        for msg in messages:
            if msg.get("type") == "tool_call" or "tool_name" in msg:
                tool_calls.append(msg)

        if not tool_calls:
            return ""

        # 统计工具使用频率
        tool_counter = Counter()
        for call in tool_calls:
            tool_name = call.get("tool_name", "未知工具")
            tool_counter[tool_name] += 1

        # 生成标题
        most_common_tool, count = tool_counter.most_common(1)[0]

        tool_name_map = {
            "search": "搜索",
            "calculate": "计算",
            "file_read": "文件读取",
            "code_execute": "代码执行",
            "web_search": "网络搜索",
            "data_analysis": "数据分析",
            "image_generate": "图像生成",
            "text_summarize": "文本摘要",
        }

        display_name = tool_name_map.get(most_common_tool, most_common_tool)

        if count == 1:
            return f"使用 {display_name}"
        else:
            return f"使用 {display_name} ({count}次)"

    def _select_best_title(self, titles: List[str], original_message: str) -> str:
        """选择最佳标题"""
        # 移除空标题
        titles = [t for t in titles if t and t.strip()]

        if not titles:
            return self.config.default_title

        # 评分每个标题
        scores = []
        for title in titles:
            score = self._score_title(title, original_message)
            scores.append((score, title))

        # 选择最高分标题
        scores.sort(reverse=True)
        best_score, best_title = scores[0]

        return best_title

    def _score_title(self, title: str, original_message: str) -> float:
        """评估标题质量"""
        score = 0.0

        # 1. 长度合适性 (0-0.3分)
        title_len = len(title)
        if self.config.min_title_length <= title_len <= self.config.max_title_length:
            length_score = 1.0 - abs(title_len - 25) / 25  # 离25字符越近越好
            score += length_score * 0.3

        # 2. 信息量 (0-0.4分)
        # 检查是否包含原消息的关键词
        msg_keywords = set(
            self.keyword_extractor.extract(original_message, use_cache=False)
        )
        title_keywords = set(self.keyword_extractor.extract(title, use_cache=False))

        if msg_keywords:
            overlap = len(msg_keywords & title_keywords) / len(msg_keywords)
            score += overlap * 0.4

        # 3. 可读性 (0-0.3分)
        # 检查是否有明确的意图标记或格式
        if "：" in title or ":" in title or "关于" in title or "对话" in title:
            score += 0.3

        return min(1.0, score)


class TitleQualityEvaluator:
    """标题质量评估器"""

    def __init__(self, config: Optional[TitleGenerationConfig] = None):
        self.config = config or TitleGenerationConfig()

    def evaluate(
        self, title: str, original_message: str, intent: Optional[IntentType] = None
    ) -> Dict[str, float]:
        """评估标题质量"""
        scores = {}

        # 1. 简洁性评分 (0-1)
        scores["简洁性"] = self._evaluate_conciseness(title)

        # 2. 信息量评分 (0-1)
        scores["信息量"] = self._evaluate_informativeness(title, original_message)

        # 3. 可读性评分 (0-1)
        scores["可读性"] = self._evaluate_readability(title)

        # 4. 相关性评分 (0-1)
        scores["相关性"] = self._evaluate_relevance(title, original_message, intent)

        # 5. 格式规范性 (0-1)
        scores["格式规范"] = self._evaluate_format(title)

        # 综合评分（加权平均）
        weights = {
            "简洁性": 0.25,
            "信息量": 0.30,
            "可读性": 0.20,
            "相关性": 0.15,
            "格式规范": 0.10,
        }

        scores["综合评分"] = sum(scores[k] * weights[k] for k in weights)

        return scores

    def _evaluate_conciseness(self, title: str) -> float:
        """评估简洁性"""
        length = len(title)

        if length < self.config.min_title_length:
            return 0.3  # 太短

        if length > self.config.max_title_length:
            return 0.2  # 太长

        # 理想长度：15-35字符
        if 15 <= length <= 35:
            return 1.0

        # 接近理想长度
        if length < 15:
            return 0.5 + (length / 15) * 0.5
        else:  # length > 35
            return 1.0 - min((length - 35) / 15, 0.8)

    def _evaluate_informativeness(self, title: str, original_message: str) -> float:
        """评估信息量"""
        # 提取关键词
        extractor = KeywordExtractor(self.config)
        msg_keywords = set(extractor.extract(original_message, use_cache=False))
        title_keywords = set(extractor.extract(title, use_cache=False))

        if not msg_keywords:
            return 0.5  # 无法评估

        # 重叠率
        overlap = len(msg_keywords & title_keywords) / len(msg_keywords)

        # 同时考虑标题自身的信息密度
        word_count = len(title.split())
        if word_count == 0:
            return 0.0

        keyword_density = len(title_keywords) / word_count

        return overlap * 0.7 + keyword_density * 0.3

    def _evaluate_readability(self, title: str) -> float:
        """评估可读性"""
        score = 0.0

        # 检查是否有不自然的字符序列
        if re.search(r'[。，；：]["\']', title):
            score -= 0.2

        # 检查是否有重复的标点
        if re.search(r"[!?。，]{2,}", title):
            score -= 0.2

        # 检查是否有不完整的句子
        if title.endswith(("的", "了", "吗", "呢", "吧")) and len(title) < 10:
            score += 0.1

        # 检查是否有明确的格式
        if "：" in title or ":" in title:
            score += 0.3

        # 检查是否自然（中文）
        if self.config.language == "zh":
            # 简单的自然度检查：是否有常见的标题模式
            title_patterns = [
                r"^[搜索|创建|删除|修改|分析|询问|对话]：",
                r"^关于.+的对话$",
                r"^使用.+[工具|功能]",
                r"^.+[查询|计算|分析|处理]",
            ]

            for pattern in title_patterns:
                if re.search(pattern, title):
                    score += 0.2
                    break

        return min(1.0, max(0.0, 0.5 + score))

    def _evaluate_relevance(
        self, title: str, original_message: str, intent: Optional[IntentType]
    ) -> float:
        """评估相关性"""
        if not intent:
            return 0.5

        # 检查标题是否反映意图
        intent_keywords = self.config.intent_keywords.get(intent, set())

        title_lower = title.lower() if self.config.language != "zh" else title
        has_intent_keyword = any(keyword in title_lower for keyword in intent_keywords)

        if has_intent_keyword:
            return 0.8

        # 检查标题是否包含意图的显示表示
        if intent.value in title:
            return 0.9

        return 0.5

    def _evaluate_format(self, title: str) -> float:
        """评估格式规范性"""
        score = 1.0

        # 扣分项
        # 1. 开头或结尾有空格
        if title.startswith(" ") or title.endswith(" "):
            score -= 0.2

        # 2. 有多余的空格
        if "  " in title:
            score -= 0.1

        # 3. 有控制字符
        if any(ord(c) < 32 for c in title):
            score -= 0.3

        return max(0.0, score)


# ============================================================================
# 第四部分：完整测试系统与演示
# ============================================================================


class TitleMiddlewareTestSystem:
    """标题中间件测试系统"""

    def __init__(self):
        self.config = TitleGenerationConfig()
        self.middleware = TitleMiddleware(self.config)
        self.advanced_generator = AdvancedTitleGenerator(self.config)
        self.quality_evaluator = TitleQualityEvaluator(self.config)

        # 测试数据
        self.test_messages = [
            # 搜索类
            "帮我搜索一下Python异步编程的资料",
            "查找关于机器学习的教程",
            "找一下昨天的会议记录",
            # 创建类
            "如何用Python创建web服务器？",
            "新建一个用户配置文件",
            "创建一个数据分析报告模板",
            # 删除类
            "删除那个没用的文件",
            "移除过期的缓存数据",
            "清除系统日志文件",
            # 修改类
            "修改用户配置，把超时时间改成30秒",
            "更新系统设置，开启自动备份",
            "调整界面颜色为主题色",
            # 分析类
            "请帮我分析这个销售数据，按月份统计",
            "统计用户活跃度，按周分组",
            "分析系统性能指标，找出瓶颈",
            # 询问类
            "怎么安装Python包？",
            "什么是深度学习？",
            "为什么需要数据库索引？",
            # 对话类
            "随便聊聊天气",
            "今天有什么新闻？",
            "讲个笑话听听",
            # 混合类
            "帮我搜索然后分析一下这个数据",
            "创建并修改这个文档",
            "查找并删除重复文件",
            # 英文测试
            "help me search for python tutorial",
            "how to create a web server",
            "please analyze this data",
        ]

        self.conversation_examples = [
            [
                {"role": "user", "content": "帮我搜索Python异步编程"},
                {"role": "assistant", "content": "找到了这些资料..."},
                {"role": "user", "content": "哪个最适合初学者？"},
                {"role": "assistant", "content": "我推荐这个..."},
            ],
            [
                {"role": "user", "content": "分析销售数据"},
                {"role": "assistant", "content": "正在分析..."},
                {
                    "type": "tool_call",
                    "tool_name": "data_analysis",
                    "content": "调用数据分析工具",
                },
                {"role": "assistant", "content": "分析完成，这是结果..."},
            ],
            [
                {"role": "user", "content": "今天天气怎么样？"},
                {"role": "assistant", "content": "今天晴，25度"},
                {"role": "user", "content": "明天呢？"},
                {"role": "assistant", "content": "明天多云，23度"},
            ],
        ]

    async def run_basic_tests(self):
        """运行基础测试"""
        print("🧪 基础测试：TitleMiddleware基本功能")
        print("=" * 60)

        for i, message in enumerate(self.test_messages[:10], 1):
            print(f"\n测试 {i}: '{message}'")

            # 创建请求
            request = AgentRequest(
                user_id=f"test_user_{i}", session_id=f"session_{i}", message=message
            )

            # 通过中间件处理
            processed_request = await self.middleware.before_agent(request)

            # 获取生成的标题
            title_data = processed_request.metadata.get("generated_title", {})
            title = title_data.get("title", "无标题")
            intent = title_data.get("intent", "未知")

            print(f"  生成标题: '{title}'")
            print(f"  识别意图: {intent}")

            # 质量评估
            if title != "无标题":
                scores = self.quality_evaluator.evaluate(title, message)
                print(f"  质量评估: {scores['综合评分']:.2f}")

    async def run_advanced_tests(self):
        """运行高级测试"""
        print("\n\n🧠 高级测试：对话历史标题生成")
        print("=" * 60)

        for i, conversation in enumerate(self.conversation_examples, 1):
            print(f"\n对话示例 {i} ({len(conversation)} 条消息):")

            # 显示对话内容
            for msg in conversation[:3]:  # 只显示前3条
                role = msg.get("role", msg.get("type", "未知"))
                content = msg.get("content", "")[:50]
                print(f"  {role}: {content}{'...' if len(content) >= 50 else ''}")
            if len(conversation) > 3:
                print(f"  ... 还有 {len(conversation) - 3} 条消息")

            # 生成标题
            title_result = self.advanced_generator.generate_from_conversation(
                conversation
            )

            print(f"  生成标题: '{title_result.title}'")
            print(f"  生成策略: {title_result.strategy.value}")
            print(f"  置信度: {title_result.confidence:.2f}")

            # 质量评估
            first_user_msg = next(
                (m["content"] for m in conversation if m.get("role") == "user"), ""
            )
            scores = self.quality_evaluator.evaluate(
                title_result.title, first_user_msg, title_result.intent
            )
            print(f"  质量评估: {scores['综合评分']:.2f}")

    async def run_performance_tests(self):
        """运行性能测试"""
        print("\n\n⚡ 性能测试：处理速度和准确性")
        print("=" * 60)

        import time

        # 测试处理速度
        test_count = 50
        start_time = time.time()

        for i in range(test_count):
            message = self.test_messages[i % len(self.test_messages)]
            request = AgentRequest(
                user_id=f"perf_user_{i}",
                session_id=f"perf_session_{i}",
                message=message,
            )
            await self.middleware.before_agent(request)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / test_count * 1000  # 转换为毫秒

        print(f"处理 {test_count} 条消息耗时: {total_time:.3f}秒")
        print(f"平均每条消息: {avg_time:.2f}毫秒")

        # 测试准确性（人工评估样本）
        print("\n准确性测试（样本评估）:")
        sample_messages = [
            "帮我搜索一下Python异步编程的资料",
            "怎么安装Python包？",
            "随便聊聊天气",
            "删除那个没用的文件",
        ]

        for msg in sample_messages:
            result = self.advanced_generator.generate(msg)
            scores = self.quality_evaluator.evaluate(result.title, msg, result.intent)

            print(
                f"  '{msg[:30]}...' -> '{result.title}' (评分: {scores['综合评分']:.2f})"
            )

    async def run_integration_demo(self):
        """运行集成演示"""
        print("\n\n🚀 集成演示：完整工作流程")
        print("=" * 60)

        # 模拟一个完整的对话流程
        print("\n1. 用户发起对话:")
        user_message = "帮我分析一下上个月的销售数据，按产品和地区分组"
        print(f"   用户: {user_message}")

        # 创建请求
        request = AgentRequest(
            user_id="demo_user", session_id="demo_session_123", message=user_message
        )

        # 中间件处理（生成标题）
        print("\n2. TitleMiddleware处理:")
        processed_request = await self.middleware.before_agent(request)
        title_data = processed_request.metadata.get("generated_title", {})
        print(f"   生成标题: '{title_data.get('title', '')}'")
        print(f"   识别意图: {title_data.get('intent', '')}")

        # 模拟Agent处理
        print("\n3. Agent处理请求...")
        await asyncio.sleep(0.5)  # 模拟处理时间

        # 创建响应
        response = AgentResponse(
            thread_id="thread_12345",
            message="已分析上个月销售数据，按产品和地区分组的结果如下...",
        )
        response.metadata = processed_request.metadata

        # 中间件后处理（保存标题）
        print("\n4. 保存标题到对话记录:")
        saved_response = await self.middleware.after_agent(response)

        # 模拟后续操作
        print("\n5. 后续操作演示:")

        # 获取标题
        stored_title = await self.middleware.get_title("thread_12345")
        if stored_title:
            print(f"   获取对话标题: '{stored_title.get('title', '')}'")

        # 更新标题（用户编辑）
        new_title = "销售数据分析：上月产品地区分布"
        success = await self.middleware.update_title("thread_12345", new_title)
        if success:
            print(f"   用户更新标题为: '{new_title}'")

        # 列出所有标题
        print("\n6. 对话标题列表:")
        titles = await self.middleware.list_titles(limit=3)
        for i, title_info in enumerate(titles, 1):
            title = title_info.get("title", "无标题")
            created = time.strftime(
                "%H:%M:%S", time.localtime(title_info.get("created_at", 0))
            )
            print(f"   {i}. '{title}' (创建于: {created})")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🎓 Day 5 Lesson 19: TitleMiddleware - 完整测试套件")
        print("=" * 80)

        await self.run_basic_tests()
        await self.run_advanced_tests()
        await self.run_performance_tests()
        await self.run_integration_demo()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")


# ============================================================================
# 主函数：运行演示
# ============================================================================


async def main_demo():
    """主演示函数"""
    test_system = TitleMiddlewareTestSystem()

    try:
        await test_system.run_all_tests()

        # 额外的示例：显示配置选项
        print("\n\n🔧 配置选项示例:")
        print("-" * 40)

        # 创建不同配置的生成器
        configs = [
            ("基础配置", TitleGenerationConfig()),
            ("英文配置", TitleGenerationConfig(language="en")),
            ("详细配置", TitleGenerationConfig(max_title_length=60, keyword_limit=8)),
            ("简洁配置", TitleGenerationConfig(max_title_length=30, keyword_limit=3)),
        ]

        test_message = "帮我搜索一下Python机器学习的教程"

        for config_name, config in configs:
            generator = BaseTitleGenerator(config)
            result = generator.generate(test_message)

            print(f"{config_name}:")
            print(f"  标题: '{result.title}'")
            print(f"  长度: {len(result.title)} 字符")
            print(f"  关键词: {result.keywords[:3]}")
            print()

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main_demo())
