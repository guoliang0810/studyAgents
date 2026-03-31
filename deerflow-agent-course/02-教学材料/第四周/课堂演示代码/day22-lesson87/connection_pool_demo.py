#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接池管理 - 演示代码

本模块展示AI Agent系统中的连接池管理。
包含：连接池核心概念、线程安全实现、监控指标。

本代码是DeerFlow架构师训练营第87节课的演示代码，
帮助学员掌握连接池管理的核心技能。

作者: DeerFlow架构师训练营
"""

import asyncio
import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
import random


# ============================================================================
# 第一部分：连接池核心概念
# ============================================================================

class ConnectionState(Enum):
    """连接状态"""
    IDLE = "idle"           # 空闲
    ACQUIRED = "acquired"   # 已借出
    TESTING = "testing"     # 测试中
    CLOSED = "closed"      # 已关闭


@dataclass
class PoolConfig:
    """连接池配置"""
    min_size: int = 2           # 最小连接数
    max_size: int = 10          # 最大连接数
    max_idle_time: float = 300  # 最大空闲时间（秒）
    connection_timeout: float = 30  # 连接超时（秒）
    acquire_timeout: float = 30   # 获取连接超时（秒）
    validation_interval: float = 60  # 验证间隔（秒）


@dataclass
class PoolStats:
    """连接池统计"""
    total_connections: int = 0   # 总连接数
    idle_connections: int = 0    # 空闲连接数
    acquired_connections: int = 0 # 已借出连接数
    wait_queue_size: int = 0    # 等待队列大小
    connection_creates: int = 0  # 创建的连接数
    connection_closes: int = 0    # 关闭的连接数
    acquire_count: int = 0        # 获取连接次数
    release_count: int = 0       # 释放连接次数
    timeout_count: int = 0        # 超时次数
    
    @property
    def utilization(self) -> float:
        """连接利用率"""
        if self.total_connections == 0:
            return 0.0
        return self.acquired_connections / self.total_connections


# ============================================================================
# 第二部分：连接实现
# ============================================================================

class DatabaseConnection:
    """数据库连接模拟
    
    模拟真实的数据库连接操作
    """
    
    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.query_count = 0
        self.state = ConnectionState.IDLE
    
    def is_alive(self) -> bool:
        """检查连接是否存活"""
        # 模拟连接健康检查
        return self.state != ConnectionState.CLOSED
    
    def is_idle_timeout(self, max_idle_time: float) -> bool:
        """检查是否空闲超时"""
        return (time.time() - self.last_used) > max_idle_time
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """执行查询
        
        Args:
            query: SQL查询
            
        Returns:
            查询结果
        """
        self.last_used = time.time()
        self.query_count += 1
        
        # 模拟查询执行
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        return {
            "conn_id": self.conn_id,
            "query": query,
            "row_count": random.randint(1, 100),
            "execution_time_ms": random.uniform(10, 100)
        }
    
    def close(self):
        """关闭连接"""
        self.state = ConnectionState.CLOSED
    
    def __repr__(self) -> str:
        return f"DatabaseConnection(id={self.conn_id}, state={self.state.value})"


# ============================================================================
# 第三部分：连接池实现
# ============================================================================

class ConnectionPool:
    """异步连接池
    
    高性能的异步连接池实现，支持：
    - 最小/最大连接数管理
    - 连接空闲超时
    - 连接健康检查
    - 线程安全操作
    
    使用示例:
        pool = ConnectionPool(config)
        
        async with pool.acquire() as conn:
            result = await conn.execute("SELECT 1")
    """
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self._pool: Queue = Queue(maxsize=config.max_size)
        self._all_connections: List[DatabaseConnection] = []
        self._lock = threading.Lock()
        self._stats = PoolStats()
        self._closed = False
        
        # 初始化最小连接数
        self._init_min_connections()
    
    def _init_min_connections(self):
        """初始化最小连接数"""
        for i in range(self.config.min_size):
            conn = DatabaseConnection(i)
            self._all_connections.append(conn)
            self._pool.put(conn)
            self._stats.total_connections += 1
            self._stats.connection_creates += 1
    
    async def acquire(self, timeout: Optional[float] = None) -> DatabaseConnection:
        """获取连接
        
        Args:
            timeout: 超时时间（秒），None使用配置默认值
            
        Returns:
            数据库连接
            
        Raises:
            TimeoutError: 获取连接超时
        """
        timeout = timeout or self.config.acquire_timeout
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                # 尝试从池中获取连接
                conn = self._pool.get_nowait()
                
                # 检查连接是否有效
                if not conn.is_alive():
                    await self._create_connection()
                    continue
                
                # 检查空闲超时
                if conn.is_idle_timeout(self.config.max_idle_time):
                    await self._close_connection(conn)
                    await self._create_connection()
                    continue
                
                # 标记为已借出
                conn.state = ConnectionState.ACQUIRED
                self._stats.acquired_connections += 1
                self._stats.acquire_count += 1
                
                return conn
                
            except Empty:
                # 池为空，尝试创建新连接
                if self._stats.total_connections < self.config.max_size:
                    await self._create_connection()
                else:
                    # 等待释放
                    await asyncio.sleep(0.01)
        
        # 超时
        self._stats.timeout_count += 1
        raise TimeoutError(f"获取连接超时（{timeout}秒）")
    
    def release(self, conn: DatabaseConnection):
        """释放连接
        
        Args:
            conn: 数据库连接
        """
        if self._closed:
            conn.close()
            return
        
        conn.state = ConnectionState.IDLE
        self._pool.put_nowait(conn)
        self._stats.acquired_connections -= 1
        self._stats.release_count += 1
    
    async def _create_connection(self) -> DatabaseConnection:
        """创建新连接"""
        with self._lock:
            if self._stats.total_connections >= self.config.max_size:
                return None
            
            conn_id = len(self._all_connections)
            conn = DatabaseConnection(conn_id)
            self._all_connections.append(conn)
            self._stats.total_connections += 1
            self._stats.connection_creates += 1
            self._stats.idle_connections += 1
            
            return conn
    
    async def _close_connection(self, conn: DatabaseConnection):
        """关闭连接"""
        conn.close()
        with self._lock:
            self._stats.total_connections -= 1
            self._stats.connection_closes += 1
    
    async def close_all(self):
        """关闭所有连接"""
        self._closed = True
        with self._lock:
            for conn in self._all_connections:
                conn.close()
            self._all_connections.clear()
            self._stats = PoolStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            "total_connections": self._stats.total_connections,
            "idle_connections": self._stats.total_connections - self._stats.acquired_connections,
            "acquired_connections": self._stats.acquired_connections,
            "utilization": f"{self._stats.utilization*100:.1f}%",
            "connection_creates": self._stats.connection_creates,
            "connection_closes": self._stats.connection_closes,
            "acquire_count": self._stats.acquire_count,
            "release_count": self._stats.release_count,
            "timeout_count": self._stats.timeout_count
        }


class PooledConnection:
    """连接池连接上下文管理器
    
    使用上下文管理器自动管理连接获取和释放
    
    使用示例:
        async with pool.acquire() as conn:
            result = await conn.execute("SELECT 1")
    """
    
    def __init__(self, pool: ConnectionPool):
        self._pool = pool
        self._conn: Optional[DatabaseConnection] = None
    
    async def __aenter__(self) -> DatabaseConnection:
        self._conn = await self._pool.acquire()
        return self._conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._pool.release(self._conn)
        return False


# ============================================================================
# 第四部分：连接池使用示例
# ============================================================================

async def example_basic_usage():
    """基础使用示例"""
    print("\n### 基础使用示例")
    
    config = PoolConfig(min_size=2, max_size=5)
    pool = ConnectionPool(config)
    
    try:
        # 使用上下文管理器
        async with pool.acquire() as conn:
            result = await conn.execute("SELECT * FROM users")
            print(f"执行结果: {result}")
        
        # 获取统计
        print(f"连接池统计: {pool.get_stats()}")
        
    finally:
        await pool.close_all()


async def example_concurrent_usage():
    """并发使用示例"""
    print("\n### 并发使用示例")
    
    config = PoolConfig(min_size=2, max_size=5)
    pool = ConnectionPool(config)
    
    async def worker(worker_id: int):
        try:
            async with pool.acquire() as conn:
                result = await conn.execute(f"SELECT {worker_id}")
                print(f"Worker {worker_id}: {result['conn_id']}")
                return result
        except TimeoutError:
            print(f"Worker {worker_id}: 获取连接超时")
    
    # 并发执行
    tasks = [worker(i) for i in range(10)]
    await asyncio.gather(*tasks)
    
    print(f"最终统计: {pool.get_stats()}")
    await pool.close_all()


# ============================================================================
# 演示代码
# ============================================================================

async def run_connection_pool_demo():
    """运行连接池演示"""
    print("=" * 70)
    print("DeerFlow连接池管理演示")
    print("=" * 70)
    
    # 1. 基础使用
    await example_basic_usage()
    
    # 2. 并发使用
    await example_concurrent_usage()
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_connection_pool_demo())
