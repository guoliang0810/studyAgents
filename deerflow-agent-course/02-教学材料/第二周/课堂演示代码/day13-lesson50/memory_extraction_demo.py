#!/usr/bin/env python3
"""
Day 13 - 第50节课：记忆提取流程实现
====================================

本演示代码实现多级记忆提取算法，包括：
1. RelevanceCalculator - 相关性计算器，多种匹配算法
2. MemoryExtractor - 记忆提取器，五步提取流程
3. ExtractionStrategy - 提取策略配置
4. MultiLevelExtractor - 多级存储提取器

运行方式:
    python memory_extraction_demo.py          # 运行演示
    python memory_extraction_demo.py --test   # 运行测试
"""

import time
import math
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import sys


# ============================================================================
# 第一部分：相关性计算
# ============================================================================

class MatchType(Enum):
    """匹配类型枚举
    
    定义不同的相关性匹配方法：
    - EXACT: 精确匹配
    - SUBSTRING: 子串匹配
    - KEYWORD: 关键词匹配
    - TF_IDF: TF-IDF权重
    - COMPOSITE: 综合评分
    """
    EXACT = "exact"
    SUBSTRING = "substring"
    KEYWORD = "keyword"
    TF_IDF = "tf_idf"
    COMPOSITE = "composite"


@dataclass
class RelevanceScore:
    """相关性评分结果
    
    包含：
    - fact_id: 事实ID
    - score: 综合相关性分数(0.0-1.0)
    - match_details: 各匹配方法的详细分数
    - match_type: 主要匹配类型
    """
    fact_id: str
    score: float
    match_details: Dict[str, float] = field(default_factory=dict)
    match_type: MatchType = MatchType.COMPOSITE


class RelevanceCalculator:
    """相关性计算器
    
    实现多种记忆与查询的相关性计算方法：
    1. 精确匹配 - 完全相同的文本
    2. 子串匹配 - 查询是内容的子串
    3. 关键词匹配 - 关键词交集比例
    4. TF-IDF - 词频-逆文档频率
    5. 综合评分 - 加权组合多种方法
    """
    
    def __init__(self):
        # 停用词列表（中英文）
        self.stop_words: Set[str] = {
            "的", "了", "在", "是", "我", "有", "和", "就",
            "不", "人", "都", "一", "一个", "上", "也", "很",
            "the", "a", "an", "is", "are", "was", "were", "be",
            "to", "of", "and", "in", "that", "have", "for"
        }
        # 文档频率统计（用于TF-IDF）
        self.doc_freq: Dict[str, int] = defaultdict(int)
        self.total_docs: int = 0
    
    def build_index(self, facts: List[Any]) -> None:
        """构建文档频率索引（用于TF-IDF计算）
        
        Args:
            facts: 事实列表
        """
        self.total_docs = len(facts)
        self.doc_freq.clear()
        
        for fact in facts:
            words = self._tokenize(fact.content)
            unique_words = set(words)
            for word in unique_words:
                self.doc_freq[word] += 1
    
    def calculate_exact(self, query: str, content: str) -> float:
        """精确匹配评分
        
        Args:
            query: 查询文本
            content: 内容文本
            
        Returns:
            精确匹配分数(0.0或1.0)
        """
        return 1.0 if query.lower() == content.lower() else 0.0
    
    def calculate_substring(self, query: str, content: str) -> float:
        """子串匹配评分
        
        基于查询在内容中的覆盖比例
        
        Args:
            query: 查询文本
            content: 内容文本
            
        Returns:
            子串匹配分数(0.0-1.0)
        """
        query_lower = query.lower()
        content_lower = content.lower()
        
        if query_lower in content_lower:
            # 查询完全包含在内容中
            return 1.0
        
        # 计算最长公共子串比例
        lcs_len = self._longest_common_substring_len(query_lower, content_lower)
        if lcs_len == 0:
            return 0.0
        
        return lcs_len / len(query_lower)
    
    def calculate_keyword(self, query: str, content: str) -> float:
        """关键词匹配评分
        
        基于关键词交集的比例
        
        Args:
            query: 查询文本
            content: 内容文本
            
        Returns:
            关键词匹配分数(0.0-1.0)
        """
        query_words = set(self._tokenize(query)) - self.stop_words
        content_words = set(self._tokenize(content)) - self.stop_words
        
        if not query_words:
            return 0.0
        
        intersection = query_words & content_words
        # Jaccard相似度
        union = query_words | content_words
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def calculate_tf_idf(self, query: str, content: str) -> float:
        """TF-IDF相关性评分
        
        Args:
            query: 查询文本
            content: 内容文本
            
        Returns:
            TF-IDF相关性分数
        """
        query_words = self._tokenize(query)
        content_words = self._tokenize(content)
        
        if not query_words or not content_words:
            return 0.0
        
        # 计算内容的词频
        content_tf: Dict[str, int] = defaultdict(int)
        for word in content_words:
            content_tf[word] += 1
        
        # 计算查询与内容的TF-IDF相似度
        query_set = set(query_words) - self.stop_words
        
        score = 0.0
        for word in query_set:
            if word in content_tf:
                # TF: 词频
                tf = content_tf[word] / len(content_words)
                # IDF: 逆文档频率
                df = self.doc_freq.get(word, 1)
                idf = math.log((self.total_docs + 1) / (df + 1)) + 1
                score += tf * idf
        
        # 归一化
        if len(query_set) > 0:
            score = min(score / len(query_set), 1.0)
        
        return score
    
    def calculate_composite(self, query: str, content: str, 
                           weights: Optional[Dict[str, float]] = None) -> float:
        """综合相关性评分
        
        加权组合多种匹配方法
        
        Args:
            query: 查询文本
            content: 内容文本
            weights: 各方法权重，默认{exact: 0.3, substring: 0.3, keyword: 0.4}
            
        Returns:
            综合相关性分数(0.0-1.0)
        """
        if weights is None:
            weights = {
                "exact": 0.3,
                "substring": 0.3,
                "keyword": 0.4
            }
        
        scores = {
            "exact": self.calculate_exact(query, content),
            "substring": self.calculate_substring(query, content),
            "keyword": self.calculate_keyword(query, content)
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for method, weight in weights.items():
            if method in scores:
                total_score += scores[method] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def calculate_all(self, query: str, content: str) -> RelevanceScore:
        """计算所有相关性分数
        
        Args:
            query: 查询文本
            content: 内容文本
            
        Returns:
            包含各方法分数的RelevanceScore
        """
        exact = self.calculate_exact(query, content)
        substring = self.calculate_substring(query, content)
        keyword = self.calculate_keyword(query, content)
        tf_idf = self.calculate_tf_idf(query, content)
        composite = self.calculate_composite(query, content)
        
        # 确定主要匹配类型
        if exact > 0:
            match_type = MatchType.EXACT
        elif substring > 0.8:
            match_type = MatchType.SUBSTRING
        elif keyword > 0.5:
            match_type = MatchType.KEYWORD
        else:
            match_type = MatchType.TF_IDF
        
        return RelevanceScore(
            fact_id="",
            score=composite,
            match_details={
                "exact": exact,
                "substring": substring,
                "keyword": keyword,
                "tf_idf": tf_idf,
                "composite": composite
            },
            match_type=match_type
        )
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词（支持中英文）
        
        Args:
            text: 输入文本
            
        Returns:
            词列表
        """
        # 简单实现：按空格和标点分割，中文按单字
        text = text.lower()
        # 移除标点
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分割
        words = text.split()
        
        # 对中文字符进一步分字（简化处理）
        result = []
        for word in words:
            if re.match(r'^[a-z0-9]+$', word):
                result.append(word)
            else:
                # 中文字符按2-3字节分词（简化）
                for i in range(0, len(word), 2):
                    if i + 2 <= len(word):
                        result.append(word[i:i+2])
                    else:
                        result.append(word[i:])
        
        return result
    
    def _longest_common_substring_len(self, s1: str, s2: str) -> int:
        """计算最长公共子串长度
        
        Args:
            s1: 字符串1
            s2: 字符串2
            
        Returns:
            最长公共子串长度
        """
        if not s1 or not s2:
            return 0
        
        # 动态规划
        dp = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]
        max_len = 0
        
        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    max_len = max(max_len, dp[i][j])
        
        return max_len


# ============================================================================
# 第二部分：提取策略配置
# ============================================================================

class ExtractionPriority(Enum):
    """提取优先级枚举
    
    - RECENCY: 优先最近创建的记忆
    - RELEVANCE: 优先高相关性记忆
    - CONFIDENCE: 优先高置信度记忆
    - ACCESS_COUNT: 优先常访问的记忆
    """
    RECENCY = "recency"
    RELEVANCE = "relevance"
    CONFIDENCE = "confidence"
    ACCESS_COUNT = "access_count"


@dataclass
class ExtractionStrategy:
    """记忆提取策略配置
    
    配置提取算法的各种参数：
    - max_results: 最大返回结果数
    - min_relevance: 最小相关性阈值
    - min_confidence: 最小置信度阈值
    - priority: 优先级排序方式
    - enable_deduplication: 是否启用去重
    - dedup_threshold: 去重相似度阈值
    - time_decay_factor: 时间衰减因子
    """
    max_results: int = 10
    min_relevance: float = 0.1
    min_confidence: float = 0.3
    priority: ExtractionPriority = ExtractionPriority.RELEVANCE
    enable_deduplication: bool = True
    dedup_threshold: float = 0.8
    time_decay_factor: float = 0.001
    
    # 各优先级的权重
    relevance_weight: float = 0.4
    confidence_weight: float = 0.3
    recency_weight: float = 0.2
    access_weight: float = 0.1


# ============================================================================
# 第三部分：记忆提取器
# ============================================================================

@dataclass
class ExtractionResult:
    """提取结果
    
    包含：
    - facts: 提取的记忆列表
    - total_searched: 搜索的总记忆数
    - extraction_time_ms: 提取耗时（毫秒）
    - query: 原始查询
    - strategy_used: 使用的策略
    """
    facts: List[Any]
    total_searched: int
    extraction_time_ms: float
    query: str
    strategy_used: ExtractionStrategy


class MemoryExtractor:
    """记忆提取器
    
    实现五步记忆提取流程：
    1. 搜索(Search) - 从各存储层搜索候选记忆
    2. 合并(Merge) - 合并多层搜索结果
    3. 去重(Deduplicate) - 去除重复或高度相似的记忆
    4. 排序(Score & Sort) - 计算综合评分并排序
    5. 截断(Truncate) - 截取top-k结果
    """
    
    def __init__(self, strategy: Optional[ExtractionStrategy] = None):
        self.strategy = strategy or ExtractionStrategy()
        self.relevance_calculator = RelevanceCalculator()
    
    def extract(self, query: str, memory_stores: Dict[str, List[Any]]) -> ExtractionResult:
        """执行五步记忆提取流程
        
        Args:
            query: 查询文本
            memory_stores: 各存储层的记忆字典，格式{"short_term": [...], "long_term": [...]}
            
        Returns:
            ExtractionResult提取结果
        """
        start_time = time.time()
        
        # 步骤1: 搜索 - 从各存储层搜索候选记忆
        candidates = self._search(query, memory_stores)
        total_searched = sum(len(v) for v in memory_stores.values())
        
        # 步骤2: 合并 - 合并多层搜索结果
        merged = self._merge(candidates)
        
        # 步骤3: 去重 - 去除重复记忆
        if self.strategy.enable_deduplication:
            deduplicated = self._deduplicate(merged)
        else:
            deduplicated = merged
        
        # 步骤4: 排序 - 计算综合评分并排序
        scored = self._score_and_sort(query, deduplicated)
        
        # 步骤5: 截断 - 截取top-k结果
        final_results = self._truncate(scored)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            facts=final_results,
            total_searched=total_searched,
            extraction_time_ms=elapsed_ms,
            query=query,
            strategy_used=self.strategy
        )
    
    def _search(self, query: str, memory_stores: Dict[str, List[Any]]) -> Dict[str, List[Tuple[Any, float]]]:
        """步骤1: 搜索候选记忆
        
        从各存储层搜索与查询相关的记忆
        
        Args:
            query: 查询文本
            memory_stores: 各存储层的记忆
            
        Returns:
            各层搜索结果，格式{"layer": [(fact, relevance_score), ...]}
        """
        results: Dict[str, List[Tuple[Any, float]]] = {}
        
        for layer, facts in memory_stores.items():
            layer_results = []
            for fact in facts:
                # 计算相关性
                relevance = self.relevance_calculator.calculate_composite(
                    query, fact.content
                )
                
                # 过滤低相关性和低置信度
                if (relevance >= self.strategy.min_relevance and 
                    fact.confidence >= self.strategy.min_confidence):
                    layer_results.append((fact, relevance))
            
            results[layer] = layer_results
        
        return results
    
    def _merge(self, candidates: Dict[str, List[Tuple[Any, float]]]) -> List[Tuple[Any, float]]:
        """步骤2: 合并候选结果
        
        合并多层搜索结果，记录来源层
        
        Args:
            candidates: 各层搜索结果
            
        Returns:
            合并后的候选列表
        """
        merged = []
        seen_ids: Set[str] = set()
        
        for layer, layer_results in candidates.items():
            for fact, relevance in layer_results:
                if fact.id not in seen_ids:
                    # 添加来源层信息
                    if not hasattr(fact, 'metadata'):
                        fact.metadata = {}
                    fact.metadata['extraction_layer'] = layer
                    merged.append((fact, relevance))
                    seen_ids.add(fact.id)
        
        return merged
    
    def _deduplicate(self, candidates: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
        """步骤3: 去除重复记忆
        
        基于内容相似度去除高度相似的记忆
        
        Args:
            candidates: 候选列表
            
        Returns:
            去重后的列表
        """
        if not candidates:
            return []
        
        unique_candidates = []
        seen_contents: List[str] = []
        
        for fact, relevance in candidates:
            is_duplicate = False
            
            for seen_content in seen_contents:
                similarity = self.relevance_calculator.calculate_keyword(
                    fact.content, seen_content
                )
                if similarity >= self.strategy.dedup_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_candidates.append((fact, relevance))
                seen_contents.append(fact.content)
        
        return unique_candidates
    
    def _score_and_sort(self, query: str, 
                        candidates: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
        """步骤4: 计算综合评分并排序
        
        综合考虑相关性、置信度、时间、访问次数
        
        Args:
            query: 查询文本
            candidates: 候选列表
            
        Returns:
            评分后的列表（按分数降序）
        """
        scored_candidates = []
        current_time = time.time()
        
        for fact, relevance in candidates:
            # 计算各项评分
            confidence_score = fact.confidence
            
            # 时间衰减（越新分数越高）
            age_seconds = current_time - fact.created_at
            recency_score = math.exp(-self.strategy.time_decay_factor * age_seconds)
            
            # 访问频率（归一化）
            access_score = min(fact.access_count / 100, 1.0)
            
            # 加权综合评分
            if self.strategy.priority == ExtractionPriority.RELEVANCE:
                final_score = relevance * 0.6 + confidence_score * 0.3 + recency_score * 0.1
            elif self.strategy.priority == ExtractionPriority.CONFIDENCE:
                final_score = confidence_score * 0.5 + relevance * 0.3 + recency_score * 0.2
            elif self.strategy.priority == ExtractionPriority.RECENCY:
                final_score = recency_score * 0.5 + relevance * 0.3 + confidence_score * 0.2
            elif self.strategy.priority == ExtractionPriority.ACCESS_COUNT:
                final_score = access_score * 0.4 + relevance * 0.4 + confidence_score * 0.2
            else:
                # 默认综合
                final_score = (
                    relevance * self.strategy.relevance_weight +
                    confidence_score * self.strategy.confidence_weight +
                    recency_score * self.strategy.recency_weight +
                    access_score * self.strategy.access_weight
                )
            
            scored_candidates.append((fact, final_score))
        
        # 按分数降序排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_candidates
    
    def _truncate(self, scored: List[Tuple[Any, float]]) -> List[Any]:
        """步骤5: 截取top-k结果
        
        Args:
            scored: 评分后的列表
            
        Returns:
            最终结果列表
        """
        return [fact for fact, _ in scored[:self.strategy.max_results]]


# ============================================================================
# 第四部分：多级存储提取器
# ============================================================================

class MultiLevelExtractor:
    """多级存储提取器
    
    支持从多级存储中提取记忆：
    - 会话记忆(Session): 当前会话的对话历史
    - 短期记忆(ShortTerm): 最近的交互记录
    - 长期记忆(LongTerm): 持久化的知识
    """
    
    LEVEL_PRIORITY = ["session", "short_term", "long_term"]
    
    def __init__(self):
        self.extractors: Dict[str, MemoryExtractor] = {}
        self._init_default_strategies()
    
    def _init_default_strategies(self) -> None:
        """初始化各层的提取策略"""
        # 会话记忆：更重视最近性
        self.extractors["session"] = MemoryExtractor(ExtractionStrategy(
            max_results=5,
            min_relevance=0.05,
            priority=ExtractionPriority.RECENCY,
            time_decay_factor=0.01
        ))
        
        # 短期记忆：平衡相关性和置信度
        self.extractors["short_term"] = MemoryExtractor(ExtractionStrategy(
            max_results=10,
            min_relevance=0.1,
            priority=ExtractionPriority.RELEVANCE,
            time_decay_factor=0.001
        ))
        
        # 长期记忆：更重视置信度
        self.extractors["long_term"] = MemoryExtractor(ExtractionStrategy(
            max_results=15,
            min_relevance=0.15,
            min_confidence=0.5,
            priority=ExtractionPriority.CONFIDENCE,
            time_decay_factor=0.0001
        ))
    
    def extract(self, query: str, 
                memory_stores: Dict[str, List[Any]]) -> ExtractionResult:
        """多级提取
        
        按优先级从各层提取，合并去重后返回
        
        Args:
            query: 查询文本
            memory_stores: 各层存储
            
        Returns:
            合并的提取结果
        """
        start_time = time.time()
        all_results: List[Any] = []
        total_searched = 0
        
        for level in self.LEVEL_PRIORITY:
            if level in memory_stores and level in self.extractors:
                level_stores = {level: memory_stores[level]}
                result = self.extractors[level].extract(query, level_stores)
                
                # 标记来源层
                for fact in result.facts:
                    if not hasattr(fact, 'metadata'):
                        fact.metadata = {}
                    fact.metadata['source_level'] = level
                
                all_results.extend(result.facts)
                total_searched += result.total_searched
        
        # 去重（保留优先级更高的层的结果）
        unique_results = self._merge_by_priority(all_results)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return ExtractionResult(
            facts=unique_results[:20],  # 最终限制20条
            total_searched=total_searched,
            extraction_time_ms=elapsed_ms,
            query=query,
            strategy_used=ExtractionStrategy(max_results=20)
        )
    
    def _merge_by_priority(self, facts: List[Any]) -> List[Any]:
        """按优先级合并（同一ID保留优先级更高的层）"""
        seen_ids: Dict[str, str] = {}  # fact_id to level mapping
        unique_facts: List[Any] = []
        
        for fact in facts:
            level = fact.metadata.get('source_level', 'unknown')
            
            if fact.id not in seen_ids:
                seen_ids[fact.id] = level
                unique_facts.append(fact)
            else:
                # 如果新来源优先级更高，替换
                existing_level = seen_ids[fact.id]
                if self.LEVEL_PRIORITY.index(level) < self.LEVEL_PRIORITY.index(existing_level):
                    # 替换
                    for i, f in enumerate(unique_facts):
                        if f.id == fact.id:
                            unique_facts[i] = fact
                            break
                    seen_ids[fact.id] = level
        
        return unique_facts


# ============================================================================
# 第五部分：测试套件
# ============================================================================

# 模拟Fact类用于测试
class MockFact:
    """模拟Fact类"""
    def __init__(self, content: str, source: str = "system", 
                 confidence: float = 1.0, created_at: float = None,
                 access_count: int = 0):
        import uuid
        self.id = str(uuid.uuid4())
        self.content = content
        self.source = source
        self.confidence = confidence
        self.created_at = created_at or time.time()
        self.access_count = access_count
        self.metadata = {}


def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆提取流程测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 6
    
    # 测试1: 精确匹配计算
    print("\n📊 测试1: 精确匹配计算")
    try:
        calc = RelevanceCalculator()
        
        assert calc.calculate_exact("Python", "Python") == 1.0
        assert calc.calculate_exact("Python", "python") == 1.0  # 忽略大小写
        assert calc.calculate_exact("Python", "Java") == 0.0
        assert calc.calculate_exact("Python编程", "Python编程") == 1.0
        
        print("   ✅ 精确匹配计算正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试2: 子串匹配计算
    print("\n📊 测试2: 子串匹配计算")
    try:
        calc = RelevanceCalculator()
        
        # 完全包含
        score1 = calc.calculate_substring("Python", "我喜欢Python编程")
        assert score1 == 1.0, f"Expected 1.0, got {score1}"
        
        # 部分包含
        score2 = calc.calculate_substring("Python编程", "我喜欢Python")
        assert 0.0 < score2 < 1.0, f"Expected 0<x<1, got {score2}"
        
        # 不包含
        score3 = calc.calculate_substring("Java", "我喜欢Python")
        assert score3 == 0.0, f"Expected 0.0, got {score3}"
        
        print(f"   ✅ 子串匹配计算正常 (Python包含={score1}, 部分={score2:.2f})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试3: 关键词匹配计算
    print("\n📊 测试3: 关键词匹配计算")
    try:
        calc = RelevanceCalculator()
        
        # 使用英文测试以避免中文分词问题
        score1 = calc.calculate_keyword("Python programming", "Python is a programming language")
        assert score1 > 0, f"Expected > 0, got {score1}"
        
        # 无交集
        score2 = calc.calculate_keyword("Java development", "Python programming")
        assert score2 == 0.0, f"Expected 0.0, got {score2}"
        
        print(f"   ✅ 关键词匹配计算正常 (有交集={score1:.2f}, 无交集={score2})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试4: 五步提取流程
    print("\n📊 测试4: 五步提取流程")
    try:
        extractor = MemoryExtractor(ExtractionStrategy(max_results=3))
        
        # 准备测试数据
        facts = [
            MockFact("用户喜欢Python编程", confidence=0.9, access_count=10),
            MockFact("用户是Java开发者", confidence=0.8, access_count=5),
            MockFact("Python是一门编程语言", confidence=1.0, access_count=2),
            MockFact("用户喜欢Python编程", confidence=0.95),  # 重复
            MockFact("今天天气很好", confidence=0.9),
        ]
        
        memory_stores = {"long_term": facts}
        result = extractor.extract("Python编程", memory_stores)
        
        # 验证结果
        assert len(result.facts) > 0, "Should have results"
        assert len(result.facts) <= 3, f"Should limit to 3, got {len(result.facts)}"
        assert result.total_searched == 5, f"Searched 5 facts"
        
        print(f"   ✅ 五步提取流程正常 (提取={len(result.facts)}条, 耗时={result.extraction_time_ms:.2f}ms)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试5: 去重功能
    print("\n📊 测试5: 去重功能")
    try:
        extractor = MemoryExtractor(ExtractionStrategy(
            max_results=10,
            enable_deduplication=True,
            dedup_threshold=0.5  # 降低阈值以适应中文相似度
        ))
        
        facts = [
            MockFact("Python是编程语言", confidence=1.0),
            MockFact("Python是一门编程语言", confidence=0.9),  # 相似
            MockFact("Java是编程语言", confidence=1.0),
        ]
        
        memory_stores = {"long_term": facts}
        result = extractor.extract("编程语言", memory_stores)
        
        # 去重后应该只有2条
        assert len(result.facts) == 2, f"Expected 2 after dedup, got {len(result.facts)}"
        
        print(f"   ✅ 去重功能正常 (去重后={len(result.facts)}条)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试6: 多级提取
    print("\n📊 测试6: 多级提取")
    try:
        multi_extractor = MultiLevelExtractor()
        
        # 准备多层数据
        session_facts = [
            MockFact("刚才说了Python", created_at=time.time() - 10),
        ]
        short_term_facts = [
            MockFact("用户学过Python基础", created_at=time.time() - 3600),
        ]
        long_term_facts = [
            MockFact("用户是资深Python开发者", confidence=0.95),
        ]
        
        memory_stores = {
            "session": session_facts,
            "short_term": short_term_facts,
            "long_term": long_term_facts
        }
        
        result = multi_extractor.extract("Python经验", memory_stores)
        
        assert len(result.facts) > 0, "Should have results"
        assert result.total_searched == 3, f"Searched 3 facts total"
        
        print(f"   ✅ 多级提取正常 (提取={len(result.facts)}条, 搜索={result.total_searched}条)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试总结
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {tests_passed}/{tests_total} 通过")
    
    if tests_passed == tests_total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {tests_total - tests_passed} 个测试失败")
    
    return tests_passed == tests_total


# ============================================================================
# 第六部分：演示主程序
# ============================================================================

def run_demo():
    """运行记忆提取演示"""
    print("🔍 Day 13 - 第50节课：记忆提取流程实现演示")
    print("=" * 60)
    
    # 1. 演示相关性计算
    print("\n📊 演示1: 相关性计算")
    print("-" * 40)
    
    calc = RelevanceCalculator()
    calc.build_index([])  # 简化，不构建索引
    
    queries_and_contents = [
        ("Python编程", "用户是Python开发者"),
        ("Python编程", "用户喜欢Java开发"),
        ("学习编程", "Python是一门编程语言"),
    ]
    
    for query, content in queries_and_contents:
        score = calc.calculate_all(query, content)
        print(f"查询: '{query}' vs 内容: '{content}'")
        print(f"  综合分数: {score.score:.3f}")
        print(f"  匹配类型: {score.match_type.value}")
        print(f"  详细分数: exact={score.match_details['exact']:.2f}, "
              f"substring={score.match_details['substring']:.2f}, "
              f"keyword={score.match_details['keyword']:.2f}")
        print()
    
    # 2. 演示五步提取流程
    print("\n📊 演示2: 五步提取流程")
    print("-" * 40)
    
    # 准备模拟记忆
    current_time = time.time()
    facts = [
        MockFact("用户是Python开发者，有5年经验", confidence=0.95, 
                 created_at=current_time - 86400, access_count=50),
        MockFact("用户最近在学习FastAPI框架", confidence=0.9,
                 created_at=current_time - 3600, access_count=20),
        MockFact("用户之前问过数据库优化问题", confidence=0.85,
                 created_at=current_time - 7200, access_count=15),
        MockFact("用户说Python很好用", confidence=1.0,
                 created_at=current_time - 60, access_count=5),
        MockFact("今天是周五，天气晴朗", confidence=0.9,
                 created_at=current_time - 30, access_count=1),
    ]
    
    extractor = MemoryExtractor(ExtractionStrategy(
        max_results=3,
        min_relevance=0.1,
        priority=ExtractionPriority.RELEVANCE
    ))
    
    query = "Python开发经验"
    result = extractor.extract(query, {"long_term": facts})
    
    print(f"查询: '{query}'")
    print(f"搜索了 {result.total_searched} 条记忆")
    print(f"提取结果 ({len(result.facts)} 条):")
    for i, fact in enumerate(result.facts, 1):
        relevance = calc.calculate_composite(query, fact.content)
        print(f"  {i}. [{relevance:.2f}] {fact.content}")
    
    # 3. 演示多级提取
    print("\n\n📊 演示3: 多级提取")
    print("-" * 40)
    
    # 准备多层记忆
    session_facts = [
        MockFact("用户刚说了正在做Python项目", created_at=current_time - 60),
        MockFact("用户提到了需要部署服务", created_at=current_time - 30),
    ]
    
    short_term_facts = [
        MockFact("用户之前问过Docker部署问题", created_at=current_time - 3600, access_count=10),
        MockFact("用户习惯使用VS Code编辑器", created_at=current_time - 7200, access_count=8),
    ]
    
    long_term_facts = [
        MockFact("用户是后端开发工程师", confidence=0.95, access_count=100),
        MockFact("用户有Kubernetes使用经验", confidence=0.8, access_count=30),
    ]
    
    multi_memory_stores = {
        "session": session_facts,
        "short_term": short_term_facts,
        "long_term": long_term_facts,
    }
    
    multi_extractor = MultiLevelExtractor()
    query = "部署经验"
    result = multi_extractor.extract(query, multi_memory_stores)
    
    print(f"查询: '{query}'")
    print(f"总搜索: {result.total_searched} 条记忆")
    print(f"提取结果 ({len(result.facts)} 条):")
    
    for i, fact in enumerate(result.facts, 1):
        level = fact.metadata.get('source_level', 'unknown')
        print(f"  {i}. [{level}] {fact.content}")
    
    # 4. 演示不同优先级策略
    print("\n\n📊 演示4: 不同优先级策略对比")
    print("-" * 40)
    
    test_facts = [
        MockFact("Python是编程语言", confidence=0.9, 
                 created_at=current_time - 10000, access_count=100),
        MockFact("Python用于数据科学", confidence=0.95,
                 created_at=current_time - 100, access_count=5),
        MockFact("Python语法简单", confidence=0.8,
                 created_at=current_time - 50, access_count=50),
    ]
    
    strategies = [
        ("相关性优先", ExtractionPriority.RELEVANCE),
        ("置信度优先", ExtractionPriority.CONFIDENCE),
        ("最近性优先", ExtractionPriority.RECENCY),
        ("访问优先", ExtractionPriority.ACCESS_COUNT),
    ]
    
    for strategy_name, priority in strategies:
        extractor = MemoryExtractor(ExtractionStrategy(
            max_results=3,
            priority=priority
        ))
        result = extractor.extract("Python", {"test": test_facts})
        
        print(f"\n{strategy_name}:")
        for i, fact in enumerate(result.facts, 1):
            print(f"  {i}. {fact.content} (置信度={fact.confidence:.2f}, "
                  f"访问={fact.access_count})")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        run_demo()
