# 🎓 详细教案 - Day 18 第72节课：MCP工具发现

## 📋 课程基本信息
- **课程名称**: MCP工具发现
- **授课日期**: 2024年4月11日（周四）
- **上课时间**: 12:00-12:45（第72节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: 已掌握MCP客户端架构、延迟加载策略和OAuth集成，理解网络通信和异步编程
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线，支持实时代码演示

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. 理解MCP工具发现机制的设计原理和实现模式
2. 掌握动态工具发现、注册和搜索的架构设计
3. 了解工具元数据管理和分类组织的最佳实践

### 技能目标（学生将能够）
1. 实现MCP工具发现服务，支持本地和网络服务器发现
2. 创建工具注册表，支持工具分类、搜索和元数据管理
3. 设计智能工具匹配和推荐算法

### 情感/态度目标
1. 培养系统化工具管理和生态建设思维
2. 增强用户体验和工具可用性设计意识
3. 激发对服务发现和元数据管理技术的研究兴趣

## 📚 教学重点与难点
- **教学重点**: 动态工具发现机制、工具注册表设计、智能搜索算法
- **教学难点**: 多源发现协调、异步并发处理、匹配算法设计
- **突破方法**: 
  1. 通过实际案例（如IDE插件市场）解释工具发现的价值
  2. 分步构建发现系统，从简单发现到智能搜索
  3. 可视化展示工具发现过程和匹配结果

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（可运行多个本地服务）
- **软件**: Python 3.12.0、VS Code、网络扫描工具、数据库管理工具
- **服务**: 本地MCP服务器示例、网络MCP服务器模拟器
- **代码**: DeerFlow 2.0代码库、MCP工具发现示例代码、测试工具
- **演示材料**: PPT幻灯片（发现流程图、注册表架构图、搜索算法图）
- **学生材料**: 练习任务卡、API文档、测试用例集
- **在线工具**: 网络端口扫描工具、服务发现工具、数据可视化工具

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员，回顾上节课（OAuth集成）要点<br>2. 提出发现问题："MCP工具分散在不同服务器，如何自动发现？"<br>3. 介绍本节课主题和学习目标 | 1. 登录课堂，开启开发环境<br>2. 思考工具发现的技术方案<br>3. 明确本节课学习目标 | PPT幻灯片第1-3页（发现问题导入） |
| 2-5分钟 | 知识激活 | 1. 提问："大家使用过哪些需要发现服务的系统？（如Docker Compose、Kubernetes）"<br>2. 引导思考服务发现的价值和挑战<br>3. 介绍MCP工具发现的应用场景 | 1. 回答提问，分享经验<br>2. 讨论服务发现的实现方案<br>3. 理解工具发现对用户体验的影响 | 白板、互动问答工具、学员讨论区 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-10分钟 | 概念讲解 | 1. 讲解MCP工具发现的多源发现机制<br>2. 展示工具发现服务的架构图<br>3. 举例说明工具发现在AI Agent生态中的应用 | 1. 听讲记录发现机制核心概念<br>2. 观看架构图理解组件关系<br>3. 思考工具发现对系统扩展性的价值 | PPT幻灯片第4-8页（工具发现架构图） |
| 10-15分钟 | 深入分析 | 1. 分析MCPToolDiscoverer的核心方法：discover_all、discover_local_servers、get_server_tools<br>2. 对比不同发现源（本地、网络、配置）的特点和挑战<br>3. 解释异步并发发现和结果合并机制 | 1. 跟随分析理解方法设计<br>2. 记录不同发现源的适用场景<br>3. 理解并发发现的技术实现 | 代码示例（MCPToolDiscoverer类）、对比表格 |
| 15-20分钟 | 算法讲解 | 1. 讲解工具注册表的搜索匹配算法原理<br>2. 演示匹配分数计算方法和排序策略<br>3. 展示工具分类和组织的数据结构设计 | 1. 观察算法实现细节<br>2. 理解匹配分数计算的各个维度<br>3. 记录元数据管理的关键设计 | 代码示例（MCPToolRegistry类）、算法流程图 |

### 阶段3：实践练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 指导练习 | 1. 发布练习任务："实现discover_local_servers方法"<br>2. 提供步骤指导：端口扫描、服务器探测、工具获取<br>3. 巡视个别指导，解答疑问 | 1. 理解练习要求，阅读任务说明<br>2. 按照指导步骤动手实现<br>3. 遇到问题及时提问 | 练习任务卡（本地服务器发现实现步骤）、代码模板 |
| 25-30分钟 | 独立实践 | 1. 观察学生进展，收集常见问题<br>2. 准备集中讲解的共性问题<br>3. 提示网络编程注意事项和错误处理 | 1. 独立完成本地服务器发现实现<br>2. 调试解决遇到的问题<br>3. 记录实现过程中的技术难点 | 开发环境、本地MCP服务器示例、网络调试工具 |
| 30-35分钟 | 成果展示 | 1. 邀请1-2名学生分享实现成果<br>2. 点评学生代码，强调健壮性和性能考虑<br>3. 总结工具发现实现的关键技术点 | 1. 展示完成的本地服务器发现功能<br>2. 分享实现心得和测试结果<br>3. 听取教师反馈和改进建议 | 屏幕共享、发现结果报告、代码审查要点 |

### 阶段4：总结与延伸（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 回顾本节课重点：工具发现机制、注册表设计、搜索算法<br>2. 强调工具发现在MCP生态中的重要性<br>3. 梳理知识结构图 | 1. 参与总结，补充学习收获<br>2. 完善知识结构笔记<br>3. 提问澄清模糊概念 | 思维导图（工具发现知识结构）、总结PPT |
| 38-41分钟 | 拓展延伸 | 1. 介绍高级工具发现主题：分布式发现、共识算法、版本兼容性<br>2. 展示企业级工具发现系统案例<br>3. 推荐服务发现和元数据管理阅读材料 | 1. 了解工具发现前沿技术<br>2. 思考工具发现在自身项目中的应用<br>3. 规划深入学习路径 | 技术博客（服务发现最佳实践）、开源项目案例 |
| 41-43分钟 | 作业布置 | 1. 说明作业要求：实现完整的MCPToolRegistry并测试搜索功能<br>2. 提供完成建议：设计测试工具集、实现多种搜索场景<br>3. 明确提交方式和截止时间 | 1. 记录作业要求和技术要点<br>2. 理解评价标准（功能完整、搜索准确率、代码质量）<br>3. 规划完成时间和寻求帮助方式 | 作业说明文档、测试工具数据集、搜索测试用例 |
| 43-45分钟 | 反馈收集 | 1. 收集课堂反馈（理解程度、教学节奏）<br>2. 解答剩余问题<br>3. 预告下一天内容（反射系统与动态加载） | 1. 提供学习反馈和建议<br>2. 提出未解决的问题<br>3. 预习下一天内容 | 课堂反馈表、课程日历、预习材料 |

## 🎭 师生互动设计

### 提问策略
1. **导入提问**: "如果有100个MCP服务器分布在不同的机器上，如何让客户端自动发现所有可用工具？"
2. **引导提问**: "工具发现过程中，如何处理网络延迟和服务器不可用的情况？"
3. **挑战提问**: "工具搜索时如何平衡匹配准确性和响应速度？"
4. **应用提问**: "在你的项目中，如何设计工具发现机制来支持插件系统？"

### 讨论活动
1. **小组讨论**: 3人一组，讨论不同服务发现协议（DNS-SD、mDNS、etcd）的优缺点
2. **头脑风暴**: 集体创意，设计工具发现的监控和告警机制
3. **案例分析**: 分析开源项目（如VS Code扩展市场）的工具发现实现
4. **算法优化**: 讨论如何改进工具匹配算法，提高搜索准确性

### 反馈机制
1. **即时反馈**: 课堂问答，及时纠正概念误解
2. **过程反馈**: 练习指导中，针对网络编程和并发处理提供具体建议
3. **成果反馈**: 作业批改，详细点评发现功能和搜索效果
4. **性能反馈**: 提供性能测试结果，量化发现系统的效率

## 🔧 差异化教学

### 针对基础薄弱学生
1. **简化任务**: 提供MCPToolDiscoverer完整框架，只需实现核心发现方法
2. **额外支持**: 一对一辅导，重点讲解网络编程和异步并发
3. **资源推荐**: 提供Python网络编程和异步IO复习材料
4. **成功体验**: 设计可运行的简单示例，展示基本的工具发现功能

### 针对进阶学生
1. **扩展挑战**: 实现分布式工具发现系统，支持多节点协调和故障转移
2. **创新空间**: 设计基于机器学习的工具推荐算法
3. **研究任务**: 调研不同服务发现协议在MCP场景中的适用性
4. **领导机会**: 在小组讨论中担任架构师，帮助其他同学设计发现系统

## 📊 评估方式
1. **课堂参与度**（20%）：提问回答、讨论贡献、练习完成度
2. **练习成果**（30%）：本地服务器发现实现完整性和正确性
3. **作业质量**（40%）：MCPToolRegistry实现、搜索功能、代码质量
4. **学习态度**（10%）：主动提问、帮助同学、课后反馈

## 🚨 应急预案
1. **网络环境问题**: 准备本地模拟的MCP服务器，确保演示可用
2. **端口冲突**: 提供可配置的端口范围，避免与其他服务冲突
3. **时间不足**: 重点讲解核心概念，简化实现细节，提供课后补充材料
4. **学生困惑**: 增加一对一辅导时间，录制重点内容讲解视频
5. **性能问题**: 优化演示代码，使用轻量级测试服务器

## 🤔 教学反思
（本节课后填写）
1. **学生掌握情况**: 
2. **教学难点突破效果**: 
3. **互动设计有效性**: 
4. **时间分配合理性**: 
5. **改进措施**: 

## 📝 课后任务
1. **核心作业**: 实现完整的MCPToolRegistry类，支持工具注册、分类、搜索功能
2. **扩展任务**: 为工具发现系统添加健康检查和自动剔除功能
3. **阅读任务**: 阅读服务发现和元数据管理相关论文/文章
4. **预习任务**: 预习Day 19"反射系统与动态加载"内容
5. **项目联系**: 设计自己项目的工具发现机制，考虑扩展性和性能

## 📎 附录

### 附录1：PPT幻灯片大纲
1. 封面页：MCP工具发现 - Day 18 第72节课
2. 课程目标：知识/技能/态度三维目标
3. 问题导入：分布式MCP工具的发现挑战
4. 发现机制：多源发现架构、流程图、数据流
5. 注册表设计：MCPToolRegistry类图、数据结构
6. 搜索算法：匹配分数计算、排序策略、分类组织
7. 性能优化：异步并发、缓存策略、错误处理
8. 代码演示：关键代码片段和运行结果
9. 练习任务：本地服务器发现实现步骤
10. 知识总结：本节课核心知识点图谱
11. 拓展延伸：高级工具发现技术与企业应用
12. 作业布置：MCPToolRegistry实现要求
13. 结束页：预告下一天内容

### 附录2：课堂练习任务卡
**任务名称**: 本地MCP服务器发现实现
**任务目标**: 理解工具发现机制，掌握网络服务和端口扫描技术

**实现步骤**:
1. 实现discover_local_servers方法，扫描指定端口范围（如3000-3010）
2. 为每个端口尝试连接，发送MCP协议探测请求
3. 对于响应的服务器，调用get_server_tools方法获取工具列表
4. 将发现的结果转换为MCPToolInfo对象列表
5. 添加超时处理和错误恢复机制
6. 实现简单的端口扫描并发优化
7. 添加发现结果缓存，避免重复扫描

**测试用例**:
```python
async def test_local_discovery():
    config = DiscoveryConfig(
        discover_local=True,
        discover_network=False,
        discover_config=False,
        discovery_interval=300
    )
    
    discoverer = MCPToolDiscoverer(config)
    
    # 启动本地测试服务器（模拟）
    # test_server = start_test_mcp_server(port=3005)
    
    # 执行本地发现
    local_tools = await discoverer.discover_local_servers()
    
    print(f"发现 {len(local_tools)} 个本地工具:")
    for tool in local_tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # 清理
    # await test_server.stop()
```

**完成标准**:
- [ ] 方法实现完整，逻辑清晰
- [ ] 支持端口范围扫描和并发探测
- [ ] 正确处理网络超时和连接错误
- [ ] 实现结果缓存和去重
- [ ] 代码符合PEP 8规范，有适当类型注解
- [ ] 包含完整的错误处理和日志记录

### 附录3：学生自我评估表
**姓名**: ___________ **日期**: ___________

| 评估项目 | 完全掌握 | 基本掌握 | 需要复习 | 备注 |
|----------|----------|----------|----------|------|
| 工具发现机制原理 | □ | □ | □ | |
| MCPToolDiscoverer设计 | □ | □ | □ | |
| 网络服务探测技术 | □ | □ | □ | |
| 异步并发发现实现 | □ | □ | □ | |
| MCPToolRegistry设计 | □ | □ | □ | |
| 工具搜索匹配算法 | □ | □ | □ | |
| 元数据管理和分类 | □ | □ | □ | |

**学习收获**:
1. 本节课我学到的最重要的三点是：
   - 
   - 
   - 
2. 我仍然困惑的问题是：
   - 
   - 
3. 我希望在后续课程中学习的内容：
   - 

**学习建议**:
- 对本节课的教学内容：_________________________________
- 对教学方式：_________________________________________
- 对练习设计：_________________________________________

### 附录4：教师观察记录表
**观察时间**: ___________ **观察者**: ___________

| 观察维度 | 观察要点 | 表现记录 | 改进建议 |
|----------|----------|----------|----------|
| 概念理解 | 发现机制、注册表、搜索算法 | | |
| 网络编程 | 端口扫描、服务探测、错误处理 | | |
| 并发处理 | 异步编程、任务协调、性能优化 | | |
| 算法实现 | 匹配算法、排序策略、数据结构 | | |
| 学习态度 | 主动性、探索精神、协作意识 | | |

**重点关注学生**:
1. 需要额外支持的学生：___________ 支持措施：___________
2. 表现突出的学生：___________ 拓展建议：___________

**课堂整体情况**:
- 网络编程掌握程度：□ 优秀 □ 良好 □ 一般 □ 需要加强
- 算法实现质量：□ 优秀 □ 良好 □ 一般 □ 需要加强
- 实践完成情况：□ 优秀 □ 良好 □ 一般 □ 需要加强
- 时间分配：□ 合理 □ 需要调整

### 附录5：关键代码示例
```python
from typing import Dict, List, Optional, Any
import asyncio
from collections import defaultdict
import logging
from httpx import AsyncClient
import json

logger = logging.getLogger(__name__)

class MCPToolInfo:
    """MCP工具信息"""
    def __init__(
        self,
        name: str,
        description: str,
        server_url: str,
        server_type: str,
        health_status: str = "unknown"
    ):
        self.name = name
        self.description = description
        self.server_url = server_url
        self.server_type = server_type
        self.health_status = health_status

class DiscoveryConfig:
    """发现配置"""
    def __init__(
        self,
        discover_local: bool = True,
        discover_network: bool = False,
        discover_config: bool = True,
        discovery_interval: int = 300,
        local_port_range: tuple = (3000, 3010)
    ):
        self.discover_local = discover_local
        self.discover_network = discover_network
        self.discover_config = discover_config
        self.discovery_interval = discovery_interval
        self.local_port_range = local_port_range

class MCPToolDiscoverer:
    """MCP工具发现器"""
    
    def __init__(self, config: DiscoveryConfig):
        self.config = config
        self.discovered_tools: Dict[str, MCPToolInfo] = {}
        self.discovery_interval = config.discovery_interval
    
    async def start_discovery(self):
        """启动工具发现服务"""
        logger.info("启动MCP工具发现服务")
        
        # 初始发现
        await self.discover_all()
        
        # 定期刷新
        while True:
            await asyncio.sleep(self.discovery_interval)
            logger.info("执行定期工具发现刷新")
            await self.refresh_discovery()
    
    async def discover_all(self):
        """发现所有可用的MCP工具"""
        tasks = []
        
        # 发现本地MCP服务器
        if self.config.discover_local:
            tasks.append(self.discover_local_servers())
        
        # 发现网络MCP服务器
        if self.config.discover_network:
            tasks.append(self.discover_network_servers())
        
        # 发现配置文件中的服务器
        if self.config.discover_config:
            tasks.append(self.discover_configured_servers())
        
        # 并行执行所有发现任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并发现结果
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"发现失败: {result}")
                continue
            
            for tool_info in result:
                self.discovered_tools[tool_info.name] = tool_info
        
        logger.info(f"发现完成，共找到 {len(self.discovered_tools)} 个工具")
    
    async def discover_local_servers(self) -> List[MCPToolInfo]:
        """发现本地MCP服务器"""
        tools = []
        start_port, end_port = self.config.local_port_range
        
        logger.info(f"扫描本地端口 {start_port}-{end_port} 寻找MCP服务器")
        
        for port in range(start_port, end_port + 1):
            server_url = f"http://localhost:{port}"
            
            try:
                server_info = await self.probe_server(server_url)
                if server_info:
                    # 获取服务器提供的工具
                    server_tools = await self.get_server_tools(server_url)
                    
                    for tool in server_tools:
                        tool_info = MCPToolInfo(
                            name=tool["name"],
                            description=tool.get("description", ""),
                            server_url=server_url,
                            server_type="local",
                            health_status="healthy",
                        )
                        tools.append(tool_info)
                        logger.debug(f"发现本地工具: {tool['name']} @ {server_url}")
            except (asyncio.TimeoutError, ConnectionError) as e:
                logger.debug(f"端口 {port} 无MCP服务器: {e}")
                continue
            except Exception as e:
                logger.warning(f"端口 {port} 探测失败: {e}")
                continue
        
        logger.info(f"本地发现完成，找到 {len(tools)} 个工具")
        return tools
    
    async def get_server_tools(self, server_url: str) -> List[Dict]:
        """获取服务器提供的工具列表"""
        try:
            async with AsyncClient() as client:
                response = await client.post(
                    f"{server_url}/jsonrpc",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/list",
                        "params": {},
                    },
                    timeout=5.0,
                )
                
                result = response.json().get("result", {})
                return result.get("tools", [])
        except Exception as e:
            logger.warning(f"获取服务器 {server_url} 工具失败: {e}")
            return []
    
    async def refresh_discovery(self):
        """刷新发现结果"""
        # 清除旧结果，重新发现
        old_count = len(self.discovered_tools)
        self.discovered_tools.clear()
        
        await self.discover_all()
        
        new_count = len(self.discovered_tools)
        logger.info(f"发现刷新完成: {old_count} -> {new_count} 个工具")

class MCPToolRegistry:
    """MCP工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.categories: Dict[str, List[str]] = defaultdict(list)
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, tool: Any, metadata: Dict[str, Any] = None):
        """注册MCP工具"""
        tool_name = getattr(tool, 'name', str(tool))
        
        if tool_name in self.tools:
            logger.warning(f"工具 {tool_name} 已注册，将覆盖")
        
        self.tools[tool_name] = tool
        
        if metadata:
            self.metadata[tool_name] = metadata
            
            # 按类别组织
            categories = metadata.get('categories', [])
            for category in categories:
                self.categories[category].append(tool_name)
        
        logger.info(f"注册工具: {tool_name}")
    
    def get_tool(self, name: str) -> Optional[Any]:
        """获取工具"""
        return self.tools.get(name)
    
    def search_tools(self, query: str, category: str = None) -> List[Dict]:
        """搜索工具"""
        results = []
        
        for tool_name, tool in self.tools.items():
            metadata = self.metadata.get(tool_name, {})
            
            # 按类别过滤
            if category and category not in metadata.get('categories', []):
                continue
            
            # 计算匹配分数
            description = getattr(tool, 'description', '')
            score = self.calculate_match_score(tool_name, description, query, metadata)
            
            if score > 0:
                result = {
                    'tool_name': tool_name,
                    'description': description,
                    'score': score,
                    'metadata': metadata,
                }
                results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"搜索 '{query}' 找到 {len(results)} 个结果")
        return results
    
    def calculate_match_score(self, name: str, description: str, query: str, metadata: Dict) -> float:
        """计算匹配分数"""
        if not query:
            return 0.0
        
        query_lower = query.lower()
        score = 0.0
        
        # 名称匹配（权重最高）
        if query_lower in name.lower():
            score += 2.0
        
        # 描述匹配
        if query_lower in description.lower():
            score += 1.0
        
        # 标签匹配
        tags = metadata.get('tags', [])
        for tag in tags:
            if query_lower in tag.lower():
                score += 0.5
        
        # 类别匹配
        categories = metadata.get('categories', [])
        for category in categories:
            if query_lower in category.lower():
                score += 0.3
        
        return score
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """获取指定类别的工具"""
        return self.categories.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self.categories.keys())
```

### 附录6：延伸学习资源
1. **服务发现资料**:
   - "微服务模式：服务发现" - Chris Richardson
   - "Consul服务发现实践" - HashiCorp官方文档
   - "etcd在服务发现中的应用" - CoreOS技术文档

2. **搜索算法**:
   - "信息检索导论" - Christopher D. Manning
   - "搜索引擎核心技术" - 技术书籍
   - "推荐系统算法实践" - 机器学习应用指南

3. **技术文章**:
   - "MCP工具生态建设实践" - DeerFlow官方博客
   - "分布式服务发现架构设计" - 大型互联网公司技术分享
   - "元数据管理的最佳实践" - 数据管理专家博客

4. **工具资源**:
   - [Python异步网络编程](https://docs.python.org/3/library/asyncio.html)
   - [服务发现工具比较](https://www.consul.io/docs/intro/vs)
   - [元数据管理框架](https://github.com/lyft/amundsen)

---
**课程设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月11日  
**版权所有**: © 2024 DeerFlow Team. 保留所有权利。