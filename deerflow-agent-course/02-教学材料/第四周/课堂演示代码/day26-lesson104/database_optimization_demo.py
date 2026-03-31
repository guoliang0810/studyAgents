#!/usr/bin/env python3
# 第104节课：数据库选型与优化
import json, time
from typing import Any, List, Dict, Optional
from dataclasses import dataclass

@dataclass
class QueryResult:
    data: List[Dict]
    execution_time: float
    cached: bool = False

class QueryBuilder:
    def __init__(self, table: str):
        self.table = table
        self.where_clauses: List[str] = []
        self.order_by: Optional[str] = None
        self.limit_val: Optional[int] = None
    def where(self, field: str, op: str, value: Any) -> 'QueryBuilder':
        self.where_clauses.append(f"{field} {op} {value!r}")
        return self
    def order(self, field: str, direction: str = "ASC") -> 'QueryBuilder':
        self.order_by = f"{field} {direction}"
        return self
    def limit(self, n: int) -> 'QueryBuilder':
        self.limit_val = n
        return self
    def build(self) -> str:
        query = f"SELECT * FROM {self.table}"
        if self.where_clauses:
            query += " WHERE " + " AND ".join(self.where_clauses)
        if self.order_by:
            query += f" ORDER BY {self.order_by}"
        if self.limit_val:
            query += f" LIMIT {self.limit_val}"
        return query

class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.available = list(range(max_connections))
        self.in_use: set = set()
    def acquire(self) -> int:
        if not self.available:
            raise RuntimeError("No connections available")
        conn = self.available.pop()
        self.in_use.add(conn)
        return conn
    def release(self, conn: int) -> None:
        if conn in self.in_use:
            self.in_use.remove(conn)
            self.available.append(conn)
    def status(self) -> Dict[str, int]:
        return {"available": len(self.available), "in_use": len(self.in_use)}

def run_demo():
    print("数据库优化演示")
    qb = QueryBuilder("users")
    query = qb.where("age", ">", 18).where("status", "=", "active").order("created_at", "DESC").limit(10).build()
    print(f"生成的SQL: {query}")
    
    pool = ConnectionPool(max_connections=5)
    conn = pool.acquire()
    print(f"获取连接: {conn}, 状态: {pool.status()}")
    pool.release(conn)
    print(f"释放连接, 状态: {pool.status()}")

def run_tests():
    print("测试: 查询构建器")
    qb = QueryBuilder("test")
    q = qb.where("id", ">", 10).limit(5).build()
    assert "SELECT * FROM test" in q
    assert "WHERE" in q
    assert "LIMIT 5" in q
    print("✓ 查询构建测试通过")
    
    print("测试: 连接池")
    pool = ConnectionPool(3)
    assert pool.acquire() in [0, 1, 2]
    assert pool.status()["in_use"] == 1
    print("✓ 连接池测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
