#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 10 Lesson 40: 超时与错误处理 (Timeout and Error Handling)

本文件演示超时控制和错误处理的完整实现，包括：
1. 超时控制 - 异步任务超时执行和取消处理
2. 重试机制 - 指数退避重试策略
3. 错误分类 - 不同类型错误的处理策略
4. 容错执行 - 集成超时、重试、降级的综合执行器

使用示例:
    python timeout_error_demo.py          # 运行基本演示
    python timeout_error_demo.py --test   # 运行测试套件
    python timeout_error_demo.py --demo   # 运行完整演示
    python timeout_error_demo.py --help   # 显示帮助信息
"""

import asyncio
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict, List, Tuple
import logging

class ErrorType(Enum):
    """错误类型枚举"""
    TIMEOUT = "timeout"            # 超时错误
    NETWORK = "network"            # 网络错误
    RESOURCE = "resource"          # 资源错误
    VALIDATION = "validation"      # 验证错误
    BUSINESS = "business"          # 业务错误
    UNKNOWN = "unknown"            # 未知错误

class RetryStrategy(Enum):
    """重试策略枚举"""
    NONE = "none"                  # 不重试
    FIXED = "fixed"                # 固定间隔重试
    EXPONENTIAL = "exponential"    # 指数退避重试
    RANDOM = "random"              # 随机间隔重试

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3                    # 最大重试次数
    base_delay: float = 1.0                 # 基础延迟（秒）
    max_delay: float = 60.0                 # 最大延迟（秒）
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL  # 重试策略
    jitter: bool = True                     # 是否添加随机抖动
    
    def get_delay(self, attempt: int) -> float:
        """获取重试延迟时间"""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        elif self.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.base_delay, self.max_delay)
        else:
            delay = 0
        
        # 添加随机抖动（0-20%）
        if self.jitter and delay > 0:
            jitter_range = delay * 0.2
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)

@dataclass
class TimeoutError(Exception):
    """超时错误"""
    timeout_value: float
    operation_name: str
    duration: float
    message: str = ""
    
    def __str__(self):
        return (f"操作 '{self.operation_name}' 超时 "
                f"(超时时间: {self.timeout_value}秒, "
                f"执行时间: {self.duration}秒)")

class CircuitBreakerState(Enum):
    """断路器状态"""
    CLOSED = "closed"      # 关闭状态（正常）
    OPEN = "open"          # 打开状态（阻止请求）
    HALF_OPEN = "half_open"  # 半开状态（测试恢复）

@dataclass
class CircuitBreaker:
    """断路器"""
    failure_threshold: int = 5           # 失败阈值
    recovery_timeout: float = 30.0       # 恢复超时（秒）
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    
    def record_success(self):
        """记录成功"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # 检查是否超过恢复超时
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        
        # HALF_OPEN状态：允许部分请求测试恢复
        return True
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
            "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time > 0 else None
        }

class FaultTolerantExecutor:
    """容错执行器"""
    
    def __init__(self, name: str = "executor"):
        self.name = name
        self.circuit_breaker = CircuitBreaker()
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "timeout_errors": 0,
            "retries": 0,
            "circuit_breaker_blocks": 0
        }
    
    async def execute_with_timeout(self, coro: Any, timeout: float, 
                                 operation_name: str = "operation") -> Any:
        """带超时的执行"""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            duration = time.time() - start_time
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            raise TimeoutError(
                timeout_value=timeout,
                operation_name=operation_name,
                duration=duration,
                message=f"操作超时 ({timeout}秒)"
            )
    
    async def retry_with_backoff(self, coro_func: Callable, 
                               retry_config: RetryConfig,
                               operation_name: str = "operation",
                               should_retry: Optional[Callable[[Exception], bool]] = None) -> Any:
        """带重试的执行"""
        last_exception = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                result = await coro_func()
                if attempt > 0:
                    self.metrics["retries"] += attempt
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                if should_retry and not should_retry(e):
                    break
                
                # 如果是最后一次尝试，不再等待
                if attempt == retry_config.max_retries:
                    break
                
                # 计算延迟时间
                delay = retry_config.get_delay(attempt)
                logging.info(f"操作 '{operation_name}' 失败，{delay:.2f}秒后重试 (尝试 {attempt + 1}/{retry_config.max_retries + 1}): {e}")
                
                await asyncio.sleep(delay)
        
        # 所有重试都失败
        self.metrics["retries"] += retry_config.max_retries
        raise last_exception
    
    async def execute_with_fallback(self, primary_coro: Any, 
                                  fallback_coro: Any,
                                  operation_name: str = "operation") -> Any:
        """带降级的执行"""
        try:
            return await primary_coro
        except Exception as e:
            logging.warning(f"主操作 '{operation_name}' 失败，执行降级操作: {e}")
            return await fallback_coro
    
    async def execute(self, coro_func: Callable, 
                     timeout: Optional[float] = None,
                     retry_config: Optional[RetryConfig] = None,
                     fallback_func: Optional[Callable] = None,
                     operation_name: str = "operation") -> Any:
        """容错执行"""
        self.metrics["total_executions"] += 1
        
        # 检查断路器
        if not self.circuit_breaker.can_execute():
            self.metrics["circuit_breaker_blocks"] += 1
            raise Exception(f"断路器打开，操作 '{operation_name}' 被阻止")
        
        async def execute_core():
            # 执行核心逻辑
            if timeout:
                return await self.execute_with_timeout(
                    coro_func(), timeout, operation_name
                )
            else:
                return await coro_func()
        
        try:
            # 使用重试机制
            if retry_config and retry_config.max_retries > 0:
                result = await self.retry_with_backoff(
                    execute_core, retry_config, operation_name
                )
            else:
                result = await execute_core()
            
            # 记录成功
            self.circuit_breaker.record_success()
            self.metrics["successful_executions"] += 1
            return result
            
        except TimeoutError:
            self.circuit_breaker.record_failure()
            self.metrics["timeout_errors"] += 1
            self.metrics["failed_executions"] += 1
            raise
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.metrics["failed_executions"] += 1
            
            # 执行降级
            if fallback_func:
                try:
                    return await fallback_func()
                except Exception as fallback_error:
                    logging.error(f"降级操作也失败: {fallback_error}")
                    raise e  # 抛出原始异常
            
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        metrics = self.metrics.copy()
        metrics["success_rate"] = (
            metrics["successful_executions"] / metrics["total_executions"] * 100
            if metrics["total_executions"] > 0 else 0
        )
        metrics["circuit_breaker"] = self.circuit_breaker.get_state_info()
        return metrics

class TimeoutErrorTestSuite:
    """超时错误测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_timeout_control", self.test_timeout_control),
            ("test_retry_mechanism", self.test_retry_mechanism),
            ("test_circuit_breaker", self.test_circuit_breaker),
            ("test_fallback_execution", self.test_fallback_execution),
            ("test_fault_tolerant_executor", self.test_fault_tolerant_executor),
        ]
    
    async def slow_operation(self, delay: float, should_fail: bool = False):
        """模拟慢操作"""
        await asyncio.sleep(delay)
        if should_fail:
            raise Exception("操作失败")
        return f"操作完成，延迟: {delay}秒"
    
    async def failing_operation(self, fail_count: int = 2):
        """模拟失败操作"""
        if not hasattr(self, '_fail_counter'):
            self._fail_counter = 0
        
        self._fail_counter += 1
        if self._fail_counter <= fail_count:
            raise Exception(f"模拟失败 (尝试 {self._fail_counter})")
        
        return "成功"
    
    def test_timeout_control(self) -> Tuple[bool, str]:
        """测试超时控制"""
        executor = FaultTolerantExecutor()
        
        async def run_test():
            # 测试正常操作（不超时）
            try:
                result = await executor.execute_with_timeout(
                    self.slow_operation(0.1),
                    timeout=1.0,
                    operation_name="快速操作"
                )
                if "操作完成" not in result:
                    return False, "正常操作执行失败"
            except Exception as e:
                return False, f"正常操作异常: {e}"
            
            # 测试超时操作
            try:
                await executor.execute_with_timeout(
                    self.slow_operation(2.0),
                    timeout=0.5,
                    operation_name="慢操作"
                )
                return False, "超时操作应该失败但成功了"
            except TimeoutError:
                pass  # 预期异常
            except Exception as e:
                return False, f"超时操作异常类型错误: {e}"
            
            return True, "超时控制测试通过"
        
        return asyncio.run(run_test())
    
    def test_retry_mechanism(self) -> Tuple[bool, str]:
        """测试重试机制"""
        executor = FaultTolerantExecutor()
        
        async def run_test():
            # 重置失败计数器
            self._fail_counter = 0
            
            # 测试重试成功
            retry_config = RetryConfig(
                max_retries=3,
                base_delay=0.1,
                strategy=RetryStrategy.FIXED,
                jitter=False
            )
            
            try:
                result = await executor.retry_with_backoff(
                    lambda: self.failing_operation(fail_count=2),
                    retry_config,
                    operation_name="重试操作"
                )
                if result != "成功":
                    return False, f"重试操作结果错误: {result}"
            except Exception as e:
                return False, f"重试操作异常: {e}"
            
            # 验证重试次数
            if executor.metrics["retries"] < 2:
                return False, f"重试次数不足: {executor.metrics['retries']}"
            
            return True, f"重试机制测试通过，重试了{executor.metrics['retries']}次"
        
        return asyncio.run(run_test())
    
    def test_circuit_breaker(self) -> Tuple[bool, str]:
        """测试断路器"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        # 初始状态应该是关闭
        if cb.state != CircuitBreakerState.CLOSED:
            return False, f"初始状态错误: {cb.state}"
        
        if not cb.can_execute():
            return False, "关闭状态下应该允许执行"
        
        # 记录失败
        cb.record_failure()
        cb.record_failure()
        
        # 应该进入打开状态
        if cb.state != CircuitBreakerState.OPEN:
            return False, f"失败阈值后状态错误: {cb.state}"
        
        if cb.can_execute():
            return False, "打开状态下应该阻止执行"
        
        # 等待恢复超时
        time.sleep(0.15)
        
        # 应该进入半开状态
        if not cb.can_execute():
            return False, "恢复超时后应该允许执行"
        
        if cb.state != CircuitBreakerState.HALF_OPEN:
            return False, f"恢复超时后状态错误: {cb.state}"
        
        # 记录成功，应该回到关闭状态
        cb.record_success()
        if cb.state != CircuitBreakerState.CLOSED:
            return False, f"成功后状态错误: {cb.state}"
        
        return True, "断路器测试通过"
    
    def test_fallback_execution(self) -> Tuple[bool, str]:
        """测试降级执行"""
        executor = FaultTolerantExecutor()
        
        async def run_test():
            # 测试主操作成功
            try:
                result = await executor.execute_with_fallback(
                    self.slow_operation(0.1, should_fail=False),
                    self.slow_operation(0.2, should_fail=False),
                    operation_name="主操作"
                )
                if "操作完成" not in result:
                    return False, "主操作执行失败"
            except Exception as e:
                return False, f"主操作异常: {e}"
            
            # 测试主操作失败，降级成功
            try:
                result = await executor.execute_with_fallback(
                    self.slow_operation(0.1, should_fail=True),
                    self.slow_operation(0.2, should_fail=False),
                    operation_name="主操作失败"
                )
                if "操作完成" not in result:
                    return False, "降级操作执行失败"
            except Exception as e:
                return False, f"降级操作异常: {e}"
            
            return True, "降级执行测试通过"
        
        return asyncio.run(run_test())
    
    def test_fault_tolerant_executor(self) -> Tuple[bool, str]:
        """测试容错执行器"""
        executor = FaultTolerantExecutor()
        
        async def run_test():
            # 测试成功执行
            try:
                result = await executor.execute(
                    lambda: self.slow_operation(0.1, should_fail=False),
                    timeout=1.0,
                    operation_name="成功操作"
                )
                if "操作完成" not in result:
                    return False, "成功操作执行失败"
            except Exception as e:
                return False, f"成功操作异常: {e}"
            
            # 测试带重试的成功执行
            retry_config = RetryConfig(
                max_retries=2,
                base_delay=0.05,
                strategy=RetryStrategy.FIXED,
                jitter=False
            )
            
            self._fail_counter = 0
            try:
                result = await executor.execute(
                    lambda: self.failing_operation(fail_count=1),
                    retry_config=retry_config,
                    operation_name="重试成功操作"
                )
                if result != "成功":
                    return False, f"重试成功操作结果错误: {result}"
            except Exception as e:
                return False, f"重试成功操作异常: {e}"
            
            # 检查指标
            metrics = executor.get_metrics()
            if metrics["total_executions"] != 2:
                return False, f"总执行次数错误: {metrics['total_executions']}"
            
            if metrics["successful_executions"] != 2:
                return False, f"成功执行次数错误: {metrics['successful_executions']}"
            
            return True, f"容错执行器测试通过，成功率: {metrics['success_rate']:.1f}%"
        
        return asyncio.run(run_test())
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行超时错误处理测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {len(self.tests)}")
        print(f"   通过测试: {passed}")
        print(f"   失败测试: {failed}")
        print(f"   成功率: {passed / len(self.tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": len(self.tests),
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": passed / len(self.tests) * 100 if len(self.tests) > 0 else 0
            },
            "detailed_results": results
        }

async def main_demo():
    """主演示函数"""
    print("🎓 Day 10 Lesson 40: 超时与错误处理演示")
    print("=" * 60)
    
    # 创建容错执行器
    executor = FaultTolerantExecutor("demo_executor")
    
    print("\n1. 超时控制演示:")
    
    async def fast_operation():
        await asyncio.sleep(0.1)
        return "快速操作完成"
    
    async def slow_operation():
        await asyncio.sleep(2.0)
        return "慢操作完成"
    
    # 测试快速操作（不超时）
    try:
        result = await executor.execute_with_timeout(
            fast_operation(),
            timeout=1.0,
            operation_name="快速操作"
        )
        print(f"   ✅ 快速操作: {result}")
    except Exception as e:
        print(f"   ❌ 快速操作失败: {e}")
    
    # 测试慢操作（超时）
    try:
        result = await executor.execute_with_timeout(
            slow_operation(),
            timeout=0.5,
            operation_name="慢操作"
        )
        print(f"   ❌ 慢操作未超时: {result}")
    except TimeoutError as e:
        print(f"   ✅ 慢操作正确超时: {e}")
    
    print("\n2. 重试机制演示:")
    
    call_count = 0
    
    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"模拟临时故障 (尝试 {call_count})")
        return "成功"
    
    # 重置计数器
    call_count = 0
    
    retry_config = RetryConfig(
        max_retries=5,
        base_delay=0.1,
        strategy=RetryStrategy.EXPONENTIAL,
        jitter=False
    )
    
    try:
        result = await executor.retry_with_backoff(
            flaky_operation,
            retry_config,
            operation_name="易失败操作"
        )
        print(f"   ✅ 重试成功: {result} (总尝试次数: {call_count})")
    except Exception as e:
        print(f"   ❌ 重试失败: {e}")
    
    print("\n3. 断路器演示:")
    
    # 创建断路器
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    print(f"   初始状态: {cb.state.value}")
    
    # 模拟失败
    for i in range(3):
        cb.record_failure()
        print(f"   记录失败 {i+1}: 状态={cb.state.value}, 失败计数={cb.failure_count}")
    
    print(f"   断路器打开，阻止执行: {not cb.can_execute()}")
    
    # 等待恢复
    print(f"   等待恢复超时...")
    await asyncio.sleep(1.1)
    
    print(f"   半开状态，允许测试: {cb.can_execute()}")
    print(f"   状态: {cb.state.value}")
    
    # 模拟成功恢复
    cb.record_success()
    print(f"   恢复成功，断路器关闭: {cb.state.value}")
    
    print("\n4. 降级执行演示:")
    
    async def primary_service():
        raise Exception("主服务故障")
    
    async def fallback_service():
        return "降级服务响应"
    
    try:
        result = await executor.execute_with_fallback(
            primary_service(),
            fallback_service(),
            operation_name="主服务"
        )
        print(f"   ✅ 降级成功: {result}")
    except Exception as e:
        print(f"   ❌ 降级失败: {e}")
    
    print("\n5. 综合容错执行演示:")
    
    # 模拟一个复杂的操作流程
    operation_count = 0
    
    async def complex_operation():
        nonlocal operation_count
        operation_count += 1
        
        # 模拟不同错误
        if operation_count == 1:
            raise Exception("网络错误")
        elif operation_count == 2:
            await asyncio.sleep(2.0)  # 超时
        else:
            return "成功执行"
    
    operation_count = 0
    
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=0.05,
        strategy=RetryStrategy.FIXED,
        jitter=False
    )
    
    try:
        result = await executor.execute(
            complex_operation,
            timeout=1.0,
            retry_config=retry_config,
            operation_name="复杂操作"
        )
        print(f"   ✅ 复杂操作最终成功: {result}")
    except Exception as e:
        print(f"   ❌ 复杂操作最终失败: {e}")
    
    # 显示统计信息
    print("\n6. 执行统计:")
    metrics = executor.get_metrics()
    print(f"   总执行次数: {metrics['total_executions']}")
    print(f"   成功执行: {metrics['successful_executions']}")
    print(f"   失败执行: {metrics['failed_executions']}")
    print(f"   超时错误: {metrics['timeout_errors']}")
    print(f"   重试次数: {metrics['retries']}")
    print(f"   成功率: {metrics['success_rate']:.1f}%")
    print(f"   断路器状态: {metrics['circuit_breaker']['state']}")

def run_tests():
    """运行测试套件"""
    test_suite = TimeoutErrorTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 超时错误处理测试套件验证通过")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False

if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(main_demo())
    else:
        asyncio.run(main_demo())