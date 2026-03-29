# 📚 Day 18 第72节课：MCP工具发现 - 课后练习

## 🎯 练习目标
通过本练习，你将掌握：
1. MCP工具发现机制的设计原理和实现模式
2. 动态工具发现、注册和搜索的架构设计
3. 工具元数据管理和分类组织的最佳实践
4. 智能工具匹配和推荐算法的实现

## ⏰ 预计用时
- 基础任务：70分钟
- 扩展挑战：120分钟
- 总计：3小时10分钟

## 🔧 环境准备
```bash
# 1. 激活虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install httpx>=0.27.0 pytest>=8.0.0 pytest-asyncio>=0.23.0

# 3. 克隆演示代码
cp -r ../课堂演示代码/day18-lesson72/ ./work/
cd work

# 4. 验证环境
python -c "import httpx; print('HTTPX版本:', httpx.__version__)"
```

## 📝 练习任务

### 任务1：理解MCP工具发现架构（15分钟）
**目标**: 理解MCP工具发现的多源发现机制和架构设计

**步骤**:
1. 阅读`MCPToolDiscoverer`类和`DiscoveryConfig`类的源代码
2. 回答以下问题：
   - 什么是多源发现机制？包括哪些发现源？
   - 为什么需要异步并发执行发现任务？
   - `discovery_interval`参数的作用是什么？
   - 本地端口扫描的范围如何配置？为什么需要限制范围？
3. 绘制工具发现架构图，标注核心组件和数据流

**思考题**:
- 如果发现过程中某个服务器不可用，应该如何优雅处理？
- 如何避免重复发现相同的工具？
- 网络发现与本地发现在实现上有哪些不同？

### 任务2：实现本地服务器发现功能（30分钟）
**目标**: 实现`MCPToolDiscoverer`的本地服务器发现功能

**要求**:
基于提供的代码框架，完成以下方法的实现：

```python
async def discover_local_servers(self) -> List[MCPToolInfo]:
    """
    发现本地MCP服务器
    
    实现步骤：
    1. 获取配置的本地端口范围（config.local_port_range）
    2. 对每个端口进行异步探测
    3. 使用probe_server方法检查是否为MCP服务器
    4. 如果是MCP服务器，调用get_server_tools获取工具列表
    5. 将工具信息转换为MCPToolInfo对象
    6. 添加适当的错误处理和日志记录
    7. 实现简单的并发优化（如asyncio.gather）
    
    返回:
        发现的工具列表（MCPToolInfo对象）
    """
    # TODO: 实现本地服务器发现
    pass
```

**具体实现要求**:
1. **端口扫描**: 扫描指定端口范围（默认3000-3010）
2. **服务器探测**: 对每个端口尝试连接，发送MCP协议探测请求
3. **工具获取**: 对于响应的服务器，调用`get_server_tools`方法获取工具列表
4. **错误处理**: 添加超时处理、连接错误恢复机制
5. **并发优化**: 使用`asyncio.gather`实现并发端口扫描
6. **结果缓存**: 实现简单的发现结果缓存，避免重复扫描

**测试用例**:
```python
async def test_local_discovery():
    """测试本地服务器发现功能"""
    config = DiscoveryConfig(
        discover_local=True,
        discover_network=False,
        discover_config=False,
        discovery_interval=300,
        local_port_range=(3000, 3005)
    )
    
    discoverer = MCPToolDiscoverer(config)
    
    # 执行本地发现
    local_tools = await discoverer.discover_local_servers()
    
    print(f"发现 {len(local_tools)} 个本地工具:")
    for tool in local_tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # 验证发现结果
    assert len(local_tools) >= 0  # 至少返回空列表
    for tool in local_tools:
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'server_url')
```

### 任务3：实现工具注册表搜索功能（25分钟）
**目标**: 实现`MCPToolRegistry`的搜索功能和匹配算法

**要求**:
完成以下方法的实现：

```python
def search_tools(self, query: str, category: str = None) -> List[Dict]:
    """
    搜索工具，支持类别过滤和智能匹配
    
    实现步骤：
    1. 遍历所有已注册的工具
    2. 如果指定了类别，先进行类别过滤
    3. 对每个工具计算匹配分数（使用calculate_match_score）
    4. 只保留分数大于0的结果
    5. 按分数降序排序
    6. 返回格式化的搜索结果
    
    参数:
        query: 搜索查询词
        category: 可选的类别过滤器
        
    返回:
        搜索结果列表，每个元素包含：
        {
            'tool_name': str,
            'description': str,
            'score': float,
            'metadata': dict
        }
    """
    # TODO: 实现工具搜索
    pass
```

**匹配算法实现**:
```python
def calculate_match_score(self, name: str, description: str, query: str, metadata: Dict) -> float:
    """
    计算工具匹配分数
    
    匹配维度（权重递减）：
    1. 名称匹配（权重: 2.0）：查询词出现在工具名称中
    2. 描述匹配（权重: 1.0）：查询词出现在工具描述中
    3. 标签匹配（权重: 0.5）：查询词出现在工具标签中（metadata['tags']）
    4. 类别匹配（权重: 0.3）：查询词出现在工具类别中（metadata['categories']）
    
    返回:
        匹配分数（float）
    """
    # TODO: 实现匹配分数计算
    pass
```

**具体实现要求**:
1. **多维度匹配**: 实现名称、描述、标签、类别四个维度的匹配
2. **权重分配**: 按照指定权重计算总分
3. **类别过滤**: 支持按类别筛选工具
4. **排序功能**: 按匹配分数降序排序
5. **结果格式化**: 返回标准化的搜索结果格式

**测试用例**:
```python
def test_search_tools():
    """测试工具搜索功能"""
    registry = MCPToolRegistry()
    
    # 注册测试工具
    tool1 = MockTool(name="代码生成器", description="生成Python代码的工具")
    tool2 = MockTool(name="图像处理工具", description="处理图像和照片的工具")
    
    registry.register_tool(tool1, {
        'categories': ['ai', 'code'],
        'tags': ['generation', 'python']
    })
    registry.register_tool(tool2, {
        'categories': ['image', 'media'],
        'tags': ['processing', 'photo']
    })
    
    # 测试搜索
    results = registry.search_tools("代码")
    assert len(results) == 1
    assert results[0]['tool_name'] == "代码生成器"
    assert results[0]['score'] > 0
    
    # 测试类别过滤
    results = registry.search_tools("工具", category="image")
    assert len(results) == 1
    assert results[0]['tool_name'] == "图像处理工具"
```

### 任务4：集成测试与优化（扩展任务，60分钟）
**目标**: 将各个组件集成，实现完整的工具发现系统

**要求**:
1. **创建集成测试**: 编写集成测试，模拟多个MCP服务器并测试发现流程
2. **实现定期刷新**: 扩展`MCPToolDiscoverer`，实现定期刷新发现结果的功能
3. **添加健康检查**: 为发现的工具添加健康状态检查和自动剔除功能
4. **性能优化**: 实现结果缓存，减少重复发现开销

**集成测试场景**:
```python
async def test_integration():
    """集成测试：完整的工具发现流程"""
    # 1. 启动多个模拟MCP服务器
    servers = []
    for port in [3001, 3002, 3003]:
        server = MockMCPServer(port=port)
        await server.start()
        servers.append(server)
    
    # 2. 创建发现器和注册表
    config = DiscoveryConfig(
        discover_local=True,
        discover_network=False,
        discover_config=False,
        local_port_range=(3000, 3010)
    )
    
    discoverer = MCPToolDiscoverer(config)
    registry = MCPToolRegistry()
    
    # 3. 执行发现
    tools = await discoverer.discover_all()
    
    # 4. 注册工具
    for tool_info in tools:
        registry.register_tool(tool_info, {
            'categories': ['test'],
            'tags': ['mcp', 'test']
        })
    
    # 5. 测试搜索
    results = registry.search_tools("test")
    assert len(results) == len(tools)
    
    # 6. 清理
    for server in servers:
        await server.stop()
```

**性能优化要求**:
1. **并发控制**: 限制并发发现任务数量，避免资源耗尽
2. **缓存实现**: 为发现结果添加TTL缓存
3. **增量更新**: 实现增量发现，只更新变化的工具
4. **错误重试**: 为失败的网络请求添加重试机制

## 📤 提交要求

### 提交内容
1. **源代码文件**:
   - 完整的`MCPToolDiscoverer`类实现
   - 完整的`MCPToolRegistry`类实现
   - 所有测试用例代码

2. **文档文件**:
   - 架构设计说明（markdown格式）
   - 性能优化报告（包含基准测试结果）
   - 遇到的问题和解决方案记录

3. **演示视频**（可选）:
   - 3分钟演示视频，展示工具发现和搜索功能

### 提交格式
```
学号_姓名_第72节课_MCP工具发现.zip
├── src/
│   ├── mcp_tool_discoverer.py
│   ├── mcp_tool_registry.py
│   └── test_discovery.py
├── docs/
│   ├── 架构设计.md
│   ├── 性能优化报告.md
│   └── 问题解决记录.md
└── README.md
```

### 截止时间
- **提交截止**: 2024年4月12日 23:59
- **互评时间**: 2024年4月13日-14日
- **成绩公布**: 2024年4月15日

## 📊 评估标准

### 基础要求（70分）
1. **功能完整性**（30分）:
   - 本地服务器发现功能完整实现（10分）
   - 工具注册表搜索功能完整实现（10分）
   - 匹配算法正确实现（10分）

2. **代码质量**（20分）:
   - 代码符合PEP 8规范（5分）
   - 有适当的类型注解和文档字符串（5分）
   - 错误处理完善（5分）
   - 日志记录完整（5分）

3. **测试覆盖**（20分）:
   - 单元测试覆盖核心功能（10分）
   - 测试用例设计合理（5分）
   - 测试通过率100%（5分）

### 扩展挑战（30分）
1. **集成测试**（10分）:
   - 集成测试覆盖完整发现流程（5分）
   - 模拟多个MCP服务器场景（5分）

2. **性能优化**（10分）:
   - 实现结果缓存（5分）
   - 性能优化措施有效（5分）

3. **创新设计**（10分）:
   - 实现网络发现功能（5分）
   - 添加健康检查机制（5分）

### 加分项（额外10分）
1. **分布式发现**: 实现分布式工具发现系统
2. **机器学习推荐**: 实现基于机器学习的工具推荐算法
3. **可视化界面**: 提供工具发现的Web可视化界面

## 🔧 调试建议

### 常见问题解决
1. **端口扫描失败**:
   ```python
   # 检查防火墙设置
   # 确认端口范围配置正确
   # 使用telnet测试端口连通性
   ```

2. **异步并发问题**:
   ```python
   # 使用asyncio.gather时添加return_exceptions=True
   # 限制并发任务数量，避免资源耗尽
   # 添加适当的超时设置
   ```

3. **搜索匹配不准确**:
   ```python
   # 调试calculate_match_score方法
   # 检查工具元数据格式
   # 调整匹配算法权重
   ```

### 调试工具
1. **日志调试**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **网络调试**:
   ```python
   # 使用httpx的调试模式
   import httpx
   client = httpx.AsyncClient(transport=httpx.HTTPTransport(verify=False))
   ```

3. **性能分析**:
   ```bash
   python -m cProfile your_script.py
   ```

## 📞 支持资源

### 参考文档
- [MCP协议规范](https://spec.modelcontextprotocol.io/)
- [Python asyncio官方文档](https://docs.python.org/3/library/asyncio.html)
- [HTTPX异步HTTP客户端](https://www.python-httpx.org/async/)

### 示例代码
- 课堂演示代码：`../课堂演示代码/day18-lesson72/`
- DeerFlow 2.0 MCP发现模块：`deerflow/src/mcp/discovery/`

### 社区支持
- DeerFlow Discord频道 #mcp-tools
- GitHub Issues: https://github.com/bytedance/deer-flow/issues
- 学习小组讨论区

---

**注意事项**:
1. 请独立完成练习，如需合作请注明贡献者
2. 提交前请确保所有测试通过
3. 如遇技术问题，及时在讨论区提问
4. 鼓励创新设计，但需保证核心功能完整

**祝你练习顺利，掌握MCP工具发现的核心技术！** 🚀

---
*课程设计: DeerFlow Python Agent架构师训练营*  
*版本: v1.0.0*  
*最后更新: 2024年4月11日*