# Day 16 - 第62节课：MCP服务器配置 - 课后练习

## 📋 练习概述

本练习旨在巩固MCP服务器配置的核心概念和实践技能。通过完成以下练习，你将掌握：
1. MCP服务器配置的YAML格式和关键配置项
2. MCPServerManager的异步启动和管理机制
3. 多种MCP服务器类型（filesystem、sql、github等）的配置方法
4. 健康检查、错误处理和状态监控机制的实施
5. 环境变量在MCP配置中的动态替换和注入

**建议完成时间**：120分钟  
**难度等级**：中级  
**前置知识**：Python基础、异步编程、YAML配置、进程管理

## 🎯 学习目标

完成本练习后，你将能够：
- ✅ 编写正确的MCP服务器YAML配置文件
- ✅ 实现MCPServerManager异步启动和管理MCP服务器
- ✅ 配置多种MCP服务器类型并解决常见问题
- ✅ 实施健康检查和自动恢复机制
- ✅ 调试和解决MCP服务器启动失败问题
- ✅ 应用环境变量在MCP配置中的动态注入

## 📁 练习文件结构

```
课后练习/
├── mcp_config.yaml                 # MCP服务器配置文件（需要创建）
├── mcp_server_manager.py           # MCP服务器管理器实现（需要编写）
├── server_lifecycle.py             # 服务器生命周期管理（需要编写）
├── error_handler.py                # 错误处理和重试机制（需要编写）
├── environment_variables.py        # 环境变量注入实现（需要编写）
└── github_mcp_server.py           # GitHub MCP服务器配置（需要编写）
```

## 🔧 环境准备

1. **Python环境**：确保已安装Python 3.12+，推荐使用虚拟环境
2. **Node.js环境**：需要Node.js 18+用于运行MCP服务器（可选，可使用模拟服务器）
3. **依赖安装**：
   ```bash
   pip install pyyaml aiohttp pytest-asyncio
   ```
4. **参考代码**：使用课堂演示代码作为参考，位于`课堂演示代码/day16-lesson62/`
5. **模拟MCP服务器**（可选）：如果无法安装Node.js，可以使用提供的模拟服务器代码

## 📝 练习任务

### 任务1：MCP配置YAML设计（25分钟）

**目标**：设计一个完整的MCP服务器配置YAML，支持三种不同类型的MCP服务器。

**要求**：
1. 创建`mcp_config.yaml`文件，包含以下服务器配置：
   - **filesystem**：文件系统MCP服务器，提供文件访问功能
   - **sql**：SQL数据库MCP服务器，提供数据库访问功能
   - **github**：GitHub MCP服务器，提供GitHub API访问功能

2. 每个服务器需要配置：
   - 基本信息：命令、参数、环境变量
   - 网络配置：端口号、健康检查URL
   - 启动控制：是否自动启动、启动超时时间
   - 错误处理：最大重试次数、重试延迟
   - 安全配置：工作目录、用户权限（模拟）

3. 全局配置需要包含：
   - 日志级别：支持DEBUG、INFO、WARN、ERROR
   - 重试策略：全局最大重试次数和重试延迟
   - 监控配置：健康检查间隔、监控开关

**提示**：
- 参考课堂演示代码中的YAML配置示例
- 使用环境变量引用：`${GITHUB_TOKEN}`、`${DATABASE_URL}`
- 设置不同端口避免冲突：3001、3002、3003
- filesystem服务器参数：`["@modelcontextprotocol/server-filesystem", "/workspace"]`
- sql服务器参数：`["@modelcontextprotocol/server-sql", "${DATABASE_URL}"]`
- github服务器参数：`["@modelcontextprotocol/server-github"]`

**检查点**：
- [ ] YAML语法正确，缩进规范
- [ ] 三个服务器配置完整，包含所有必需字段
- [ ] 环境变量引用格式正确
- [ ] 端口配置无冲突
- [ ] 全局配置合理

### 任务2：MCP服务器管理器实现（30分钟）

**目标**：实现一个MCP服务器管理器，能够异步启动和管理MCP服务器。

**要求**：
1. 创建`mcp_server_manager.py`文件，实现以下类：
   - `MCPServer`：单个MCP服务器管理类
   - `MCPServerManager`：MCP服务器管理器类
   - `ServerStatus`：服务器状态枚举类

2. `MCPServer`类需要实现的功能：
   ```python
   class MCPServer:
       async def start(self) -> bool:
           """启动MCP服务器"""
           # 实现：构建命令行 → 启动异步子进程 → 收集输出 → 等待就绪
           pass
       
       async def stop(self, timeout: float = 5.0) -> bool:
           """停止MCP服务器"""
           # 实现：发送停止信号 → 等待退出 → 超时强制终止
           pass
       
       async def health_check(self) -> bool:
           """健康检查"""
           # 实现：检查健康检查端点或进程状态
           pass
       
       async def wait_for_ready(self, timeout: float = 30.0) -> bool:
           """等待服务器就绪"""
           # 实现：定期健康检查，直到成功或超时
           pass
   ```

3. `MCPServerManager`类需要实现的功能：
   ```python
   class MCPServerManager:
       async def start_all(self) -> Dict[str, bool]:
           """启动所有auto_start为true的服务器"""
           # 实现：并行启动符合条件的服务器
           pass
       
       async def stop_all(self) -> Dict[str, bool]:
           """停止所有正在运行的服务器"""
           pass
       
       async def start_server(self, server_name: str) -> bool:
           """启动单个服务器"""
           pass
       
       async def stop_server(self, server_name: str) -> bool:
           """停止单个服务器"""
           pass
       
       async def health_check_all(self) -> Dict[str, bool]:
           """检查所有服务器的健康状态"""
           pass
       
       def list_servers(self) -> List[Dict[str, Any]]:
           """列出所有服务器状态信息"""
           pass
   ```

**提示**：
- 使用`asyncio.create_subprocess_exec`创建异步子进程
- 进程环境变量需要合并系统环境变量和配置环境变量
- 收集标准输出和错误输出，用于调试和日志
- 服务器状态需要实时更新：STOPPED、STARTING、RUNNING、ERROR、STOPPING

**检查点**：
- [ ] MCPServer类完整实现所有方法
- [ ] MCPServerManager类完整实现所有方法
- [ ] 异步子进程管理正确
- [ ] 状态管理准确反映服务器实际状态
- [ ] 健康检查机制有效

### 任务3：服务器生命周期管理（20分钟）

**目标**：实现服务器生命周期管理，包括启动、停止、重启和状态监控。

**要求**：
1. 创建`server_lifecycle.py`文件，实现以下功能：
   - **启动顺序控制**：支持依赖关系，确保依赖服务器先启动
   - **并发启动优化**：无依赖关系的服务器并行启动
   - **状态持久化**：保存服务器状态，支持重启后恢复
   - **生命周期钩子**：支持启动前、启动后、停止前、停止后的回调

2. 实现以下生命周期管理方法：
   ```python
   async def start_with_dependencies(self, server_name: str) -> bool:
       """启动服务器及其依赖"""
       # 实现：递归启动依赖服务器
       pass
   
   async def graceful_shutdown(self, timeout: float = 30.0) -> bool:
       """优雅关闭所有服务器"""
       # 实现：按依赖逆序停止服务器
       pass
   
   async def restart_server(self, server_name: str) -> bool:
       """重启单个服务器"""
       # 实现：停止 → 等待 → 启动
       pass
   
   async def monitor_servers(self):
       """监控服务器状态，自动恢复失败的服务器"""
       # 实现：定期健康检查，自动重启失败的服务器
       pass
   ```

3. 实现依赖关系解析：
   ```python
   def resolve_dependencies(self, server_name: str) -> List[str]:
       """解析服务器的依赖关系"""
       # 实现：从配置中读取依赖关系，返回启动顺序列表
       pass
   ```

**提示**：
- 依赖关系可以在YAML配置中定义，例如：
  ```yaml
  github:
    # ...其他配置...
    depends_on: ["filesystem", "sql"]
  ```
- 使用拓扑排序算法解决依赖关系
- 监控循环需要处理异常，避免崩溃

**检查点**：
- [ ] 依赖关系解析和启动顺序控制正确
- [ ] 并发启动优化提高启动速度
- [ ] 生命周期钩子机制灵活可扩展
- [ ] 优雅关闭机制正确处理依赖关系
- [ ] 监控循环稳定，自动恢复机制有效

### 任务4：错误处理和重试机制（20分钟）

**目标**：实现健壮的错误处理和重试机制，提高MCP服务器的可靠性。

**要求**：
1. 创建`error_handler.py`文件，实现以下错误处理机制：
   - **启动失败重试**：带指数退避的启动重试机制
   - **健康检查失败处理**：健康检查失败时的自动恢复
   - **进程异常监控**：监控子进程异常退出并自动重启
   - **资源泄漏防护**：确保异常情况下资源正确释放

2. 实现带指数退避的重试机制：
   ```python
   async def start_with_retry(self, server_name: str, max_retries: int = 3) -> bool:
       """带重试的服务器启动"""
       for attempt in range(max_retries):
           try:
               success = await self.start_server(server_name)
               if success:
                   return True
               
               # 指数退避延迟
               delay = self.config.retry_delay * (2 ** attempt)
               await asyncio.sleep(delay)
               
           except Exception as e:
               logging.error(f"启动尝试 {attempt + 1} 失败: {e}")
       
       return False
   ```

3. 实现健康检查失败的自愈机制：
   ```python
   async def auto_heal_server(self, server_name: str) -> bool:
       """自动恢复失败的服务器"""
       # 实现：检查健康状态 → 如果失败 → 停止 → 等待 → 重启
       pass
   ```

4. 实现进程异常监控：
   ```python
   async def monitor_processes(self):
       """监控所有服务器进程状态"""
       # 实现：定期检查进程状态，处理异常退出
       pass
   ```

**提示**：
- 指数退避公式：`delay = base_delay * (2 ** attempt)`
- 健康检查失败可能是暂时的，需要重试几次再重启
- 进程异常退出需要记录退出码和错误输出

**检查点**：
- [ ] 启动失败重试机制正确实现指数退避
- [ ] 健康检查失败的自愈机制有效
- [ ] 进程异常监控能够检测和处理异常退出
- [ ] 资源泄漏防护确保异常情况下正确释放资源
- [ ] 错误日志记录完整，便于调试

### 任务5：环境变量注入和配置解析（15分钟）

**目标**：实现环境变量在MCP配置中的动态注入和解析。

**要求**：
1. 创建`environment_variables.py`文件，实现以下功能：
   - **环境变量解析**：解析`${VAR_NAME}`和`${VAR_NAME:default}`格式
   - **配置模板渲染**：将环境变量注入到配置模板中
   - **环境验证**：验证必需环境变量是否设置
   - **配置加密**：支持敏感配置的加密和解密（模拟）

2. 实现环境变量解析器：
   ```python
   class EnvironmentVariableResolver:
       def resolve(self, text: str, env_vars: Dict[str, str]) -> str:
           """解析文本中的环境变量引用"""
           # 实现：替换${VAR_NAME}和${VAR_NAME:default}格式
           pass
       
       def resolve_config(self, config: Dict, env_vars: Dict[str, str]) -> Dict:
           """递归解析配置中的所有环境变量"""
           pass
       
       def validate_required_vars(self, config: Dict) -> List[str]:
           """验证必需环境变量是否已设置"""
           # 返回缺失的环境变量名称列表
           pass
   ```

3. 实现配置模板渲染：
   ```python
   class ConfigTemplateRenderer:
       def render(self, template_path: str, output_path: str, env_vars: Dict[str, str]):
           """渲染配置模板"""
           # 实现：读取模板 → 替换环境变量 → 写入输出文件
           pass
   ```

4. 实现简单的配置加密（模拟）：
   ```python
   class ConfigEncryptor:
       def encrypt_sensitive_values(self, config: Dict, sensitive_keys: List[str]) -> Dict:
           """加密敏感配置值"""
           # 模拟实现：将敏感值标记为已加密
           pass
       
       def decrypt_sensitive_values(self, config: Dict) -> Dict:
           """解密敏感配置值"""
           pass
   ```

**提示**：
- 使用正则表达式匹配环境变量引用：`r'\$\{([^}:]+)(?::([^}]+))?\}'`
- 递归处理嵌套的字典和列表
- 缺失必需环境变量时提供清晰的错误信息

**检查点**：
- [ ] 环境变量解析器正确解析两种格式
- [ ] 配置模板渲染功能完整
- [ ] 必需环境变量验证准确
- [ ] 配置加密解密机制（模拟）可用
- [ ] 错误处理友好，提供明确的错误信息

### 任务6：GitHub MCP服务器配置实战（10分钟）

**目标**：完成GitHub MCP服务器的完整配置和测试。

**要求**：
1. 创建`github_mcp_server.py`文件，实现以下功能：
   - **GitHub令牌管理**：安全获取和使用GitHub令牌
   - **服务器配置生成**：根据环境生成GitHub MCP服务器配置
   - **连接测试**：测试GitHub MCP服务器连接和功能
   - **权限验证**：验证GitHub令牌的权限范围

2. 实现GitHub令牌管理器：
   ```python
   class GitHubTokenManager:
       def get_token(self) -> str:
           """获取GitHub令牌"""
           # 实现：从环境变量、文件或密钥管理服务获取
           pass
       
       def validate_token(self, token: str) -> bool:
           """验证GitHub令牌有效性"""
           # 实现：调用GitHub API验证令牌
           pass
       
       def get_token_scopes(self, token: str) -> List[str]:
           """获取令牌权限范围"""
           pass
   ```

3. 实现GitHub MCP服务器配置器：
   ```python
   class GitHubMCPServerConfigurator:
       def create_config(self) -> Dict:
           """创建GitHub MCP服务器配置"""
           # 实现：生成完整的YAML配置
           pass
       
       async def test_connection(self) -> bool:
           """测试GitHub MCP服务器连接"""
           # 实现：启动服务器并测试基本功能
           pass
       
       def check_permissions(self) -> Dict[str, bool]:
           """检查GitHub令牌权限"""
           pass
   ```

4. 编写完整的配置示例：
   ```yaml
   github:
     command: "npx"
     args: ["@modelcontextprotocol/server-github"]
     env:
       MCP_PORT: 3003
       GITHUB_TOKEN: "${GITHUB_TOKEN}"
       GITHUB_API_URL: "https://api.github.com"
       LOG_LEVEL: "info"
     auto_start: false
     health_check: "http://localhost:3003/health"
     timeout: 60.0
     description: "GitHub MCP服务器，提供GitHub API访问功能"
     depends_on: ["filesystem"]  # 可选依赖
   ```

**提示**：
- GitHub令牌可以从环境变量`GITHUB_TOKEN`获取
- 使用GitHub REST API验证令牌：`GET https://api.github.com/user`
- 测试连接可以尝试调用简单的GitHub API

**检查点**：
- [ ] GitHub令牌管理安全可靠
- [ ] 服务器配置生成完整正确
- [ ] 连接测试功能有效
- [ ] 权限验证准确
- [ ] 配置示例符合最佳实践

## 🧪 测试要求

### 基础测试（必须完成）
1. **配置加载测试**：测试YAML配置正确加载和解析
2. **服务器启动测试**：测试filesystem服务器成功启动
3. **健康检查测试**：测试健康检查机制正常工作
4. **环境变量测试**：测试环境变量正确注入

### 进阶测试（推荐完成）
1. **错误处理测试**：测试启动失败重试机制
2. **依赖关系测试**：测试服务器依赖关系正确处理
3. **并发启动测试**：测试多个服务器并行启动
4. **监控恢复测试**：测试自动监控和恢复机制

### 挑战测试（可选）
1. **性能测试**：测试服务器启动时间和资源使用
2. **压力测试**：测试多服务器并发管理能力
3. **故障注入测试**：测试各种故障场景下的系统行为
4. **安全测试**：测试配置安全性（敏感信息保护）

## 📊 评估标准

### 优秀（90-100分）
- 所有任务完整实现，代码质量高
- 异步编程正确，无资源泄漏
- 错误处理健壮，覆盖各种异常场景
- 代码注释完整，文档清晰
- 测试覆盖全面，通过所有测试用例

### 良好（80-89分）
- 所有任务基本完成，代码质量良好
- 主要功能正确实现
- 错误处理基本覆盖
- 代码有基本注释
- 通过基础测试和部分进阶测试

### 合格（60-79分）
- 完成主要任务，代码质量一般
- 核心功能实现，但存在一些缺陷
- 错误处理基本覆盖
- 通过基础测试

### 需改进（<60分）
- 任务完成度不足
- 核心功能存在严重缺陷
- 错误处理不完善
- 未通过基础测试

## 🔍 调试技巧

### 常见问题及解决方案
1. **端口冲突**：
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :3001
   # 或使用lsof
   lsof -i :3001
   ```

2. **启动失败**：
   - 检查命令路径是否正确
   - 检查环境变量是否设置
   - 查看子进程错误输出
   - 检查权限问题

3. **健康检查失败**：
   - 确认服务器是否真的启动成功
   - 检查健康检查URL是否正确
   - 增加启动超时时间
   - 查看服务器日志

4. **环境变量未解析**：
   - 检查环境变量名称是否正确
   - 检查解析器正则表达式
   - 验证环境变量值是否包含特殊字符

### 调试工具
1. **日志记录**：使用Python logging模块记录详细日志
2. **进程监控**：使用`ps aux | grep mcp`查看进程状态
3. **网络调试**：使用`curl http://localhost:3001/health`测试健康检查
4. **性能分析**：使用`time`命令测量启动时间

## 📚 扩展学习

### 进一步探索
1. **Docker容器化**：将MCP服务器容器化，使用Docker运行
2. **Kubernetes部署**：在K8s中部署和管理MCP服务器集群
3. **Prometheus监控**：集成Prometheus监控MCP服务器指标
4. **自动化测试**：编写完整的自动化测试套件
5. **配置管理工具**：集成Ansible、Terraform等配置管理工具

### 推荐阅读
1. **MCP官方文档**：https://spec.modelcontextprotocol.io/
2. **Python asyncio文档**：https://docs.python.org/3/library/asyncio.html
3. **YAML规范**：https://yaml.org/spec/
4. **进程管理最佳实践**：Unix进程管理相关书籍

## 🎓 学习反思

完成本练习后，请思考以下问题：
1. MCP服务器配置中最容易出错的部分是什么？如何避免？
2. 异步服务器管理相比同步管理有哪些优势和挑战？
3. 环境变量注入机制如何平衡灵活性和安全性？
4. 健康检查机制的设计如何影响系统的可靠性？
5. 在实际生产环境中，MCP服务器配置还需要考虑哪些因素？

## 📝 提交要求

1. **代码提交**：将所有练习文件打包为zip文件提交
2. **配置示例**：提供完整的`mcp_config.yaml`配置示例
3. **测试报告**：提供测试运行结果截图或日志
4. **问题记录**：记录练习过程中遇到的问题和解决方案
5. **改进建议**：对练习内容或课程的建议

## 🏆 完成标志

成功完成本练习的标志：
- ✅ 能够独立配置和管理3种不同类型的MCP服务器
- ✅ 实现完整的服务器生命周期管理和错误处理
- ✅ 掌握环境变量注入和配置解析机制
- ✅ 能够调试和解决常见的MCP服务器问题
- ✅ 理解MCP服务器配置的最佳实践

**恭喜！** 完成本练习后，你已经掌握了MCP服务器配置的核心技能，可以应用到实际的AI Agent项目中。

---

**下一节课预告**：第63节课《多代理协作配置》将深入讲解AI Agent系统中多代理协作的配置管理，提高系统的协作能力和任务分配效率。