#!/usr/bin/env python3
# 第103节课：缓存策略
import time, hashlib
from typing import Any, Optional

class CacheEntry:
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.expires_at = time.time() + ttl
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class MemoryCache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: dict = {}
    def get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if entry and not entry.is_expired():
            return entry.value
        if key in self.cache: del self.cache[key]
        return None
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache.items(), key=lambda x: x[1].expires_at)
            del self.cache[oldest[0]]
        self.cache[key] = CacheEntry(value, ttl)
    def delete(self, key: str) -> None:
        if key in self.cache: del self.cache[key]
    def clear(self) -> None:
        self.cache.clear()

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
    def get(self, key: str) -> Optional[Any]:
        return None
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        pass
    def delete(self, key: str) -> None:
        pass
    def exists(self, key: str) -> bool:
        return False

def run_demo():
    print("缓存策略演示")
    cache = MemoryCache(max_size=100)
    cache.set("user:1", {"name": "Alice"}, ttl=60)
    cache.set("user:2", {"name": "Bob"}, ttl=60)
    print(f"获取user:1: {cache.get('user:1')}")
    print(f"获取user:999: {cache.get('user:999')}")
    cache.delete("user:1")
    print(f"删除后user:1: {cache.get('user:1')}")

def run_tests():
    print("测试: 内存缓存")
    cache = MemoryCache()
    cache.set("key", "value", ttl=1)
    assert cache.get("key") == "value"
    time.sleep(1.1)
    assert cache.get("key") is None
    print("✓ 缓存过期测试通过")
    
    print("测试: 缓存删除")
    cache.set("test", "data")
    cache.delete("test")
    assert cache.get("test") is None
    print("✓ 缓存删除测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
