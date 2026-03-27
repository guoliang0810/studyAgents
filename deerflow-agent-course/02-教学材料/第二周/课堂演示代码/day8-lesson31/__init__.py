"""
Day 8 Lesson 31: LocalSandboxProvider

本包提供LocalSandboxProvider的完整实现和演示代码，包括：
1. LocalSandboxProvider类 - 实现BaseProvider协议和Sandbox接口的具体提供者
2. 本地沙箱核心功能 - 工作目录隔离、环境变量合并、异步子进程执行
3. Provider模式集成 - 与ProviderRegistry、ProviderFactory的完整集成
4. 安全限制机制 - 本地沙箱的安全限制设计和实现
5. 测试套件 - 完整的单元测试和集成测试

使用示例:
    from local_sandbox_demo import LocalSandboxProvider, LocalSandboxConfig
    import asyncio
    
    async def demo():
        # 创建配置
        config = LocalSandboxConfig(
            workdir="/tmp/sandbox_test",
            timeout_seconds=30.0,
            env={"TEST": "value"}
        )
        
        # 创建Provider实例
        provider = LocalSandboxProvider(config)
        
        # 初始化
        await provider.initialize({})
        
        # 执行命令
        result = await provider.execute("ls", ["-la"])
        print(f"执行结果: {result}")

课程重点:
- Provider模式的具体实现
- 本地沙箱的安全隔离机制
- 异步子进程管理和超时控制
- 配置驱动的Provider创建
"""

__version__ = "1.0.0"
__author__ = "DeerFlow Team"
__description__ = "LocalSandboxProvider实现 - Day 8 Lesson 31"