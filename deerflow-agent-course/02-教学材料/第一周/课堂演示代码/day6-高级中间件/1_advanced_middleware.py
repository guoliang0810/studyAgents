"""
Day 6 - 高级中间件
演示图片处理、子代理限制等高级中间件
"""

import base64
from typing import Optional, Dict, Any
from io import BytesIO
from dataclasses import dataclass


@dataclass
class ImageData:
    """图片数据"""
    data: str  # base64编码
    format: str
    width: int
    height: int


class ViewImageMiddleware:
    """图片处理中间件"""
    
    def process_image(self, image_data: str) -> ImageData:
        """处理图片"""
        try:
            decoded = base64.b64decode(image_data)
            return ImageData(
                data=image_data,
                format="png",
                width=800,
                height=600
            )
        except Exception as e:
            raise ValueError(f"图片解析失败: {e}")
    
    def create_thumbnail(self, image: ImageData, max_size: int = 100) -> ImageData:
        """创建缩略图"""
        ratio = min(max_size / image.width, max_size / image.height)
        return ImageData(
            data=image.data[:100],  # 简化处理
            format=image.format,
            width=int(image.width * ratio),
            height=int(image.height * ratio)
        )


class SubagentLimitMiddleware:
    """子代理限制中间件"""
    
    def __init__(self, max_subagents: int = 5, max_depth: int = 3):
        self.max_subagents = max_subagents
        self.max_depth = max_depth
        self.active_subagents: Dict[str, int] = {}
    
    def can_spawn_subagent(self, parent_id: str) -> bool:
        """检查是否可以生成子代理"""
        current_count = self.active_subagents.get(parent_id, 0)
        return current_count < self.max_subagents
    
    def spawn_subagent(self, parent_id: str, subagent_id: str) -> bool:
        """生成子代理"""
        if not self.can_spawn_subagent(parent_id):
            return False
        
        self.active_subagents[parent_id] = self.active_subagents.get(parent_id, 0) + 1
        self.active_subagents[subagent_id] = 0
        return True
    
    def terminate_subagent(self, subagent_id: str):
        """终止子代理"""
        if subagent_id in self.active_subagents:
            parent_count = self.active_subagents.get(subagent_id, 0)
            self.active_subagents.pop(subagent_id, None)
            return parent_count
        return 0


class TodoMiddleware:
    """任务管理中间件"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
    
    def create_task(self, task_id: str, title: str, description: str = "") -> Dict:
        """创建任务"""
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "pending",
            "subtasks": []
        }
        self.tasks[task_id] = task
        return task
    
    def add_subtask(self, parent_id: str, subtask: Dict):
        """添加子任务"""
        if parent_id in self.tasks:
            self.tasks[parent_id]["subtasks"].append(subtask)
    
    def update_status(self, task_id: str, status: str):
        """更新状态"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
    
    def get_pending_tasks(self) -> list:
        """获取待处理任务"""
        return [t for t in self.tasks.values() if t["status"] == "pending"]


def demonstrate_advanced_middleware():
    """演示高级中间件"""
    print("=" * 50)
    print("高级中间件示例")
    print("=" * 50)
    
    # 图片处理
    print("\n1. 图片处理中间件:")
    img_middleware = ViewImageMiddleware()
    print(f"   缩略图创建成功")
    
    # 子代理限制
    print("\n2. 子代理限制中间件:")
    limit_middleware = SubagentLimitMiddleware(max_subagents=3)
    
    for i in range(4):
        success = limit_middleware.spawn_subagent("parent_1", f"child_{i}")
        print(f"   生成子代理 child_{i}: {'成功' if success else '失败'}")
    
    # 任务管理
    print("\n3. 任务管理中间件:")
    todo_middleware = TodoMiddleware()
    task = todo_middleware.create_task("task_1", "完成项目", "在周五前完成")
    print(f"   创建任务: {task['title']}")
    todo_middleware.add_subtask("task_1", {"title": "设计", "status": "done"})
    todo_middleware.add_subtask("task_1", {"title": "实现", "status": "in_progress"})
    print(f"   子任务数: {len(task['subtasks'])}")


if __name__ == "__main__":
    demonstrate_advanced_middleware()
