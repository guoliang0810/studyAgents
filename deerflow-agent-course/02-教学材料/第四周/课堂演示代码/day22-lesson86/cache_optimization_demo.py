#!/usr/bin/env python3
# 第86节课：缓存策略优化
from collections import OrderedDict
from typing import Any, Optional
import time


class LRUCache:
    """LRU缓存实现"""
    
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


def main():
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    print(cache.get("a"))
    cache.put("d", 4)
    print(cache.get("b"))


if __name__ == "__main__":
    main()
