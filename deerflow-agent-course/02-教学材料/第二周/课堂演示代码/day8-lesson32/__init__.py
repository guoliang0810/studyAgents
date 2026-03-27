"""
Day 8 Lesson 32: AioSandboxProvider

本包提供AioSandboxProvider的完整实现和演示代码，包括：
1. AioSandboxProvider类 - 实现BaseProvider协议和Sandbox接口的异步连接池提供者
2. 异步连接池管理 - 信号量控制、连接复用、自动伸缩等高性能特性
3. Provider模式集成 - 与ProviderRegistry、ProviderFactory的完整集成
4. 性能优化技巧 - 预热池、懒加载、健康检查等高级功能
5. 测试套件 - 完整的单元测试和集成测试，包括并发性能测试

使用示例:
    from aio_sandbox_demo import AioSandboxProvider, SandboxConfig
    import asyncio
    
    async def demo():
        # 创建配置
        config = SandboxConfig(
            provider="aio",
            pool_size=5,           # 连接池大小
            timeout_seconds=30.0,
            env={"TEST": "value"}
        )
        
        # 创建Provider实例
        provider = AioSandboxProvider()
        sandbox = provider.create(config)
        
        # 初始化
        await sandbox.initialize({})
        
        # 并发执行命令
        async def execute_task(i):
            result = await sandbox.execute("echo", [f"Task {i}"])
            return result
        
        tasks = [execute_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"任务{i}: {result.stdout.strip()}")

课程重点:
- 异步连接池的设计与实现
- 信号量在并发控制中的应用
- 高性能沙箱的性能优化技巧
- 异步执行与同步执行的性能对比
- 连接池管理的自动伸缩和健康检查
"""

__version__ = "1.0.0"
__author__ = "DeerFlow Team"
__description__ = "AioSandboxProvider实现 - Day 8 Lesson 32"