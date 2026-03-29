# Day 17 - 第68节课：多模型路由

## 📋 课程概述

本节课深入讲解AI Agent系统中多模型路由的设计和实现。通过智能的模型选择策略，我们能够根据任务特征、成本预算和性能要求动态选择最合适的AI模型，优化系统效率和成本效益。

## 🎯 学习目标

### 知识目标
1. 理解多模型路由的核心概念和应用价值
2. 掌握基于任务特征的模型选择决策逻辑
3. 理解不同路由策略（成本优化、性能优化、平衡）的设计原理
4. 了解模型路由中的评分系统和权重分配方法

### 技能目标
1. 能够实现ModelRouter类进行智能模型选择
2. 能够设计和实现多种路由策略
3. 能够根据多维度特征计算模型适配度得分
4. 能够实现自适应路由和策略选择

## 📁 文件结构

```
day17-lesson68/
├── multi_model_routing_demo.py   # 主演示代码文件
├── README.md                     # 本文件
└── (后续可能添加的练习文件)
```

## 🔧 主要组件

### 1. ModelCapabilities（模型能力定义）
- **功能**: 定义模型支持的各种能力（视觉、函数调用、长上下文等）
- **核心特性**: 能力检查、验证、序列化
- **关键方法**: has_capability()

### 2. ModelConfig（模型配置）
- **功能**: 存储模型配置信息（提供者、成本、参数等）
- **核心字段**: provider, model_name, capabilities, cost_per_token, config
- **关键方法**: __post_init__() 验证

### 3. RoutingDecision（路由决策结果）
- **功能**: 封装路由决策的结果信息
- **核心字段**: model_name, strategy, confidence, reason, metadata
- **关键方法**: to_dict(), __str__()

### 4. RouterConfig（路由器配置）
- **功能**: 管理路由器配置和YAML解析
- **核心特性**: YAML/JSON配置支持、配置验证、模型管理
- **关键方法**: from_yaml(), to_yaml()

### 5. TaskFeatures（任务特征）
- **功能**: 描述任务的各项特征（类型、复杂度、紧急度等）
- **核心字段**: task_type, complexity, urgency, budget, latency_requirement
- **关键方法**: validate()

### 6. UsageTracker（使用情况跟踪器）
- **功能**: 跟踪模型使用情况和性能统计
- **核心特性**: 性能得分计算、使用统计、历史记录
- **关键方法**: record_usage(), get_performance_score(), get_usage_summary()

### 7. RoutingStrategy（路由策略基类）
- **功能**: 定义路由策略的抽象接口
- **核心特性**: 策略模式、异步路由
- **关键方法**: route(), get_strategy_name()

### 8. 具体路由策略实现
- **CostOptimizedStrategy（成本优化策略）**: 选择成本最低的模型
- **PerformanceOptimizedStrategy（性能优化策略）**: 选择性能最好的模型
- **BalancedStrategy（平衡策略）**: 平衡成本和性能的选择
- **LearningBasedStrategy（学习型策略）**: 基于历史成功率的选择

### 9. ModelRouter（模型路由器）
- **功能**: 基础模型路由器和智能模型选择
- **核心特性**: 候选模型筛选、多维度评分、模型注册
- **关键方法**: route(), register_model(), get_usage_stats()

### 10. SmartRouter（智能路由器）
- **功能**: 策略管理和自适应路由
- **核心特性**: 策略注册、特征提取、自适应选择
- **关键方法**: route_with_strategy(), adaptive_route(), add_strategy()

## 🚀 快速开始

### 环境要求
- Python 3.12+
- PyYAML库（可选，演示代码已包含备用方案）

### 安装依赖
```bash
pip install pyyaml
```

### 运行演示
```bash
# 进入目录
cd day17-lesson68

# 运行演示代码
python multi_model_routing_demo.py
```

### 基础使用示例
```python
from multi_model_routing_demo import (
    create_sample_router_config,
    ModelRouter,
    analyze_task_from_text
)

# 创建路由器配置
config = create_sample_router_config()

# 创建模型路由器
router = ModelRouter(config)

# 模拟注册模型
for model_name in config.models:
    router.register_model(model_name, f"模拟模型实例: {model_name}")

# 分析任务特征
task_text = "帮我写一个Python函数，计算斐波那契数列"
features = analyze_task_from_text(task_text)

# 执行路由
import asyncio
async def demo():
    model = await router.route(
        prompt=task_text,
        task_type=features.task_type,
        budget=5.0
    )
    print(f"选择的模型: {model}")

asyncio.run(demo())
```

## 📖 核心概念

### 多模型路由
多模型路由是AI Agent系统中根据任务特征智能选择最合适AI模型的技术。核心价值包括：

1. **成本优化**: 为简单任务选择低成本模型，降低运营成本
2. **性能优化**: 为复杂任务选择高性能模型，保证响应质量
3. **负载均衡**: 在多模型间分配请求，提高系统稳定性
4. **自适应选择**: 根据实时特征动态调整选择策略

### 路由决策因素
路由决策基于多维度特征：

1. **任务特征**: 类型、复杂度、紧急度、预算、延迟要求
2. **模型特征**: 能力、成本、性能历史、上下文长度
3. **系统状态**: 当前负载、可用性、响应时间
4. **业务规则**: 优先级、合规要求、服务等级协议

### 评分系统
模型选择基于综合评分，包括：

1. **性能得分 (40%)**: 基于历史成功率和响应时间
2. **成本得分 (30%)**: 基于每token成本，越便宜得分越高
3. **适合度得分 (30%)**: 基于任务特征与模型能力的匹配度

### 路由策略
系统支持多种路由策略：

1. **成本优化策略**: 优先选择成本最低的可用模型
2. **性能优化策略**: 优先选择历史性能最好的模型
3. **平衡策略**: 综合考虑成本和性能的平衡选择
4. **学习型策略**: 基于历史成功率的学习选择
5. **自适应策略**: 根据任务特征自动选择最佳策略

## 🧪 演示功能

### 1. 基础路由演示
- 创建示例路由器配置
- 注册模拟模型实例
- 测试不同任务类型的路由
- 展示使用统计和性能得分

### 2. 策略路由演示
- 创建智能路由器
- 测试各种路由策略（成本优化、性能优化、平衡、学习型）
- 展示不同策略的选择结果和置信度
- 解释选择理由和决策过程

### 3. 自适应路由演示
- 演示自适应路由功能
- 根据任务特征自动选择最佳策略
- 展示特征提取和策略选择逻辑
- 解释自适应决策过程

### 4. 完整测试套件
- 配置加载和验证测试
- 任务特征分析测试
- 使用跟踪器功能测试
- 路由策略实现测试
- 模型路由器功能测试
- 智能路由器功能测试
- 序列化和配置测试

## 🔍 核心算法

### 模型选择算法
```python
def select_best_model(candidates, prompt):
    scores = {}
    for model_name in candidates:
        score = 0.0
        
        # 1. 性能得分（基于历史数据）
        perf_score = usage_tracker.get_performance_score(model_name)
        score += perf_score * 0.4
        
        # 2. 成本得分（越便宜得分越高）
        cost = config.models[model_name].cost_per_token
        cost_score = max(0, 1 - cost * 1000)  # 归一化
        score += cost_score * 0.3
        
        # 3. 适合度得分（基于提示长度和复杂度）
        fit_score = calculate_fit_score(model_name, prompt)
        score += fit_score * 0.3
        
        scores[model_name] = score
    
    return max(scores.items(), key=lambda x: x[1])[0]
```

### 自适应策略选择
```python
def select_strategy_for_features(features):
    prompt_length = features.get("prompt_length", 0)
    complexity = features.get("complexity", 0)
    urgency = features.get("urgency", 0)
    cost_sensitive = features.get("cost_sensitive", False)
    
    # 决策逻辑
    if cost_sensitive:
        return "cost_optimized"
    elif urgency > 0.7:
        return "performance_optimized"
    elif complexity > 0.6:
        return "balanced"
    else:
        return "balanced"  # 默认策略
```

### 性能得分计算
```python
def calculate_performance_score(model_name):
    stats = usage_stats.get(model_name)
    if not stats or stats["call_count"] == 0:
        return default_scores.get(model_name, 0.5)
    
    success_rate = stats["success_count"] / stats["call_count"]
    avg_response_time = stats["total_response_time"] / stats["call_count"]
    time_score = max(0, 1 - min(avg_response_time, 5) / 5)
    
    # 综合得分：成功率60%，响应时间40%
    return success_rate * 0.6 + time_score * 0.4
```

## 🛠️ 配置示例

### 模型配置YAML
```yaml
models:
  gpt-4:
    provider: "openai"
    model_name: "gpt-4"
    capabilities:
      supports_vision: false
      supports_function_calling: true
      supports_long_context: true
      max_context_length: 8192
      reasoning_depth: "deep"
    cost_per_token: 0.00003
    config:
      temperature: 0.7
      max_tokens: 2000
  
  gpt-3.5-turbo:
    provider: "openai"
    model_name: "gpt-3.5-turbo"
    capabilities:
      supports_vision: false
      supports_function_calling: true
      supports_long_context: false
      max_context_length: 4096
      reasoning_depth: "medium"
    cost_per_token: 0.0000015
    config:
      temperature: 0.7
      max_tokens: 1000
  
  claude-3:
    provider: "anthropic"
    model_name: "claude-3-opus"
    capabilities:
      supports_vision: false
      supports_function_calling: true
      supports_long_context: true
      max_context_length: 100000
      reasoning_depth: "deep"
    cost_per_token: 0.00015
    config:
      temperature: 0.7
      max_tokens: 4000
  
  gemini-pro:
    provider: "google"
    model_name: "gemini-pro"
    capabilities:
      supports_vision: true
      supports_function_calling: true
      supports_long_context: true
      max_context_length: 32768
      reasoning_depth: "medium"
    cost_per_token: 0.000001
    config:
      temperature: 0.7
      max_tokens: 1500

task_routing:
  code_generation: ["gpt-4", "claude-3"]
  text_analysis: ["gpt-4", "gemini-pro"]
  quick_answer: ["gpt-3.5-turbo"]
  creative_writing: ["claude-3", "gpt-4"]
  vision_analysis: ["gemini-pro"]

default_model: "gpt-3.5-turbo"
```

### 自定义路由策略
```python
from multi_model_routing_demo import RoutingStrategy, RoutingDecision

class CustomRoutingStrategy(RoutingStrategy):
    """自定义路由策略"""
    
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """实现自定义路由逻辑"""
        models = context.get("available_models", [])
        
        # 自定义选择逻辑
        selected_model = models[0]  # 示例：选择第一个模型
        
        return RoutingDecision(
            model_name=selected_model.model_name,
            strategy="custom",
            confidence=0.9,
            reason="自定义策略选择"
        )

# 注册自定义策略
smart_router = SmartRouter()
smart_router.add_strategy("custom", CustomRoutingStrategy())
```

## 🔧 扩展功能

### 添加新模型
```python
# 创建新模型能力
new_capabilities = ModelCapabilities(
    supports_vision=True,
    supports_function_calling=True,
    supports_long_context=True,
    max_context_length=128000,
    reasoning_depth="deep"
)

# 创建新模型配置
new_model = ModelConfig(
    provider="new_provider",
    model_name="new-model-v2",
    capabilities=new_capabilities,
    cost_per_token=0.00002,
    config={"temperature": 0.8, "max_tokens": 3000}
)

# 添加到配置
config.models["new-model"] = new_model
config.task_routing["advanced_analysis"] = ["new-model", "gpt-4"]
```

### 自定义评分权重
```python
class CustomModelRouter(ModelRouter):
    """自定义评分权重的路由器"""
    
    def _select_best_model(self, candidates: List[str], prompt: str) -> str:
        """自定义评分权重"""
        scores = {}
        
        for model_name in candidates:
            score = 0.0
            
            # 自定义权重：性能50%，成本30%，适合度20%
            perf_score = self.usage_tracker.get_performance_score(model_name)
            score += perf_score * 0.5
            
            model_config = self.config.models[model_name]
            cost = model_config.cost_per_token
            cost_score = max(0, 1 - cost * 1000)
            score += cost_score * 0.3
            
            fit_score = self._calculate_fit_score(model_name, prompt)
            score += fit_score * 0.2
            
            scores[model_name] = score
        
        return max(scores.items(), key=lambda x: x[1])[0]
```

### 实时性能监控
```python
# 获取实时使用统计
stats = router.get_usage_stats()

for model_name, model_stats in stats.items():
    print(f"{model_name}:")
    print(f"  调用次数: {model_stats['call_count']}")
    print(f"  成功率: {model_stats['success_rate']:.2%}")
    print(f"  平均响应时间: {model_stats['avg_response_time']:.4f}s")
    print(f"  平均token数: {model_stats['avg_tokens']:.0f}")
    print(f"  最后使用时间: {model_stats['last_used']}")

# 性能告警
for model_name, model_stats in stats.items():
    if model_stats['success_rate'] < 0.8:
        print(f"⚠️  警告: {model_name}成功率低于80%")
    if model_stats['avg_response_time'] > 3.0:
        print(f"⚠️  警告: {model_name}平均响应时间超过3秒")
```

## 🚨 故障排除

### 常见问题
1. **配置解析失败**
   - 检查YAML语法是否正确
   - 验证必需字段是否齐全
   - 查看错误消息中的具体行号

2. **路由选择不合理**
   - 检查任务特征是否准确
   - 验证评分权重设置
   - 查看模型能力配置

3. **性能得分不准确**
   - 检查使用记录是否完整
   - 验证成功率计算逻辑
   - 调整响应时间评分公式

4. **异步调用失败**
   - 确保使用异步上下文
   - 检查事件循环设置
   - 验证异步兼容性

### 调试技巧
1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **查看路由决策细节**
   ```python
   # 在ModelRouter中添加调试输出
   print(f"候选模型: {candidates}")
   print(f"过滤后: {filtered}")
   print(f"模型得分: {scores}")
   ```

3. **性能分析**
   ```python
   import time
   start_time = time.time()
   # 执行路由
   model = await router.route(prompt, task_type)
   elapsed = time.time() - start_time
   print(f"路由耗时: {elapsed:.4f}s")
   ```

4. **配置验证**
   ```python
   # 验证任务特征
   errors = features.validate()
   if errors:
       print(f"任务特征错误: {errors}")
   
   # 验证配置
   for model_name, config in router.config.models.items():
       print(f"{model_name}: 成本={config.cost_per_token}, 能力={config.capabilities}")
   ```

## 📚 延伸学习

### 推荐阅读
1. **AI模型管理**: 多模型系统架构设计
2. **决策系统**: 规则引擎和评分系统设计
3. **成本优化**: AI运营成本分析和优化策略
4. **性能监控**: 分布式系统性能监控和告警

### 相关技术
1. **负载均衡**: 分布式系统负载均衡算法
2. **A/B测试**: 模型效果对比测试框架
3. **特征工程**: 任务特征提取和表示学习
4. **强化学习**: 基于反馈的路由策略优化

### 开源项目参考
1. **Load Balancer**: 传统负载均衡器实现
2. **Model Garden**: 多模型管理和调度平台
3. **Cost Optimizer**: 云成本优化工具
4. **Performance Monitor**: 系统性能监控工具

## 👥 课程联系

### 与前后课程的关系
- **前导课程**: 第67节课《视觉能力支持》
  - 学习AI模型的视觉处理能力
  - 掌握图像分析和理解技术
  
- **后续课程**: 第69节课《MCP客户端架构》
  - 学习MCP协议和客户端实现
  - 掌握工具发现和调用机制

### 实际应用场景
1. **AI服务平台**: 为不同客户需求选择合适模型
2. **成本敏感应用**: 在预算限制下优化模型选择
3. **高性能系统**: 为关键任务选择高性能模型
4. **多租户系统**: 为不同租户分配不同模型资源

## 📝 练习任务

### 基础练习
1. 创建新的路由策略（如"质量优先策略"）
2. 添加新的任务类型和模型映射
3. 实现路由决策历史记录功能
4. 创建配置验证工具

### 进阶挑战
1. 实现基于机器学习的路由策略
2. 设计实时性能监控和告警系统
3. 实现分布式路由协调
4. 创建路由效果Dashboard

### 项目实践
将多模型路由系统集成到实际项目中：
1. 为现有AI服务添加智能路由功能
2. 实现路由策略A/B测试框架
3. 构建路由配置管理界面
4. 实现路由性能优化和调优

## 🏆 学习成果评估

### 优秀标准
- 能够独立设计完整的多模型路由系统
- 理解多维度评分系统的设计原理
- 能够优化路由策略选择算法
- 在实际项目中成功应用多模型路由

### 评估方式
1. **代码实现**: 检查路由系统完整性和正确性
2. **设计文档**: 评估架构设计合理性
3. **性能测试**: 验证系统性能和扩展性
4. **实际应用**: 在项目中的实际使用效果

---

**祝您学习顺利，掌握多模型路由的核心技能！**

*"最合适的工具不是最强大的，而是最适合当前任务的。"* - 系统设计原则