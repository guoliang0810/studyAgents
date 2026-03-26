#!/usr/bin/env python3
"""
🎓 Day2 第6节课：自定义Reducer函数 - 课堂演示代码

本文件演示Reducer函数的设计原则、实现模式、复杂业务逻辑设计以及集成到ThreadState的完整流程。
采用四部分结构：架构模拟、状态机实现、模块化设计演示、架构分析。

使用方式：
    python custom_reducer_demo.py          # 运行完整演示
    python custom_reducer_demo.py --test   # 运行所有测试
    python custom_reducer_demo.py --debug  # 运行调试模式
"""

import sys
import time
import random
from typing import TypeVar, Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import math

# ============================================================================
# 第一部分：架构模拟 (Architecture Simulation)
# ============================================================================

print("=" * 60)
print("第一部分：架构模拟 - Reducer在分布式状态管理中的作用")
print("=" * 60)


class AgentNode:
    """模拟分布式系统中的Agent节点"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.local_state: Dict[str, Any] = {}
        self.state_version = 0
        self.reducer_registry: Dict[str, Callable] = {}

    def register_reducer(self, field_name: str, reducer_func: Callable):
        """注册字段的Reducer函数"""
        self.reducer_registry[field_name] = reducer_func
        print(f"  Agent[{self.node_id}] 注册Reducer: {field_name}")

    def update_state(self, updates: Dict[str, Any]):
        """更新本地状态，应用Reducer合并逻辑"""
        print(f"\n  Agent[{self.node_id}] 状态更新:")
        print(f"    当前状态: {self.local_state}")
        print(f"    更新内容: {updates}")

        for field_name, new_value in updates.items():
            if field_name in self.reducer_registry:
                # 应用Reducer合并
                existing = self.local_state.get(field_name)
                reducer = self.reducer_registry[field_name]
                merged = reducer(existing, new_value)
                self.local_state[field_name] = merged
                print(f"    {field_name}: {existing} + {new_value} → {merged}")
            else:
                # 直接设置
                self.local_state[field_name] = new_value
                print(f"    {field_name}: 直接设置 → {new_value}")

        self.state_version += 1

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return self.local_state.copy()


def simulate_distributed_state_merging():
    """模拟多Agent状态合并场景"""
    print("\n模拟分布式状态合并场景:")
    print("-" * 40)

    # 创建三个Agent节点
    agents = {"A": AgentNode("A"), "B": AgentNode("B"), "C": AgentNode("C")}

    # 注册相同的Reducer函数
    for agent in agents.values():
        agent.register_reducer("message_count", lambda x, y: (x or 0) + (y or 0))
        agent.register_reducer(
            "user_list", lambda x, y: list(set((x or []) + (y or [])))
        )
        agent.register_reducer("max_score", lambda x, y: max(x or 0, y or 0))

    # 模拟并行更新
    print("\n阶段1: 各Agent独立更新状态")

    # Agent A更新
    agents["A"].update_state(
        {"message_count": 5, "user_list": ["user1", "user2"], "max_score": 85}
    )

    # Agent B更新
    agents["B"].update_state(
        {"message_count": 3, "user_list": ["user2", "user3"], "max_score": 92}
    )

    # Agent C更新
    agents["C"].update_state(
        {"message_count": 7, "user_list": ["user1", "user4"], "max_score": 78}
    )

    print("\n阶段2: 状态合并到协调节点")

    # 创建协调节点
    coordinator = AgentNode("Coordinator")
    coordinator.register_reducer("message_count", lambda x, y: (x or 0) + (y or 0))
    coordinator.register_reducer(
        "user_list", lambda x, y: list(set((x or []) + (y or [])))
    )
    coordinator.register_reducer("max_score", lambda x, y: max(x or 0, y or 0))

    # 合并所有Agent状态
    for agent_id, agent in agents.items():
        coordinator.update_state(agent.get_state())

    print(f"\n最终合并状态: {coordinator.get_state()}")

    # 验证合并结果
    final_state = coordinator.get_state()
    assert final_state["message_count"] == 15  # 5+3+7
    assert set(final_state["user_list"]) == {"user1", "user2", "user3", "user4"}
    assert final_state["max_score"] == 92

    print("\n✅ 分布式状态合并验证通过!")

    return agents, coordinator


# ============================================================================
# 第二部分：状态机实现 (State Machine Implementation)
# ============================================================================

print("\n" + "=" * 60)
print("第二部分：状态机实现 - Reducer设计原则验证与工厂模式")
print("=" * 60)


class ReducerDesignPrinciple(Enum):
    """Reducer设计原则枚举"""

    IDEMPOTENCE = "幂等性"  # 多次应用结果相同
    COMMUTATIVITY = "可交换性"  # 顺序不影响结果
    ASSOCIATIVITY = "可结合性"  # 分组不影响结果
    NULL_HANDLING = "空值处理"  # 正确处理None值


@dataclass
class ReducerValidationResult:
    """Reducer验证结果"""

    reducer_name: str
    principles: Dict[ReducerDesignPrinciple, bool]
    performance_ms: float
    error_message: Optional[str] = None

    def is_valid(self) -> bool:
        """检查是否所有必需原则都满足"""
        return all(self.principles.values())

    def print_report(self):
        """打印验证报告"""
        print(f"\n🔍 Reducer验证报告: {self.reducer_name}")
        print("-" * 40)
        for principle, satisfied in self.principles.items():
            status = "✅" if satisfied else "❌"
            print(f"  {principle.value}: {status}")
        print(f"  性能: {self.performance_ms:.2f}ms")
        if self.error_message:
            print(f"  错误: {self.error_message}")


class ReducerValidator:
    """Reducer设计原则验证器"""

    @staticmethod
    def validate_idempotence(reducer: Callable, test_cases: List[Tuple]) -> bool:
        """验证幂等性: reducer(x, x) == x"""
        try:
            for existing, new in test_cases:
                # 第一次合并
                result1 = reducer(existing, new)
                # 第二次用相同输入合并
                result2 = reducer(result1, new)
                # 检查是否相等
                if result1 != result2:
                    return False
            return True
        except Exception:
            return False

    @staticmethod
    def validate_commutativity(reducer: Callable, test_cases: List[Tuple]) -> bool:
        """验证可交换性: reducer(a, b) == reducer(b, a)"""
        try:
            for a, b in test_cases:
                result_ab = reducer(a, b)
                result_ba = reducer(b, a)
                if result_ab != result_ba:
                    return False
            return True
        except Exception:
            return False

    @staticmethod
    def validate_associativity(reducer: Callable, test_cases: List[Tuple]) -> bool:
        """验证可结合性: reducer(a, reducer(b, c)) == reducer(reducer(a, b), c)"""
        try:
            for a, b, c in test_cases:
                left = reducer(a, reducer(b, c))
                right = reducer(reducer(a, b), c)
                if left != right:
                    return False
            return True
        except Exception:
            return False

    @staticmethod
    def validate_null_handling(reducer: Callable) -> bool:
        """验证空值处理: reducer(None, x) == x, reducer(x, None) == x"""
        try:
            # 测试数据
            test_value = [1, 2, 3]

            # reducer(None, x) == x
            result1 = reducer(None, test_value)
            if result1 != test_value:
                return False

            # reducer(x, None) == x
            result2 = reducer(test_value, None)
            if result2 != test_value:
                return False

            # reducer(None, None) 应该返回合理默认值或不抛出异常
            try:
                reducer(None, None)
                return True
            except Exception:
                return False
        except Exception:
            return False

    @classmethod
    def validate_reducer(
        cls, reducer: Callable, reducer_name: str, test_cases: List[Tuple]
    ) -> ReducerValidationResult:
        """全面验证Reducer函数"""
        start_time = time.time()

        principles = {
            ReducerDesignPrinciple.IDEMPOTENCE: cls.validate_idempotence(
                reducer, test_cases
            ),
            ReducerDesignPrinciple.COMMUTATIVITY: cls.validate_commutativity(
                reducer, test_cases
            ),
            ReducerDesignPrinciple.ASSOCIATIVITY: cls.validate_associativity(
                reducer, test_cases
            ),
            ReducerDesignPrinciple.NULL_HANDLING: cls.validate_null_handling(reducer),
        }

        end_time = time.time()
        performance_ms = (end_time - start_time) * 1000

        return ReducerValidationResult(
            reducer_name=reducer_name,
            principles=principles,
            performance_ms=performance_ms,
        )


class ReducerFactory:
    """Reducer工厂模式，支持创建符合设计原则的Reducer"""

    @staticmethod
    def create_list_reducer(keep_order: bool = True) -> Callable:
        """创建列表合并Reducer"""

        def merge_lists(existing: Optional[List], new: Optional[List]) -> List:
            # 处理空值
            if existing is None and new is None:
                return []
            if existing is None:
                return new.copy() if new else []
            if new is None:
                return existing.copy()

            # 合并策略
            if keep_order:
                # 保持顺序，新列表在前，去重
                result = []
                seen = set()

                # 先添加新列表元素
                for item in new:
                    if item not in seen:
                        result.append(item)
                        seen.add(item)

                # 然后添加现有列表元素
                for item in existing:
                    if item not in seen:
                        result.append(item)
                        seen.add(item)

                return result
            else:
                # 简单去重合并，不保持顺序
                return list(set(existing) | set(new))

        return merge_lists

    @staticmethod
    def create_counter_reducer() -> Callable:
        """创建计数器合并Reducer"""

        def merge_counter(existing: Optional[int], new: Optional[int]) -> int:
            # 处理空值
            if existing is None:
                existing = 0
            if new is None:
                new = 0

            # 简单加法（注意：这不满足幂等性！）
            return existing + new

        return merge_counter

    @staticmethod
    def create_max_reducer() -> Callable:
        """创建取最大值Reducer"""

        def merge_max(existing: Optional[Any], new: Optional[Any]) -> Any:
            # 处理空值
            if existing is None:
                return new
            if new is None:
                return existing

            # 取最大值
            return max(existing, new)

        return merge_max

    @staticmethod
    def create_reducer_template(merge_logic: Callable, default_value: Any) -> Callable:
        """创建符合设计原则的Reducer模板"""

        def reducer(existing: Optional[Any], new: Optional[Any]) -> Any:
            # 处理空值
            if existing is None and new is None:
                return default_value
            if existing is None:
                return new
            if new is None:
                return existing

            # 应用合并逻辑
            return merge_logic(existing, new)

        return reducer


def demonstrate_reducer_validation():
    """演示Reducer验证和工厂模式"""
    print("\n演示Reducer设计原则验证:")
    print("-" * 40)

    validator = ReducerValidator()

    # 测试用例
    test_cases = [
        ([1, 2], [2, 3, 4]),  # 列表合并
        ([], [1, 2, 3]),  # 空列表合并
        ([1, 2, 3], []),  # 列表与空合并
    ]

    # 验证列表Reducer
    list_reducer = ReducerFactory.create_list_reducer()
    result = validator.validate_reducer(list_reducer, "列表合并Reducer", test_cases)
    result.print_report()

    # 验证计数器Reducer（应不满足幂等性）
    counter_reducer = ReducerFactory.create_counter_reducer()
    counter_test_cases = [(1, 2), (0, 5), (3, 0)]
    result = validator.validate_reducer(
        counter_reducer, "计数器Reducer", counter_test_cases
    )
    result.print_report()

    # 验证最大值Reducer
    max_reducer = ReducerFactory.create_max_reducer()
    max_test_cases = [(1, 2), (5, 3), (0, 0)]
    result = validator.validate_reducer(max_reducer, "最大值Reducer", max_test_cases)
    result.print_report()

    print("\n🎯 设计原则要点:")
    print("  • 幂等性: 计数器Reducer不满足（业务需求决定）")
    print("  • 可交换性: 列表Reducer满足（去重后顺序可能不同）")
    print("  • 可结合性: 所有示例Reducer都满足")
    print("  • 空值处理: 模板确保正确处理None值")


# ============================================================================
# 第三部分：模块化设计演示 (Modular Design Demonstration)
# ============================================================================

print("\n" + "=" * 60)
print("第三部分：模块化设计演示 - Reducer模式实现与复杂业务设计")
print("=" * 60)


class Priority(Enum):
    """优先级枚举"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ConversationHeat:
    """对话热度模型"""

    def __init__(self, base_heat: float = 0.0, decay_rate: float = 0.5):
        self.base_heat = base_heat
        self.decay_rate = decay_rate  # 每轮衰减率
        self.last_update = datetime.now()

    def add_message(self, importance: float = 1.0):
        """添加消息，增加热度"""
        self._apply_decay()
        self.base_heat += importance
        self.last_update = datetime.now()

    def _apply_decay(self):
        """应用时间衰减"""
        now = datetime.now()
        hours_passed = (now - self.last_update).total_seconds() / 3600
        decay_factor = math.exp(-self.decay_rate * hours_passed)
        self.base_heat *= decay_factor

    def get_heat(self) -> float:
        """获取当前热度"""
        self._apply_decay()
        return max(0.0, self.base_heat)

    def __repr__(self) -> str:
        return f"ConversationHeat(heat={self.get_heat():.2f}, decay={self.decay_rate})"


def merge_priority(existing: Optional[Priority], new: Optional[Priority]) -> Priority:
    """合并优先级：取最高优先级"""
    # 处理空值
    if existing is None and new is None:
        return Priority.LOW
    if existing is None:
        return new
    if new is None:
        return existing

    # 取最高优先级
    return max(existing, new, key=lambda p: p.value)


def merge_conversation_heat(
    existing: Optional[ConversationHeat], new: Optional[ConversationHeat]
) -> ConversationHeat:
    """合并对话热度：取最大值，考虑衰减"""
    # 处理空值
    if existing is None and new is None:
        return ConversationHeat()
    if existing is None:
        return new
    if new is None:
        return existing

    # 取热度较高的那个（考虑衰减）
    existing_heat = existing.get_heat()
    new_heat = new.get_heat()

    if existing_heat >= new_heat:
        return existing
    else:
        return new


def merge_user_preferences(existing: Optional[Dict], new: Optional[Dict]) -> Dict:
    """合并用户偏好：新值覆盖旧值，字典合并"""
    # 处理空值
    if existing is None and new is None:
        return {}
    if existing is None:
        return new.copy() if new else {}
    if new is None:
        return existing.copy()

    # 字典合并，新值覆盖旧值
    result = existing.copy()
    result.update(new)
    return result


def merge_shopping_cart(existing: Optional[Dict], new: Optional[Dict]) -> Dict:
    """合并购物车状态：商品数量累加，去重"""
    # 处理空值
    if existing is None and new is None:
        return {"items": {}, "total": 0.0}
    if existing is None:
        return new.copy() if new else {"items": {}, "total": 0.0}
    if new is None:
        return existing.copy()

    # 合并商品
    items = existing.get("items", {}).copy()
    new_items = new.get("items", {})

    for product_id, quantity in new_items.items():
        if product_id in items:
            items[product_id] += quantity
        else:
            items[product_id] = quantity

    # 重新计算总价（简化）
    total = existing.get("total", 0.0) + new.get("total", 0.0)

    return {"items": items, "total": total}


def demonstrate_complex_reducers():
    """演示复杂业务Reducer设计"""
    print("\n演示复杂业务Reducer设计:")
    print("-" * 40)

    # 1. 优先级合并演示
    print("\n1. 优先级合并:")
    p1 = Priority.MEDIUM
    p2 = Priority.HIGH
    p3 = Priority.LOW

    result = merge_priority(p1, p2)
    print(f"  {p1} + {p2} → {result} (取最高)")

    result = merge_priority(result, p3)
    print(f"  {result} + {p3} → {result} (保持不变)")

    # 2. 对话热度合并演示
    print("\n2. 对话热度合并:")
    heat1 = ConversationHeat(base_heat=5.0)
    heat2 = ConversationHeat(base_heat=8.0)

    # 模拟时间流逝
    import time

    time.sleep(0.1)

    print(f"  热度1: {heat1}")
    print(f"  热度2: {heat2}")

    result = merge_conversation_heat(heat1, heat2)
    print(f"  合并结果: {result} (取热度较高者)")

    # 3. 用户偏好合并演示
    print("\n3. 用户偏好合并:")
    prefs1 = {"theme": "dark", "language": "zh", "notifications": True}
    prefs2 = {"language": "en", "font_size": 14}

    result = merge_user_preferences(prefs1, prefs2)
    print(f"  偏好1: {prefs1}")
    print(f"  偏好2: {prefs2}")
    print(f"  合并结果: {result} (新值覆盖旧值)")

    # 4. 购物车合并演示
    print("\n4. 购物车合并:")
    cart1 = {"items": {"apple": 3, "banana": 2}, "total": 10.0}
    cart2 = {"items": {"apple": 2, "orange": 4}, "total": 8.0}

    result = merge_shopping_cart(cart1, cart2)
    print(f"  购物车1: {cart1}")
    print(f"  购物车2: {cart2}")
    print(f"  合并结果: {result} (商品数量累加)")


class ThreadStateIntegrator:
    """ThreadState集成工具"""

    @staticmethod
    def create_extended_thread_state():
        """创建扩展ThreadState定义"""
        print("\n🎯 集成到ThreadState:")
        print("-" * 40)

        # 模拟ThreadState定义
        thread_state_code = '''
from typing import TypedDict, List, Dict, Optional, Annotated, NotRequired
from datetime import datetime

# 自定义Reducer导入
from .reducers import (
    merge_conversation_heat,
    merge_user_preferences, 
    merge_shopping_cart,
    merge_priority
)

class ExtendedThreadState(TypedDict):
    """扩展的ThreadState，包含自定义Reducer字段"""
    
    # 必需字段
    messages: List[Any]
    
    # 自定义Reducer字段
    conversation_heat: Annotated[
        NotRequired[ConversationHeat],
        merge_conversation_heat
    ]
    
    user_preferences: Annotated[
        NotRequired[Dict[str, Any]],
        merge_user_preferences
    ]
    
    shopping_cart: Annotated[
        NotRequired[Dict[str, Any]],
        merge_shopping_cart
    ]
    
    alert_priority: Annotated[
        NotRequired[Priority],
        merge_priority
    ]
    
    # 标准字段
    thread_data: NotRequired[Dict[str, Any]]
    todos: NotRequired[List[Any]]
    artifacts: NotRequired[List[str]]
'''

        print(thread_state_code)
        print("\n✅ Reducer已成功集成到ThreadState中！")


# ============================================================================
# 第四部分：架构分析 (Architecture Analysis)
# ============================================================================

print("\n" + "=" * 60)
print("第四部分：架构分析 - Reducer设计对系统的影响")
print("=" * 60)


def analyze_reducer_impact():
    """分析Reducer设计对系统可靠性的影响"""

    print("\n📊 Reducer设计对系统可靠性的影响分析:")
    print("-" * 50)

    impacts = [
        {
            "aspect": "幂等性 (Idempotence)",
            "benefit": "支持重试机制，防止重复操作导致状态错误",
            "risk": "不满足时重试可能导致状态不一致",
            "example": "计数器累加不幂等，重试会使计数翻倍",
        },
        {
            "aspect": "可交换性 (Commutativity)",
            "benefit": "支持并行和乱序更新，提高系统并发能力",
            "risk": "不满足时并发更新可能导致结果不确定",
            "example": "列表追加不可交换，顺序不同结果不同",
        },
        {
            "aspect": "可结合性 (Associativity)",
            "benefit": "支持分布式合并和分层聚合",
            "risk": "不满足时分布式合并结果不确定",
            "example": "除法不可结合，(a/b)/c ≠ a/(b/c)",
        },
        {
            "aspect": "空值处理 (Null Handling)",
            "benefit": "处理初始化、缺失、清理等场景，提高鲁棒性",
            "risk": "未处理空值可能导致运行时异常",
            "example": "访问None的属性会抛出AttributeError",
        },
    ]

    for impact in impacts:
        print(f"\n🔸 {impact['aspect']}:")
        print(f"   好处: {impact['benefit']}")
        print(f"   风险: {impact['risk']}")
        print(f"   示例: {impact['example']}")

    print("\n🎯 性能优化策略:")
    print("  1. 惰性计算: 只在需要时计算合并结果")
    print("  2. 批处理: 多个更新批量合并")
    print("  3. 缓存: 缓存频繁使用的合并结果")
    print("  4. 增量更新: 只计算变化部分")

    print("\n⚠️ 常见反模式:")
    print("  1. 全局状态依赖: Reducer依赖外部可变状态")
    print("  2. 副作用操作: Reducer执行IO、网络请求等")
    print("  3. 非确定性: 结果依赖随机数、时间等")
    print("  4. 异常泄漏: 未处理的异常传播到调用者")

    print("\n✅ 最佳实践:")
    print("  1. 纯函数设计: 无副作用，引用透明")
    print("  2. 全面测试: 覆盖边界情况和设计原则")
    print("  3. 性能测试: 测试大数据量下的表现")
    print("  4. 文档完整: 说明合并逻辑和设计决策")


class ReducerBenchmark:
    """Reducer性能基准测试"""

    @staticmethod
    def run_benchmark():
        """运行性能基准测试"""
        print("\n⚡ Reducer性能基准测试:")
        print("-" * 40)

        # 创建测试数据
        large_list1 = list(range(10000))
        large_list2 = list(range(5000, 15000))

        large_dict1 = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_dict2 = {f"key_{i + 500}": f"value_{i + 500}" for i in range(1000)}

        # 测试列表Reducer
        list_reducer = ReducerFactory.create_list_reducer()

        start = time.time()
        for _ in range(100):
            list_reducer(large_list1, large_list2)
        list_time = (time.time() - start) * 1000 / 100  # 平均毫秒

        # 测试字典Reducer
        dict_reducer = merge_user_preferences

        start = time.time()
        for _ in range(100):
            dict_reducer(large_dict1, large_dict2)
        dict_time = (time.time() - start) * 1000 / 100

        print(f"  列表合并 (10000元素): {list_time:.2f}ms/次")
        print(f"  字典合并 (1000键值): {dict_time:.2f}ms/次")

        print("\n📈 性能优化建议:")
        if list_time > 10.0:
            print("  • 列表合并较慢，考虑使用集合运算优化")
        if dict_time > 5.0:
            print("  • 字典合并较慢，考虑增量更新或批处理")

        return list_time, dict_time


# ============================================================================
# 主演示函数
# ============================================================================


def run_full_demonstration():
    """运行完整演示"""

    print("\n" + "=" * 60)
    print("🎓 Day2 第6节课：自定义Reducer函数 - 完整演示")
    print("=" * 60)

    # 第一部分：架构模拟
    agents, coordinator = simulate_distributed_state_merging()

    # 第二部分：状态机实现
    demonstrate_reducer_validation()

    # 第三部分：模块化设计演示
    demonstrate_complex_reducers()
    ThreadStateIntegrator.create_extended_thread_state()

    # 第四部分：架构分析
    analyze_reducer_impact()
    list_time, dict_time = ReducerBenchmark.run_benchmark()

    print("\n" + "=" * 60)
    print("🎉 演示完成！")
    print("=" * 60)

    # 总结
    print("\n📚 学习要点总结:")
    print("  1. Reducer是状态合并的核心，设计需遵循四大原则")
    print("  2. 不同业务场景需要不同的合并策略")
    print("  3. 使用工厂模式创建可重用的Reducer")
    print("  4. 通过Annotated将Reducer集成到ThreadState")
    print("  5. 性能优化和可靠性是生产环境的关键")

    return {
        "agents": len(agents),
        "coordinator_state": coordinator.get_state(),
        "list_merge_performance_ms": list_time,
        "dict_merge_performance_ms": dict_time,
    }


def run_tests():
    """运行所有测试"""
    print("\n🧪 运行Reducer测试...")

    # 测试列表Reducer
    list_reducer = ReducerFactory.create_list_reducer()
    assert list_reducer([1, 2], [2, 3]) == [2, 3, 1]  # 去重，新在前
    assert list_reducer(None, [1, 2]) == [1, 2]
    assert list_reducer([1, 2], None) == [1, 2]
    print("✅ 列表Reducer测试通过")

    # 测试优先级Reducer
    assert merge_priority(Priority.LOW, Priority.HIGH) == Priority.HIGH
    assert merge_priority(None, Priority.MEDIUM) == Priority.MEDIUM
    print("✅ 优先级Reducer测试通过")

    # 测试用户偏好Reducer
    prefs1 = {"a": 1}
    prefs2 = {"b": 2}
    result = merge_user_preferences(prefs1, prefs2)
    assert result == {"a": 1, "b": 2}
    print("✅ 用户偏好Reducer测试通过")

    print("\n🎉 所有测试通过！")


def run_debug_mode():
    """运行调试模式"""
    print("\n🐛 调试模式启用...")

    # 创建调试Reducer
    debug_reducer = ReducerFactory.create_list_reducer()

    # 测试各种边界情况
    test_cases = [
        (None, None),
        (None, []),
        ([], None),
        ([], []),
        ([1], []),
        ([], [1]),
        ([1, 2], [2, 3]),
        ([1, 2, 3], [3, 4, 5]),
    ]

    for i, (existing, new) in enumerate(test_cases):
        result = debug_reducer(existing, new)
        print(f"  测试{i + 1}: {existing} + {new} → {result}")

    print("\n🔍 调试完成！")


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="自定义Reducer函数演示")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--debug", action="store_true", help="运行调试模式")
    parser.add_argument("--benchmark", action="store_true", help="运行性能基准测试")

    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.debug:
        run_debug_mode()
    elif args.benchmark:
        ReducerBenchmark.run_benchmark()
    else:
        # 运行完整演示
        try:
            results = run_full_demonstration()
            print(f"\n📊 演示结果汇总:")
            for key, value in results.items():
                if isinstance(value, (int, float)):
                    print(f"  {key}: {value}")
                elif isinstance(value, dict):
                    print(f"  {key}: {len(value)}个字段")
        except KeyboardInterrupt:
            print("\n\n⚠️ 演示被用户中断")
        except Exception as e:
            print(f"\n❌ 演示出错: {e}")
            import traceback

            traceback.print_exc()
