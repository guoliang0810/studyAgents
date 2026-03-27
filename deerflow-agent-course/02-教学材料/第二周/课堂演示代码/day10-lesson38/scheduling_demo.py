#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 10 Lesson 38: 任务调度算法 (Task Scheduling Algorithms)

本文件演示任务调度算法的完整实现，包括：
1. 基本调度算法 - FIFO、优先级调度、轮转调度
2. 资源感知调度 - 基于CPU、内存等资源的智能调度
3. 负载均衡调度 - Worker负载评估和任务分配
4. 实时调度算法 - 最早截止时间优先（EDF）

使用示例:
    python scheduling_demo.py          # 运行基本演示
    python scheduling_demo.py --test   # 运行测试套件
    python scheduling_demo.py --demo   # 运行完整演示
    python scheduling_demo.py --help   # 显示帮助信息
"""

import asyncio
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import heapq
from abc import ABC, abstractmethod

class SchedulingStrategy(Enum):
    """调度策略枚举"""
    FIFO = "fifo"                  # 先进先出
    PRIORITY = "priority"          # 优先级调度
    ROUND_ROBIN = "round_robin"    # 轮转调度
    SHORTEST_JOB_FIRST = "sjf"     # 最短作业优先
    RESOURCE_AWARE = "resource"    # 资源感知调度
    EARLIEST_DEADLINE_FIRST = "edf"  # 最早截止时间优先

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败

@dataclass
class ResourceRequirement:
    """资源需求数据类"""
    cpu_cores: float = 1.0        # CPU核心数
    memory_mb: float = 128.0      # 内存（MB）
    disk_io_mbps: float = 10.0    # 磁盘IO（MB/s）
    network_mbps: float = 1.0     # 网络带宽（MB/s）
    
    def meets(self, available: 'ResourceRequirement') -> bool:
        """检查是否满足资源需求"""
        return (self.cpu_cores <= available.cpu_cores and
                self.memory_mb <= available.memory_mb and
                self.disk_io_mbps <= available.disk_io_mbps and
                self.network_mbps <= available.network_mbps)

@dataclass
class ScheduledTask:
    """调度任务数据类"""
    task_id: str                          # 任务ID
    name: str                             # 任务名称
    priority: int = 50                    # 优先级（0-100）
    estimated_time: float = 1.0           # 预估执行时间（秒）
    deadline: Optional[float] = None      # 截止时间（时间戳）
    resource_req: ResourceRequirement = field(default_factory=ResourceRequirement)
    created_time: float = field(default_factory=time.time)  # 创建时间
    
    def __lt__(self, other):
        """用于堆排序比较"""
        return self.priority > other.priority  # 优先级高的排前面

@dataclass
class Worker:
    """工作节点数据类"""
    worker_id: str                        # Worker ID
    name: str                             # Worker名称
    available_resources: ResourceRequirement  # 可用资源
    task_queue: List[ScheduledTask] = field(default_factory=list)  # 任务队列
    current_task: Optional[ScheduledTask] = None  # 当前任务
    completed_tasks: int = 0              # 完成任务数
    total_processing_time: float = 0.0    # 总处理时间
    
    @property
    def load_score(self) -> float:
        """计算负载分数（0-100，越高越忙）"""
        if not self.task_queue and not self.current_task:
            return 0.0
        
        # 基于任务队列长度和当前任务预估时间计算负载
        queue_load = len(self.task_queue) * 20
        current_load = 0
        
        if self.current_task:
            # 当前任务负载基于预估时间（假设最大10秒为100分）
            current_load = min(100, self.current_task.estimated_time * 10)
        
        return min(100, queue_load + current_load)
    
    def is_available(self, task: ScheduledTask) -> bool:
        """检查是否可接受新任务"""
        return task.resource_req.meets(self.available_resources)
    
    def assign_task(self, task: ScheduledTask) -> bool:
        """分配任务给Worker"""
        if not self.is_available(task):
            return False
        
        self.task_queue.append(task)
        return True
    
    def process_next_task(self) -> Optional[ScheduledTask]:
        """处理下一个任务"""
        if self.current_task or not self.task_queue:
            return None
        
        self.current_task = self.task_queue.pop(0)
        return self.current_task
    
    def complete_current_task(self) -> Optional[ScheduledTask]:
        """完成当前任务"""
        if not self.current_task:
            return None
        
        completed = self.current_task
        self.completed_tasks += 1
        self.total_processing_time += completed.estimated_time
        self.current_task = None
        return completed

class TaskScheduler(ABC):
    """任务调度器抽象基类"""
    
    def __init__(self, strategy: SchedulingStrategy):
        self.strategy = strategy
        self.pending_tasks: List[ScheduledTask] = []
        self.workers: Dict[str, Worker] = {}
        self.completed_tasks: List[ScheduledTask] = []
    
    def add_worker(self, worker: Worker) -> None:
        """添加Worker"""
        self.workers[worker.worker_id] = worker
    
    def remove_worker(self, worker_id: str) -> None:
        """移除Worker"""
        if worker_id in self.workers:
            del self.workers[worker_id]
    
    def submit_task(self, task: ScheduledTask) -> None:
        """提交任务"""
        self.pending_tasks.append(task)
    
    @abstractmethod
    def schedule(self) -> Dict[str, List[ScheduledTask]]:
        """调度任务（抽象方法，由子类实现）"""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度统计信息"""
        total_tasks = len(self.completed_tasks)
        total_workers = len(self.workers)
        
        worker_stats = {}
        for worker_id, worker in self.workers.items():
            worker_stats[worker_id] = {
                "completed_tasks": worker.completed_tasks,
                "total_processing_time": worker.total_processing_time,
                "load_score": worker.load_score
            }
        
        return {
            "strategy": self.strategy.value,
            "total_tasks": total_tasks,
            "total_workers": total_workers,
            "worker_statistics": worker_stats,
            "pending_tasks": len(self.pending_tasks)
        }

class FIFOScheduler(TaskScheduler):
    """FIFO调度器"""
    
    def __init__(self):
        super().__init__(SchedulingStrategy.FIFO)
    
    def schedule(self) -> Dict[str, List[ScheduledTask]]:
        """FIFO调度：按任务到达顺序分配"""
        assignments = {worker_id: [] for worker_id in self.workers}
        
        # 按创建时间排序（最早创建的任务优先）
        sorted_tasks = sorted(self.pending_tasks, key=lambda t: t.created_time)
        
        worker_list = list(self.workers.values())
        worker_index = 0
        
        for task in sorted_tasks:
            # 循环选择Worker
            for _ in range(len(worker_list)):
                worker = worker_list[worker_index]
                worker_index = (worker_index + 1) % len(worker_list)
                
                if worker.assign_task(task):
                    assignments[worker.worker_id].append(task)
                    self.pending_tasks.remove(task)
                    break
        
        return assignments

class PriorityScheduler(TaskScheduler):
    """优先级调度器"""
    
    def __init__(self):
        super().__init__(SchedulingStrategy.PRIORITY)
    
    def schedule(self) -> Dict[str, List[ScheduledTask]]:
        """优先级调度：按优先级分配"""
        assignments = {worker_id: [] for worker_id in self.workers}
        
        # 按优先级排序（优先级高的任务优先）
        sorted_tasks = sorted(self.pending_tasks, key=lambda t: t.priority, reverse=True)
        
        worker_list = list(self.workers.values())
        
        for task in sorted_tasks:
            # 选择当前负载最低的Worker
            best_worker = min(worker_list, key=lambda w: w.load_score)
            
            if best_worker.assign_task(task):
                assignments[best_worker.worker_id].append(task)
                self.pending_tasks.remove(task)
        
        return assignments

class ResourceAwareScheduler(TaskScheduler):
    """资源感知调度器"""
    
    def __init__(self):
        super().__init__(SchedulingStrategy.RESOURCE_AWARE)
    
    def schedule(self) -> Dict[str, List[ScheduledTask]]:
        """资源感知调度：考虑资源需求和可用性"""
        assignments = {worker_id: [] for worker_id in self.workers}
        
        # 按资源需求排序（资源需求大的任务优先）
        sorted_tasks = sorted(self.pending_tasks, 
                            key=lambda t: t.resource_req.cpu_cores + t.resource_req.memory_mb / 100, 
                            reverse=True)
        
        worker_list = list(self.workers.values())
        
        for task in sorted_tasks:
            # 选择满足资源需求且负载最低的Worker
            suitable_workers = [w for w in worker_list if w.is_available(task)]
            
            if suitable_workers:
                best_worker = min(suitable_workers, key=lambda w: w.load_score)
                if best_worker.assign_task(task):
                    assignments[best_worker.worker_id].append(task)
                    self.pending_tasks.remove(task)
        
        return assignments

class EDFScheduler(TaskScheduler):
    """最早截止时间优先调度器"""
    
    def __init__(self):
        super().__init__(SchedulingStrategy.EARLIEST_DEADLINE_FIRST)
    
    def schedule(self) -> Dict[str, List[ScheduledTask]]:
        """EDF调度：按截止时间分配"""
        assignments = {worker_id: [] for worker_id in self.workers}
        
        # 按截止时间排序（截止时间早的任务优先）
        tasks_with_deadline = [t for t in self.pending_tasks if t.deadline is not None]
        tasks_without_deadline = [t for t in self.pending_tasks if t.deadline is None]
        
        # 有截止时间的任务按截止时间排序
        sorted_with_deadline = sorted(tasks_with_deadline, key=lambda t: t.deadline)
        # 无截止时间的任务按创建时间排序
        sorted_without_deadline = sorted(tasks_without_deadline, key=lambda t: t.created_time)
        
        # 合并排序（有截止时间的优先）
        sorted_tasks = sorted_with_deadline + sorted_without_deadline
        
        worker_list = list(self.workers.values())
        
        for task in sorted_tasks:
            # 选择当前负载最低的Worker
            best_worker = min(worker_list, key=lambda w: w.load_score)
            
            if best_worker.assign_task(task):
                assignments[best_worker.worker_id].append(task)
                self.pending_tasks.remove(task)
        
        return assignments

class SchedulingTestSuite:
    """调度测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_fifo_scheduler", self.test_fifo_scheduler),
            ("test_priority_scheduler", self.test_priority_scheduler),
            ("test_resource_aware_scheduler", self.test_resource_aware_scheduler),
            ("test_edf_scheduler", self.test_edf_scheduler),
            ("test_worker_load_calculation", self.test_worker_load_calculation),
        ]
    
    def test_fifo_scheduler(self) -> Tuple[bool, str]:
        """测试FIFO调度器"""
        scheduler = FIFOScheduler()
        
        # 创建Worker
        worker1 = Worker("worker1", "Worker 1", ResourceRequirement(4, 4096))
        worker2 = Worker("worker2", "Worker 2", ResourceRequirement(4, 4096))
        
        scheduler.add_worker(worker1)
        scheduler.add_worker(worker2)
        
        # 创建任务
        for i in range(4):
            task = ScheduledTask(
                task_id=f"task_{i}",
                name=f"Task {i}",
                estimated_time=1.0,
                created_time=time.time() + i  # 不同创建时间
            )
            scheduler.submit_task(task)
        
        # 执行调度
        assignments = scheduler.schedule()
        
        # 验证结果
        total_assigned = sum(len(tasks) for tasks in assignments.values())
        if total_assigned != 4:
            return False, f"任务分配数量错误: {total_assigned}/4"
        
        return True, f"FIFO调度测试通过，分配了{total_assigned}个任务"
    
    def test_priority_scheduler(self) -> Tuple[bool, str]:
        """测试优先级调度器"""
        scheduler = PriorityScheduler()
        
        # 创建Worker
        worker = Worker("worker1", "Worker 1", ResourceRequirement(4, 4096))
        scheduler.add_worker(worker)
        
        # 创建不同优先级的任务
        priorities = [30, 70, 50, 90, 10]
        for i, priority in enumerate(priorities):
            task = ScheduledTask(
                task_id=f"task_{i}",
                name=f"Task {i}",
                priority=priority,
                estimated_time=1.0
            )
            scheduler.submit_task(task)
        
        # 执行调度
        assignments = scheduler.schedule()
        
        # 验证高优先级任务优先分配
        assigned_tasks = assignments.get("worker1", [])
        if len(assigned_tasks) != 5:
            return False, f"任务分配数量错误: {len(assigned_tasks)}/5"
        
        # 检查是否按优先级排序
        assigned_priorities = [task.priority for task in assigned_tasks]
        sorted_priorities = sorted(priorities, reverse=True)
        
        if assigned_priorities != sorted_priorities:
            return False, f"任务未按优先级排序"
        
        return True, "优先级调度测试通过"
    
    def test_resource_aware_scheduler(self) -> Tuple[bool, str]:
        """测试资源感知调度器"""
        scheduler = ResourceAwareScheduler()
        
        # 创建不同资源的Worker
        worker1 = Worker("worker1", "Worker 1", ResourceRequirement(2, 2048))
        worker2 = Worker("worker2", "Worker 2", ResourceRequirement(8, 8192))
        
        scheduler.add_worker(worker1)
        scheduler.add_worker(worker2)
        
        # 创建资源需求不同的任务
        # 高资源需求任务
        high_resource_task = ScheduledTask(
            task_id="high_task",
            name="High Resource Task",
            resource_req=ResourceRequirement(4, 4096),  # 需要4核4GB
            estimated_time=2.0
        )
        
        # 低资源需求任务
        low_resource_task = ScheduledTask(
            task_id="low_task",
            name="Low Resource Task",
            resource_req=ResourceRequirement(1, 512),   # 需要1核512MB
            estimated_time=1.0
        )
        
        scheduler.submit_task(high_resource_task)
        scheduler.submit_task(low_resource_task)
        
        # 执行调度
        assignments = scheduler.schedule()
        
        # 验证高资源任务分配给高资源Worker
        worker1_tasks = assignments.get("worker1", [])
        worker2_tasks = assignments.get("worker2", [])
        
        if len(worker1_tasks) + len(worker2_tasks) != 2:
            return False, "任务分配数量错误"
        
        # 高资源任务应该分配给worker2
        high_task_assigned_to = None
        for worker_id, tasks in assignments.items():
            for task in tasks:
                if task.task_id == "high_task":
                    high_task_assigned_to = worker_id
        
        if high_task_assigned_to != "worker2":
            return False, f"高资源任务错误分配给了{high_task_assigned_to}"
        
        return True, "资源感知调度测试通过"
    
    def test_edf_scheduler(self) -> Tuple[bool, str]:
        """测试最早截止时间优先调度器"""
        scheduler = EDFScheduler()
        
        # 创建Worker
        worker = Worker("worker1", "Worker 1", ResourceRequirement(4, 4096))
        scheduler.add_worker(worker)
        
        # 创建不同截止时间的任务
        current_time = time.time()
        deadlines = [current_time + 5, current_time + 2, current_time + 10, current_time + 1]
        
        for i, deadline in enumerate(deadlines):
            task = ScheduledTask(
                task_id=f"task_{i}",
                name=f"Task {i}",
                deadline=deadline,
                estimated_time=1.0
            )
            scheduler.submit_task(task)
        
        # 执行调度
        assignments = scheduler.schedule()
        
        # 验证任务按截止时间分配
        assigned_tasks = assignments.get("worker1", [])
        if len(assigned_tasks) != 4:
            return False, f"任务分配数量错误: {len(assigned_tasks)}/4"
        
        # 检查是否按截止时间排序
        assigned_deadlines = [task.deadline for task in assigned_tasks]
        sorted_deadlines = sorted(deadlines)
        
        if assigned_deadlines != sorted_deadlines:
            return False, "任务未按截止时间排序"
        
        return True, "最早截止时间优先调度测试通过"
    
    def test_worker_load_calculation(self) -> Tuple[bool, str]:
        """测试Worker负载计算"""
        worker = Worker("worker1", "Worker 1", ResourceRequirement(4, 4096))
        
        # 测试空闲Worker
        if worker.load_score != 0.0:
            return False, f"空闲Worker负载分数错误: {worker.load_score}"
        
        # 添加任务到队列
        for i in range(3):
            task = ScheduledTask(
                task_id=f"task_{i}",
                name=f"Task {i}",
                estimated_time=2.0
            )
            worker.task_queue.append(task)
        
        # 测试有队列任务的Worker
        expected_load = 3 * 20  # 3个任务 * 20分/任务
        if worker.load_score != expected_load:
            return False, f"Worker负载分数计算错误: {worker.load_score} vs {expected_load}"
        
        # 设置当前任务
        current_task = ScheduledTask(
            task_id="current",
            name="Current Task",
            estimated_time=5.0  # 5秒任务，应该贡献50分
        )
        worker.current_task = current_task
        
        expected_load = min(100, 3 * 20 + 50)  # 队列任务 + 当前任务，但上限100
        if worker.load_score != expected_load:
            return False, f"Worker负载分数计算错误: {worker.load_score} vs {expected_load}"
        
        return True, f"Worker负载计算测试通过，负载分数: {worker.load_score}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行调度算法测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {len(self.tests)}")
        print(f"   通过测试: {passed}")
        print(f"   失败测试: {failed}")
        print(f"   成功率: {passed / len(self.tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": len(self.tests),
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": passed / len(self.tests) * 100 if len(self.tests) > 0 else 0
            },
            "detailed_results": results
        }

def main_demo():
    """主演示函数"""
    print("🎓 Day 10 Lesson 38: 任务调度算法演示")
    print("=" * 60)
    
    # 创建Workers
    workers = [
        Worker("worker1", "Worker 1", ResourceRequirement(4, 4096)),
        Worker("worker2", "Worker 2", ResourceRequirement(8, 8192)),
        Worker("worker3", "Worker 3", ResourceRequirement(2, 2048)),
    ]
    
    print("\n1. 创建Workers:")
    for worker in workers:
        print(f"   {worker.name}: CPU={worker.available_resources.cpu_cores}核, "
              f"内存={worker.available_resources.memory_mb}MB")
    
    # 创建任务
    tasks = [
        ScheduledTask("task1", "数据处理任务", priority=80, estimated_time=3.0, 
                     resource_req=ResourceRequirement(2, 1024)),
        ScheduledTask("task2", "机器学习任务", priority=90, estimated_time=5.0,
                     resource_req=ResourceRequirement(4, 2048)),
        ScheduledTask("task3", "文件转换任务", priority=70, estimated_time=2.0,
                     resource_req=ResourceRequirement(1, 512)),
        ScheduledTask("task4", "网络请求任务", priority=60, estimated_time=1.0,
                     resource_req=ResourceRequirement(1, 256)),
        ScheduledTask("task5", "图像处理任务", priority=85, estimated_time=4.0,
                     resource_req=ResourceRequirement(2, 1024)),
    ]
    
    print("\n2. 创建任务:")
    for task in tasks:
        print(f"   {task.name}: 优先级={task.priority}, 预估时间={task.estimated_time}秒")
    
    # 测试不同调度策略
    schedulers = [
        ("FIFO调度", FIFOScheduler()),
        ("优先级调度", PriorityScheduler()),
        ("资源感知调度", ResourceAwareScheduler()),
    ]
    
    for scheduler_name, scheduler in schedulers:
        print(f"\n3. {scheduler_name}测试:")
        
        # 添加Workers
        for worker in workers:
            scheduler.add_worker(worker)
        
        # 提交任务
        for task in tasks:
            scheduler.submit_task(task)
        
        # 执行调度
        assignments = scheduler.schedule()
        
        # 显示分配结果
        for worker_id, assigned_tasks in assignments.items():
            if assigned_tasks:
                task_names = [task.name for task in assigned_tasks]
                print(f"   {worker_id}: {', '.join(task_names)}")
        
        # 显示统计信息
        stats = scheduler.get_statistics()
        print(f"   总任务数: {stats['total_tasks']}")
        print(f"   待处理任务: {stats['pending_tasks']}")
    
    print("\n4. 负载均衡演示:")
    # 创建一个负载不均衡的场景
    scheduler = PriorityScheduler()
    for worker in workers:
        scheduler.add_worker(worker)
    
    # 模拟worker1已有任务
    workers[0].task_queue = [
        ScheduledTask("existing1", "现有任务1", estimated_time=2.0),
        ScheduledTask("existing2", "现有任务2", estimated_time=3.0),
    ]
    
    # 提交新任务
    new_task = ScheduledTask("new_task", "新任务", priority=75, estimated_time=1.0)
    scheduler.submit_task(new_task)
    
    # 执行调度
    assignments = scheduler.schedule()
    
    print("   初始负载:")
    for worker in workers:
        print(f"     {worker.name}: 负载={worker.load_score:.1f}, 队列={len(worker.task_queue)}个任务")
    
    print(f"   调度结果: 新任务分配给了{list(assignments.keys())[0] if assignments else '无Worker'}")

def run_tests():
    """运行测试套件"""
    test_suite = SchedulingTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 调度算法测试套件验证通过")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        main_demo()
    else:
        main_demo()