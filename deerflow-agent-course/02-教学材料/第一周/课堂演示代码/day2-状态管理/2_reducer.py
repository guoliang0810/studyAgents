"""
Day 2 - 自定义Reducer函数
演示如何使用Reducer自定义状态合并逻辑
"""

from typing import TypedDict, Annotated, List
from collections import Counter
from langgraph.graph import StateGraph, START, END


class AggregatorState(TypedDict):
    """带聚合功能的状态"""
    # 使用Counter作为Reducer，统计各类型出现次数
    item_counts: Annotated[dict, lambda old, new: Counter(old) + Counter(new)]
    
    # 列表会累积追加
    items: Annotated[List[str], "append"]
    
    # 最后一个值会被新值覆盖
    last_item: str


def add_item(state: AggregatorState, item: str, category: str) -> AggregatorState:
    """添加项目"""
    return {
        "item_counts": {category: 1},
        "items": [item],
        "last_item": item
    }


def build_aggregator_graph():
    """构建聚合图"""
    graph = StateGraph(AggregatorState)
    
    def start_node(state: AggregatorState) -> AggregatorState:
        print(f"开始聚合，当前状态:")
        print(f"  计数: {dict(state['item_counts'])}")
        print(f"  项目: {state['items']}")
        return state
    
    graph.add_node("start", start_node)
    graph.add_edge(START, "start")
    graph.add_edge("start", END)
    
    return graph.compile()


def demonstrate_reducers():
    """演示Reducer机制"""
    print("=" * 50)
    print("自定义Reducer示例")
    print("=" * 50)
    
    # 初始状态
    initial_state = {
        "item_counts": {"fruit": 2, "vegetable": 1},
        "items": ["apple", "carrot"],
        "last_item": "carrot"
    }
    
    print(f"\n初始状态:")
    print(f"  计数: {dict(initial_state['item_counts'])}")
    print(f"  项目: {initial_state['items']}")
    
    # 模拟多次更新
    updates = [
        {"item_counts": {"fruit": 1}, "items": ["banana"], "last_item": "banana"},
        {"item_counts": {"vegetable": 2}, "items": ["broccoli"], "last_item": "broccoli"},
        {"item_counts": {"fruit": 1}, "items": ["orange"], "last_item": "orange"},
    ]
    
    for update in updates:
        # 使用Reducer合并
        for key in initial_state:
            if key in update:
                if key == "item_counts":
                    # Counter合并
                    counter = Counter(initial_state[key])
                    counter.update(update[key])
                    initial_state[key] = dict(counter)
                elif key == "items":
                    # 列表追加
                    initial_state[key].append(update[key][0])
                else:
                    # 覆盖
                    initial_state[key] = update[key]
        
        print(f"\n更新后 (last_item={update['last_item']}):")
        print(f"  计数: {initial_state['item_counts']}")
        print(f"  项目数: {len(initial_state['items'])}")


if __name__ == "__main__":
    demonstrate_reducers()
