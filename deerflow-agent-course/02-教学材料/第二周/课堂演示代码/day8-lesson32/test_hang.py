#!/usr/bin/env python3
import asyncio
import logging
import sys
sys.path.insert(0, '.')

from aio_sandbox_demo import AioSandboxProvider, SandboxConfig

logging.basicConfig(level=logging.INFO)

async def test():
    print("Creating provider...")
    config = SandboxConfig(pool_size=3, health_check_interval=1.0)
    provider = AioSandboxProvider(config)
    
    print("Initializing...")
    success = await provider.initialize({})
    print(f"Initialized: {success}")
    
    print("Shutting down...")
    await provider.shutdown()
    print("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(test())