# 🎓 Day 6 第23节课：TodoMiddleware（任务管理中间件）- 课后练习

## 📋 练习说明

**目标**: 通过本练习，深入理解复杂任务管理在AI Agent系统中的重要性和挑战，掌握任务分解的四种核心需求：分解、跟踪、持久化、优先级，理解TodoItem数据结构和依赖关系管理机制，了解任务进度计算和状态同步原理，能够设计合理的TodoItem数据结构（dataclass），实现任务依赖检查和阻塞状态判断，编写TodoMiddleware的before/after/during方法，计算和生成任务进度报告，并掌握依赖图（DAG）管理和拓扑排序算法。

**建议时间**: 120-150分钟  
**难度**: 中等偏高  
**提交方式**: 完成所有设计文档和代码实现，提交到GitHub仓库

---

## 🧠 第一部分：概念理解与选择

### 1.1 多项选择题

**1. TodoMiddleware的主要作用是什么？**
A) 仅跟踪任务创建时间  
B) 仅记录任务执行结果  
C) 在Agent执行流程中插入任务管理功能，支持任务加载/初始化、依赖检查、状态跟踪、进度计算、结果保存  
D) 仅验证任务输入格式  
E) 仅监控任务执行时间

**2. 任务管理的四种核心需求不包括以下哪项？**
A) 任务分解  
B) 任务跟踪  
C) 任务持久化  
D) 任务可视化  
E) 任务优先级

**3. TaskStatus枚举中，哪个状态表示任务准备就绪（依赖已满足）？**
A) PENDING  
B) READY  
C) RUNNING  
D) COMPLETED  
E) BLOCKED

**4. TodoItem的is_blocked方法返回True表示什么？**
A) 任务已完成  
B) 任务执行失败  
C) 任务被阻塞（依赖任务未完成）  
D) 任务被取消  
E) 任务不存在

**5. 在依赖图（DependencyGraph）中，has_cycle方法使用什么算法检测循环依赖？**
A) 广度优先搜索（BFS）  
B) 深度优先搜索（DFS）  
C) 迪杰斯特拉算法（Dijkstra）  
D) 克鲁斯卡尔算法（Kruskal）  
E) 弗洛伊德算法（Floyd-Warshall）

**6. 拓扑排序（topological_sort）使用什么算法实现？**
A) DFS后序遍历  
B) BFS层次遍历  
C) Kahn算法（基于入度的BFS）  
D) 快速排序  
E) 归并排序

**7. TodoProgressCalculator计算总体进度时，已完成任务的权重是多少？**
A) 0.0  
B) 0.5  
C) 1.0  
D) 1.5  
E) 2.0

**8. TodoMiddleware的during_agent方法主要目的是什么？**
A) 在Agent执行前加载任务和检查依赖  
B) 在Agent执行后保存结果和更新状态  
C) 在Agent执行期间检查超时和更新进度  
D) 在Agent出错时记录错误信息  
E) 在任务完成时触发依赖任务检查

**9. TaskBlocked异常包含什么信息？**
A) 仅错误消息  
B) 错误消息和任务ID  
C) 错误消息、任务ID和阻塞依赖列表  
D) 仅任务ID  
E) 仅阻塞依赖列表

**10. 在TodoItem的calculate_progress方法中，总体进度计算采用什么权重分配？**
A) 依赖进度权重：0.6，自身进度权重：0.4  
B) 依赖进度权重：0.5，自身进度权重：0.5  
C) 依赖进度权重：0.4，自身进度权重：0.6  
D) 仅考虑自身进度  
E) 仅考虑依赖进度

**11. TodoStorage存储抽象层采用什么设计模式？**
A) 单例模式  
B) 工厂模式  
C) 策略模式  
D) 观察者模式  
E) 装饰器模式

**12. 关键路径（critical_path）计算基于什么？**
A) 任务依赖关系和预估时长  
B) 任务实际执行时间  
C) 任务优先级  
D) 任务创建时间  
E) 任务标签

---

### 1.2 判断题

**1. TodoItem使用Python dataclass可以自动生成__init__、__repr__等方法，简化代码编写。**  
( ) 正确  ( ) 错误

**2. 任务状态流转中，COMPLETED状态可以转换回RUNNING状态。**  
( ) 正确  ( ) 错误

**3. 循环依赖检测中，深度优先搜索（DFS）可以检测有向图中的所有环。**  
( ) 正确  ( ) 错误

**4. 拓扑排序只能应用于有向无环图（DAG）。**  
( ) 正确  ( ) 错误

**5. TodoMiddleware的before_agent方法会创建新任务，如果输入中没有task_id。**  
( ) 正确  ( ) 错误

**6. 任务进度计算中，BLOCKED状态的任务进度为0。**  
( ) 正确  ( ) 错误

**7. InMemoryTodoStorage是线程安全的，支持多线程并发访问。**  
( ) 正确  ( ) 错误

**8. 依赖图的分层执行顺序（get_execution_order）中，同一层的任务可以并行执行。**  
( ) 正确  ( ) 错误

**9. TodoMiddleware的on_error方法会将任务状态更新为FAILED并记录错误信息。**  
( ) 正确  ( ) 错误

**10. 关键路径是项目中最长的任务链，决定了项目的最短可能完成时间。**  
( ) 正确  ( ) 错误

---

### 1.3 填空题

**1. TodoItem的状态机中，从PENDING状态可以转换到______、______、______状态。**

**2. 依赖图检测循环依赖时，使用______集合记录递归栈中的节点，检测到节点已在递归栈中表示______。**

**3. 拓扑排序的Kahn算法中，首先找到所有______为0的节点，加入队列。**

**4. TodoProgressCalculator计算总体进度时，RUNNING状态的任务权重为______，COMPLETED状态的任务权重为______。**

**5. TodoMiddleware的三个核心异步方法是______、______、______。**

**6. 任务依赖关系中，如果任务A依赖任务B，那么B是A的______，A是B的______。**

**7. 在进度计算中，总体进度 = (依赖进度 × ______) + (自身进度 × ______)。**

**8. TaskBlockedError异常继承自______类，包含task_id和______属性。**

**9. 关键路径计算中，假设任务A（预估2小时）→ 任务B（预估3小时）→ 任务C（预估1小时），那么关键路径长度为______小时。**

**10. TodoStorage接口定义了五个抽象方法：______、______、______、______、______。**

---

## 💻 第二部分：代码分析与设计

### 2.1 代码阅读题

阅读以下TodoItem.is_blocked方法的代码片段，回答相关问题：

```python
def is_blocked(self, todos: Dict[str, "TodoItem"]) -> bool:
    if not self.dependencies:
        return False
    
    visited = set()
    
    def check_dependency(dep_id: str) -> bool:
        if dep_id in visited:
            return False
        visited.add(dep_id)
        
        dep = todos.get(dep_id)
        if dep is None:
            return True
        
        if dep.status != TaskStatus.COMPLETED:
            return True
        
        for sub_dep_id in dep.dependencies:
            if check_dependency(sub_dep_id):
                return True
        
        return False
    
    for dep_id in self.dependencies:
        if check_dependency(dep_id):
            return True
    
    return False
```

**问题：**
1. 这段代码的时间复杂度是多少？为什么？
2. visited集合的作用是什么？如果不使用visited集合会有什么问题？
3. 当dep为None时，为什么返回True？这代表什么设计决策？
4. 这段代码如何处理间接依赖（依赖的依赖）？
5. 这段代码能否检测循环依赖？如果能，是如何处理的？如果不能，为什么？

### 2.2 设计题

**任务1：设计扩展的TodoItem数据结构**

当前TodoItem支持基本任务管理功能，但实际项目中可能需要更多功能。请设计一个扩展的TodoItemEx类，满足以下需求：

1. **子任务支持**: 任务可以包含子任务，形成任务树结构
2. **时间估算优化**: 支持乐观时间、悲观时间、最可能时间（PERT估算）
3. **资源需求**: 任务需要的资源类型和数量（CPU、内存、存储等）
4. **里程碑标记**: 标记关键里程碑任务
5. **版本控制**: 任务版本号和修改历史

请提供：
- 类定义（使用dataclass）
- 关键方法签名和简要说明
- 与原始TodoItem的兼容性考虑

**任务2：设计分布式任务存储**

当前InMemoryTodoStorage仅支持单机内存存储。请设计一个分布式任务存储系统，满足以下需求：

1. **多节点支持**: 支持多个Agent节点共享任务状态
2. **数据一致性**: 保证任务状态在多个节点间的一致性
3. **容错性**: 单个节点故障不影响整体系统
4. **性能要求**: 支持高并发读写操作
5. **扩展性**: 易于添加新存储节点

请提供：
- 系统架构图
- 关键组件设计（协调器、存储节点、缓存等）
- 数据同步策略
- 一致性保证机制

---

## 🔧 第三部分：编程实现

### 3.1 基础实现题

**任务1：实现TodoItem的增强方法**

基于课堂演示代码中的TodoItem类，实现以下增强方法：

```python
def get_dependency_chain(self, todos: Dict[str, "TodoItem"]) -> List[List[str]]:
    """
    获取任务的完整依赖链
    
    返回一个列表的列表，每个子列表表示一条从当前任务回溯到无依赖任务的依赖链。
    例如：如果任务C依赖B，B依赖A，那么返回 [["C", "B", "A"]]
    如果任务C同时依赖B1和B2，B1依赖A1，B2依赖A2，那么返回 [["C", "B1", "A1"], ["C", "B2", "A2"]]
    
    要求：
    1. 正确处理多个依赖分支
    2. 检测循环依赖并避免无限递归
    3. 按依赖顺序排序（从当前任务到最底层依赖）
    """
    pass

def estimate_completion_time(self, todos: Dict[str, "TodoItem"]) -> float:
    """
    估算任务完成时间
    
    基于任务的依赖关系和预估时长，估算任务的最早可能完成时间。
    假设：
    1. 依赖任务可以并行执行（如果它们之间没有依赖关系）
    2. 任务本身的预估时长是准确的
    3. 所有依赖任务都从当前时间开始执行
    
    返回从当前时间开始，预计需要多少秒才能完成此任务。
    """
    pass
```

**任务2：实现优先级调度器**

基于DependencyGraph类，实现一个优先级调度器，支持以下功能：

```python
class PriorityScheduler:
    """
    优先级调度器
    
    在考虑依赖关系的基础上，根据任务优先级进行调度。
    高优先级任务应优先执行，但必须满足依赖关系。
    """
    
    def __init__(self, graph: DependencyGraph):
        self.graph = graph
    
    def get_schedule(self) -> List[List[str]]:
        """
        获取调度顺序
        
        返回任务的分层执行顺序，但在每一层内：
        1. 先调度高优先级任务
        2. 同优先级任务按拓扑顺序排列
        3. 必须满足依赖关系
        
        返回格式与get_execution_order相同，但每层内的任务按优先级排序。
        """
        pass
    
    def get_critical_path_with_priority(self) -> List[str]:
        """
        获取考虑优先级的关键路径
        
        在计算关键路径时，考虑任务优先级：
        1. 高优先级任务在关键路径中权重更高
        2. 如果两条路径长度相近，高优先级任务的路径更可能成为关键路径
        
        返回考虑优先级的关键路径任务ID列表。
        """
        pass
```

### 3.2 中级实现题

**任务3：实现TodoMiddleware的扩展功能**

扩展TodoMiddleware类，支持以下新功能：

1. **任务超时自动重试**: 当任务执行超时时，自动重试（最多重试N次）
2. **任务依赖动态调整**: 支持运行时动态添加/移除任务依赖
3. **任务进度自动保存**: 定期自动保存任务进度到持久化存储
4. **任务执行历史**: 记录任务每次执行的历史（开始时间、结束时间、结果、错误等）
5. **任务告警机制**: 当任务长时间阻塞或多次失败时，发送告警

请实现：
- 扩展的TodoMiddlewareEx类定义
- 上述功能的完整实现
- 相应的测试用例

**任务4：实现可视化进度报告**

基于TodoProgressCalculator，实现可视化进度报告生成：

```python
class VisualProgressReporter:
    """
    可视化进度报告生成器
    
    生成人类可读、可视化的进度报告，包括：
    1. ASCII进度条
    2. 依赖关系图（ASCII艺术）
    3. 关键路径高亮显示
    4. 统计图表（文本形式）
    """
    
    def __init__(self, calculator: TodoProgressCalculator):
        self.calculator = calculator
    
    def generate_ascii_progress_bar(self, width: int = 50) -> str:
        """
        生成ASCII进度条
        
        例如：[██████████          ] 40%
        """
        pass
    
    def generate_dependency_ascii_art(self) -> str:
        """
        生成依赖关系ASCII图
        
        例如：
        Task1 → Task2 → Task4
                 ↘ Task3 ↗
        """
        pass
    
    def generate_summary_report(self) -> str:
        """
        生成完整的文本报告
        
        包括：
        1. 进度条
        2. 关键统计数字
        3. 依赖关系图
        4. 关键路径
        5. 建议和警告
        """
        pass
```

### 3.3 高级挑战题

**任务5：实现智能任务调度算法**

基于机器学习或启发式算法，实现智能任务调度：

1. **历史学习**: 基于历史执行数据，学习任务实际执行时间的分布
2. **资源感知调度**: 考虑系统资源约束（CPU、内存、IO）进行调度
3. **截止时间感知**: 考虑任务截止时间，优先调度紧急任务
4. **负载均衡**: 在多Agent系统中平衡各Agent的负载
5. **动态调整**: 根据系统负载动态调整调度策略

请设计并实现：
- 智能调度器的算法设计文档
- 核心调度算法的实现
- 性能评估方法和基准测试

**任务6：实现分布式任务协调系统**

设计并实现一个简单的分布式任务协调系统：

1. **分布式锁**: 协调多个节点对共享任务的访问
2. **领导者选举**: 选举主节点负责任务调度
3. **任务分发**: 将任务分发给合适的Agent节点执行
4. **结果收集**: 收集各节点的任务执行结果
5. **故障转移**: 主节点故障时自动切换

请实现：
- 系统架构和协议设计
- 核心组件的实现
- 一致性保证机制
- 容错和恢复策略

---

## 📊 第四部分：案例分析

### 4.1 实际场景分析

**案例：智能数据分析流水线**

某公司需要构建一个智能数据分析流水线，处理以下任务：
1. 数据收集（从多个源收集数据）
2. 数据清洗（处理缺失值、异常值）
3. 特征工程（提取、转换特征）
4. 模型训练（训练机器学习模型）
5. 模型评估（评估模型性能）
6. 结果可视化（生成报告和图表）

**依赖关系**:
- 数据清洗依赖数据收集完成
- 特征工程依赖数据清洗完成  
- 模型训练依赖特征工程完成
- 模型评估依赖模型训练完成
- 结果可视化依赖模型评估完成

**额外需求**:
- 每个任务可以并行处理多个数据集
- 某些任务需要特殊资源（GPU、大内存）
- 任务执行时间不确定，需要动态调整
- 需要实时监控流水线进度

**问题**:
1. 如何设计TodoItem来表示这些任务？需要哪些额外字段？
2. 如何构建依赖图来表示这个流水线？
3. 如何计算整个流水线的预计完成时间？
4. 如果某个任务失败，如何设计重试和恢复策略？
5. 如何扩展系统支持并行处理多个数据集？

### 4.2 系统设计题

**设计一个企业级任务管理系统**

要求支持以下功能：
1. **多项目管理**: 同时管理多个项目的任务
2. **团队协作**: 支持多用户、多角色（管理员、开发者、测试员等）
3. **资源管理**: 管理计算资源、人力资源
4. **时间跟踪**: 记录任务实际耗时，支持工时统计
5. **报告生成**: 生成项目进度、资源使用、团队绩效等报告
6. **集成能力**: 与Git、JIRA、Slack等工具集成
7. **权限控制**: 细粒度的任务访问和操作权限
8. **审计日志**: 记录所有任务操作的历史

**设计任务**:
1. 系统架构设计（微服务、单体、混合？）
2. 数据库设计（关系型、文档型、图数据库？）
3. API设计（REST、GraphQL、gRPC？）
4. 前端设计（Web、桌面、移动？）
5. 部署架构（云原生、容器化、Serverless？）
6. 安全考虑（认证、授权、加密等）

请提供完整的设计文档，包括：
- 架构图和技术选型理由
- 核心数据模型设计
- 关键API接口定义
- 部署和运维方案
- 性能和安全考虑

---

## 🔍 第五部分：调试与优化

### 5.1 代码调试题

以下代码片段来自一个TodoMiddleware的实现，但存在多个bug。请找出并修复这些bug：

```python
async def before_agent(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    task_id = agent_input.get("task_id")
    if not task_id:
        task_id = self._create_new_task(agent_input)
    
    todo = self.storage.load_todo(task_id)
    if not todo:
        todo = self._create_todo_from_input(agent_input)
        self.storage.save_todo(todo)
    
    # 检查依赖
    todos = self._load_all_todos()
    if todo.is_blocked(todos):
        todo.status = TaskStatus.BLOCKED
        self.storage.update_todo(todo)
        raise Exception(f"Task {todo.id} is blocked")
    
    # 更新状态
    todo.status = TaskStatus.RUNNING
    self.storage.update_todo(todo)
    
    self.current_task_id = todo.id
    self.task_start_time = datetime.now()
    
    return agent_input

async def after_agent(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
    if not self.current_task_id:
        return agent_output
    
    todo = self.storage.load_todo(self.current_task_id)
    if not todo:
        return agent_output
    
    if agent_output.get("success"):
        todo.status = TaskStatus.COMPLETED
    else:
        todo.status = TaskStatus.FAILED
    
    self.storage.update_todo(todo)
    
    self.current_task_id = None
    self.task_start_time = None
    
    return agent_output
```

**问题**:
1. 找出代码中的至少5个bug或设计问题
2. 解释每个问题的原因和影响
3. 提供修复后的代码

### 5.2 性能优化题

以下是一个依赖图算法的实现，但存在性能问题：

```python
class DependencyGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
    
    def has_cycle(self) -> bool:
        for node_id in self.nodes:
            if self._dfs(node_id, set()):
                return True
        return False
    
    def _dfs(self, node_id: str, visited: set) -> bool:
        if node_id in visited:
            return True
        
        visited.add(node_id)
        
        for neighbor_id in self.edges.get(node_id, []):
            if self._dfs(neighbor_id, visited.copy()):
                return True
        
        return False
    
    def topological_sort(self) -> List[str]:
        result = []
        visited = set()
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            for neighbor_id in self.edges.get(node_id, []):
                visit(neighbor_id)
            
            result.append(node_id)
        
        for node_id in self.nodes:
            visit(node_id)
        
        return list(reversed(result))
```

**优化任务**:
1. 分析算法的时间复杂度和空间复杂度
2. 指出性能瓶颈和潜在问题
3. 提供优化后的实现
4. 设计性能测试用例验证优化效果

---

## 📝 第六部分：综合项目

### 6.1 项目任务：实现完整的智能任务管理系统

**项目要求**:
基于TodoMiddleware和课堂所学知识，实现一个完整的智能任务管理系统，包含以下模块：

1. **任务管理核心**: 完整的TodoItem、DependencyGraph、TodoProgressCalculator实现
2. **存储系统**: 支持内存、文件、数据库（SQLite/PostgreSQL）多种存储后端
3. **中间件集成**: 与AI Agent系统无缝集成，支持异步执行
4. **调度器**: 实现智能调度算法，支持优先级、资源约束、截止时间
5. **监控系统**: 实时监控任务执行状态，生成可视化报告
6. **API服务**: 提供RESTful API供其他系统调用
7. **命令行工具**: 提供命令行界面进行任务管理
8. **测试套件**: 完整的单元测试、集成测试、性能测试

**交付物**:
1. 完整的源代码（Python项目）
2. 设计文档（架构设计、API文档、用户手册）
3. 测试报告（功能测试、性能测试结果）
4. 部署指南（本地部署、云部署）
5. 演示视频（5分钟系统演示）

**评估标准**:
1. **功能完整性**: 是否实现所有要求功能（40%）
2. **代码质量**: 代码结构、注释、测试覆盖率（25%）
3. **设计合理性**: 架构设计、扩展性、性能考虑（20%）
4. **文档完整性**: 设计文档、API文档、用户手册（10%）
5. **创新性**: 是否有创新功能或优化（5%）

### 6.2 扩展挑战：集成AI能力

在基础系统上，集成AI能力实现以下功能：

1. **智能任务分解**: 使用LLM将复杂任务自动分解为子任务
2. **时间预测**: 基于历史数据使用机器学习预测任务执行时间
3. **智能调度**: 使用强化学习优化任务调度顺序
4. **异常检测**: 使用异常检测算法识别异常任务执行模式
5. **自动优化**: 基于执行结果自动优化任务参数和依赖关系

**挑战要求**:
1. 设计AI集成架构
2. 实现至少2项AI功能
3. 评估AI功能的效果和性能
4. 提供AI模型训练和部署方案

---

## 🎯 练习提交指南

### 提交要求
1. **代码部分**: 所有实现代码打包为ZIP文件，或提供GitHub仓库链接
2. **文档部分**: 设计文档、分析报告等提交为PDF格式
3. **演示部分**: 演示视频上传到视频平台，提供链接

### 评分标准
- **选择题/判断题/填空题**: 每题1分，共32分
- **代码分析题**: 每题5分，共10分  
- **设计题**: 每题10分，共20分
- **编程实现题**: 每题15分，共60分（基础20+中级20+高级20）
- **案例分析题**: 每题10分，共20分
- **调试优化题**: 每题10分，共20分
- **综合项目**: 100分（按评估标准分配）
- **扩展挑战**: 额外30分

**总分**: 262分 + 30分（挑战）

### 时间安排建议
- 第一部分（概念）: 30分钟
- 第二部分（分析设计）: 40分钟  
- 第三部分（编程实现）: 60-90分钟
- 第四部分（案例分析）: 30分钟
- 第五部分（调试优化）: 30分钟
- 第六部分（综合项目）: 课外完成（建议5-10小时）

---

**最后提醒**: 本练习旨在巩固Day 6第23节课所学知识，培养实际工程能力。请独立完成，遇到困难时可参考课堂演示代码，但鼓励创新和扩展。完成后请及时提交，教师将在一周内反馈评分和建议。

**祝您学习愉快，编码顺利！** 🚀