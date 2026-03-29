#!/usr/bin/env python3
# 第87节课：连接池管理
import asyncio
from typing import Optional


class Connection:
    def __init__(self, id: int):
        self.id = id
        self.in_use = False
    
    async def execute(self, query: str):
        await asyncio.sleep(0.1)
        return f"Result from connection {self.id}"


class ConnectionPool:
    def __init__(self, size: int = 5):
        self.size = size
        self.connections = [Connection(i) for i in range(size)]
        self.queue = asyncio.Queue()
    
    async def acquire(self) -> Connection:
        for conn in self.connections:
            if not conn.in_use:
                conn.in_use = True
                return conn
        return await self.queue.get()
    
    def release(self, conn: Connection):
        conn.in_use = False
        self.queue.put_nowait(conn)


async def main():
    pool = ConnectionPool(3)
    conn = await pool.acquire()
    result = await conn.execute("SELECT 1")
    pool.release(conn)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
