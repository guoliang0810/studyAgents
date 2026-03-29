# 🎓 Day 18 第72节课：MCP工具发现 - 课堂演示代码

## 📚 课程概述

本课程深入讲解MCP工具发现机制的设计与实现。通过完整的代码演示，学生将掌握动态工具发现、注册表设计和智能搜索算法，构建可扩展的MCP工具发现系统。

## 🎯 学习目标

### 知识目标
1. 理解MCP工具发现机制的设计原理和实现模式
2. 掌握动态工具发现、注册和搜索的架构设计
3. 了解工具元数据管理和分类组织的最佳实践

### 技能目标
1. 实现MCP工具发现服务，支持本地和网络服务器发现
2. 创建工具注册表，支持工具分类、搜索和元数据管理
3. 设计智能工具匹配和推荐算法

## 📁 文件结构

```
day18-lesson72/
├── mcp_tool_discovery_demo.py     # 主演示代码文件（1654行）
├── README.md                     # 本文件
└── requirements.txt              # Python依赖包列表
```

## 🛠️ 技术栈

- **Python 3.12+**: 异步编程支持
- **HTTPX**: 异步HTTP客户端库，用于MCP服务器通信
- **异步IO**: asyncio并发处理，提高发现效率
- **MCP协议**: Model Context Protocol工具集成
- **搜索算法**: 基于名称、描述、标签、类别的智能匹配

## 🔧 核心组件

### 1. MCPToolInfo - MCP工具信息类
```python
class MCPToolInfo:
    """MCP工具信息封装"""
    def __init__(self, name: str, description: str, server_url: str, server_type: str, 
                 health_status: str = "unknown", categories: List[str] = None):
        # 工具元数据初始化
```

**功能**:
- 封装MCP工具的完整元数据信息
- 提供工具状态的健康检查
- 支持工具的分类和组织

### 2. DiscoveryConfig - 发现配置类
```python
class DiscoveryConfig:
    """工具发现配置"""
    def __init__(self, discover_local: bool = True, discover_network: bool = False,
                 discover_config: bool = True, discovery_interval: int = 300,
                 local_port_range: tuple = (3000, 3010)):
        # 多源发现配置
```

**功能**:
- 配置工具发现的各个来源（本地、网络、配置文件）
- 设置发现间隔和端口范围
- 提供配置验证和序列化

### 3. MCPToolDiscoverer - MCP工具发现器核心类
```python
class MCPToolDiscoverer:
    """MCP工具发现器"""
    async def discover_all(self) -> List[MCPToolInfo]:
        # 发现所有可用的MCP工具
    async def discover_local_servers(self) -> List[MCPToolInfo]:
        # 发现本地MCP服务器
    async def discover_network_servers(self) -> List[MCPToolInfo]:
        # 发现网络MCP服务器
```

**功能**:
- 多源发现：支持本地、网络和配置文件的工具发现
- 异步并发：并行执行多个发现任务，提高效率
- 定期刷新：自动发现新工具和剔除失效工具
- 错误处理：优雅处理网络错误和服务器不可用

### 4. MCPToolRegistry - MCP工具注册表类
```python
class MCPToolRegistry:
    """MCP工具注册表"""
    def register_tool(self, tool: Any, metadata: Dict[str, Any] = None):
        # 注册工具及其元数据
    def search_tools(self, query: str, category: str = None) -> List[Dict]:
        # 搜索工具，支持类别过滤
    def calculate_match_score(self, name: str, description: str, query: str, metadata: Dict) -> float:
        # 计算工具匹配分数
```

**功能**:
- 工具注册：管理所有发现的MCP工具
- 智能搜索：基于多维度匹配算法的工具搜索
- 分类组织：按类别组织工具，便于导航
- 元数据管理：存储和检索工具扩展信息

### 5. MockMCPServer - 模拟MCP服务器（用于测试）
```python
class MockMCPServer:
    """模拟MCP服务器，用于测试发现功能"""
    async def start(self, host: str = "localhost", port: int = 3005):
        # 启动模拟服务器
    async def stop(self):
        # 停止服务器
```

**功能**:
- 测试支持：提供可配置的模拟MCP服务器
- 工具模拟：模拟真实MCP服务器的工具列表接口
- 健康状态：支持不同健康状态的测试场景

## 🔍 发现机制

### 多源发现架构
```
┌─────────────────────────────────────────────┐
│            MCPToolDiscoverer               │
├─────────────┬─────────────┬───────────────┤
│ 本地发现     │ 网络发现     │ 配置发现       │
│ Local       │ Network     │ Configuration │
│ Discovery   │ Discovery   │ Discovery     │
├─────────────┼─────────────┼───────────────┤
│ 端口扫描     │ DNS解析      │ 配置文件读取    │
│ 服务器探测    │ 服务发现协议  │ 静态配置解析    │
└─────────────┴─────────────┴───────────────┘
```

### 发现流程
1. **配置初始化**: 根据DiscoveryConfig设置发现源
2. **并行发现**: 异步并发执行本地、网络和配置发现
3. **结果合并**: 合并所有发现结果，去重处理
4. **工具注册**: 将发现的工具注册到MCPToolRegistry
5. **定期刷新**: 定时重新发现，保持工具列表最新

### 智能搜索算法
**匹配分数计算维度**（权重递减）：
1. **名称匹配** (权重: 2.0): 查询词出现在工具名称中
2. **描述匹配** (权重: 1.0): 查询词出现在工具描述中
3. **标签匹配** (权重: 0.5): 查询词出现在工具标签中
4. **类别匹配** (权重: 0.3): 查询词出现在工具类别中

**搜索优化**:
- 前缀匹配优先
- 多关键词支持
- 模糊匹配（未来扩展）

## 🧪 测试与演示

### 运行测试
```bash
python mcp_tool_discovery_demo.py --test
```

**测试内容**:
- ✅ MCPToolInfo类测试
- ✅ DiscoveryConfig类测试
- ✅ MCPToolDiscoverer本地发现测试
- ✅ MCPToolDiscoverer网络发现测试
- ✅ MCPToolRegistry注册表测试
- ✅ 搜索算法匹配测试
- ✅ MockMCPServer模拟测试

### 运行演示
```bash
python mcp_tool_discovery_demo.py --demo
```

**演示内容**:
1. 创建发现配置
2. 初始化MCPToolDiscoverer
3. 执行本地服务器发现
4. 发现结果展示和分析
5. 工具注册表操作演示
6. 智能搜索功能演示
7. 定期刷新机制演示

## 🔄 与MCP工具集成

### 集成模式
```python
# 创建工具发现器
config = DiscoveryConfig(
    discover_local=True,
    discover_network=True,
    discover_config=True,
    discovery_interval=300
)
discoverer = MCPToolDiscoverer(config)

# 创建工具注册表
registry = MCPToolRegistry()

# 发现并注册工具
discovered_tools = await discoverer.discover_all()
for tool_info in discovered_tools:
    registry.register_tool(tool_info, metadata={
        'categories': ['ai', 'automation'],
        'tags': ['mcp', 'tool']
    })

# 搜索工具
results = registry.search_tools("代码生成", category="ai")
for result in results[:5]:
    print(f"{result['tool_name']}: {result['description']} (分数: {result['score']})")
```

### 集成优势
1. **自动发现**: 自动发现环境中的MCP工具，无需手动配置
2. **智能搜索**: 基于多维度匹配的精准工具搜索
3. **动态更新**: 定期刷新工具列表，适应环境变化
4. **统一管理**: 集中管理所有工具及其元数据

## ⚠️ 生产环境注意事项

### 网络发现安全
1. **端口扫描限制**: 遵守网络安全政策，限制扫描范围和频率
2. **认证支持**: 支持需要认证的MCP服务器发现
3. **网络隔离**: 处理跨网络分区的发现场景
4. **服务发现协议**: 考虑集成DNS-SD、mDNS等标准协议

### 性能优化
1. **并发控制**: 控制并发发现任务数量，避免资源耗尽
2. **结果缓存**: 缓存发现结果，减少重复发现开销
3. **增量更新**: 实现增量发现，只更新变化的工具
4. **分布式发现**: 分布式环境下使用共识算法协调发现

### 可扩展性设计
1. **插件式发现源**: 支持自定义发现源插件
2. **可配置匹配算法**: 允许自定义匹配算法权重
3. **元数据扩展**: 支持自定义元数据字段
4. **多语言支持**: 考虑多语言工具描述的支持

## 📊 性能优化

### 异步并发优化
```python
# 使用异步并发执行多个发现任务
async def discover_all(self):
    tasks = []
    if self.config.discover_local:
        tasks.append(self.discover_local_servers())
    if self.config.discover_network:
        tasks.append(self.discover_network_servers())
    if self.config.discover_config:
        tasks.append(self.discover_configured_servers())
    
    # 并行执行所有发现任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 缓存策略
```python
# 实现发现结果缓存
class CachedMCPToolDiscoverer(MCPToolDiscoverer):
    def __init__(self, config: DiscoveryConfig, cache_ttl: int = 300):
        super().__init__(config)
        self.cache: Dict[str, List[MCPToolInfo]] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = cache_ttl
    
    async def discover_with_cache(self, source: str) -> List[MCPToolInfo]:
        current_time = time.time()
        if (source in self.cache and 
            current_time - self.cache_timestamps[source] < self.cache_ttl):
            return self.cache[source]
        
        # 执行实际发现
        tools = await self._discover_source(source)
        self.cache[source] = tools
        self.cache_timestamps[source] = current_time
        return tools
```

### 搜索性能优化
```python
# 使用倒排索引加速搜索
class IndexedMCPToolRegistry(MCPToolRegistry):
    def __init__(self):
        super().__init__()
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
    
    def register_tool(self, tool: Any, metadata: Dict[str, Any] = None):
        super().register_tool(tool, metadata)
        
        # 建立倒排索引
        tool_name = getattr(tool, 'name', str(tool))
        description = getattr(tool, 'description', '')
        
        # 为名称和描述中的词建立索引
        for word in self._extract_words(tool_name + ' ' + description):
            self.inverted_index[word.lower()].append(tool_name)
```

## 📝 作业要求

### 基础作业
1. 实现MCPToolDiscoverer的本地服务器发现功能，通过所有测试
2. 创建MCPToolRegistry并实现基本的工具搜索功能
3. 编写工具发现流程的详细文档

### 扩展挑战
1. 实现网络服务器发现，支持DNS服务发现协议
2. 添加工具健康检查功能，自动剔除不健康的工具
3. 实现分布式工具发现系统，支持多节点协调
4. 设计基于机器学习的工具推荐算法

## 🚀 下一步学习

### 相关课程
- **第73节课**: 消息队列集成
- **第74节课**: 缓存策略实现
- **第75节课**: 分布式锁机制

### 实战项目
- **工具发现网关**: 实现统一的MCP工具发现网关
- **工具市场**: 构建MCP工具市场，支持工具发布和发现
- **智能推荐系统**: 开发基于用户行为的工具推荐系统

## 📚 扩展学习

### 服务发现技术
1. **服务发现协议**: 深入研究DNS-SD、mDNS、etcd、Consul等协议
2. **分布式一致性**: 了解Raft、Paxos等共识算法在服务发现中的应用
3. **服务网格**: 学习Istio、Linkerd等服务网格中的服务发现机制

### 搜索与推荐
1. **信息检索**: 学习倒排索引、TF-IDF、BM25等搜索算法
2. **推荐系统**: 了解协同过滤、内容推荐等推荐算法
3. **语义搜索**: 研究基于Embedding的语义搜索技术

### 元数据管理
1. **数据目录**: 学习Amundsen、DataHub等数据目录系统
2. **元数据标准**: 了解Schema.org、Dublin Core等元数据标准
3. **治理与质量**: 掌握元数据治理和数据质量管理

## 🔧 故障排除

### 常见问题
1. **端口扫描被阻止**: 检查防火墙设置和安全策略
2. **发现性能低下**: 调整并发数量，优化网络请求
3. **搜索结果不准确**: 调整匹配算法权重，优化工具描述
4. **内存泄漏**: 检查工具注册表的清理机制

### 调试技巧
1. **启用详细日志**: 设置日志级别为DEBUG查看发现过程
2. **使用网络抓包**: 使用Wireshark分析MCP协议通信
3. **模拟环境测试**: 使用MockMCPServer进行隔离测试
4. **性能分析**: 使用cProfile分析发现性能瓶颈

## 📞 支持与资源

### 官方文档
- [MCP协议规范](https://spec.modelcontextprotocol.io/)
- [Python asyncio文档](https://docs.python.org/3/library/asyncio.html)
- [HTTPX官方文档](https://www.python-httpx.org/)

### 工具资源
- [服务发现工具比较](https://www.consul.io/docs/intro/vs)
- [端口扫描工具Nmap](https://nmap.org/)
- [网络调试工具Wireshark](https://www.wireshark.org/)

### 社区支持
- DeerFlow Discord频道 #mcp-tools
- GitHub Discussions
- Stack Overflow #model-context-protocol标签

---

**课程设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月11日  
**教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）  
**版权所有**: © 2024 DeerFlow Team. 保留所有权利。