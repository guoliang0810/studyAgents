#!/usr/bin/env python3
# 第106节课：容错设计
import time, random
from typing import Any, Callable, List
from dataclasses import dataclass

@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential: bool = True

def retry_with_config(config: RetryConfig) -> Callable:
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(config.max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < config.max_attempts - 1:
                        delay = config.base_delay * (2 ** attempt if config.exponential else 1)
                        delay = min(delay, config.max_delay)
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

class Fallback:
    def __init__(self, primary: Callable, fallback: Callable):
        self.primary = primary
        self.fallback = fallback
    def execute(self, *args, **kwargs):
        try:
            return self.primary(*args, **kwargs)
        except:
            return self.fallback(*args, **kwargs)

class RateLimiter:
    def __init__(self, max_requests: int, window: int):
        self.max_requests = max_requests
        self.window = window
        self.requests: List[float] = []
    def acquire(self) -> bool:
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.window]
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

def run_demo():
    print("容错设计演示")
    
    @retry_with_config(RetryConfig(max_attempts=3, base_delay=0.1))
    def unstable_func():
        if random.random() > 0.5:
            raise Exception("随机失败")
        return "成功"
    
    for i in range(3):
        try:
            result = unstable_func()
            print(f"尝试{i+1}: {result}")
        except:
            print(f"尝试{i+1}: 失败")
    
    limiter = RateLimiter(2, 1)
    for i in range(5):
        print(f"请求{i+1}: {'通过' if limiter.acquire() else '限制'}")

def run_tests():
    print("测试: 重试机制")
    call_count = 0
    @retry_with_config(RetryConfig(max_attempts=3, base_delay=0.01))
    def fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("fail")
        return "success"
    assert fail_twice() == "success"
    print("✓ 重试测试通过")
    
    print("测试: 降级")
    fb = Fallback(lambda: 1/0, lambda: "fallback")
    assert fb.execute() == "fallback"
    print("✓ 降级测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
