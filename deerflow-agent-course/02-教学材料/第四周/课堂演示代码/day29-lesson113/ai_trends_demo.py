#!/usr/bin/env python3
# 第113节课：AI Agent技术趋势
from typing import Dict, Any, List

class TrendCategory:
    MULTIMODAL = "multimodal"
    AUTONOMOUS = "autonomous"
    FEDERATED = "federated"
    EDGE = "edge"

class TrendAnalyzer:
    def __init__(self):
        self.trends: List[Dict] = []
    
    def add_trend(self, category: str, name: str, description: str, impact: int):
        self.trends.append({"category": category, "name": name, "description": description, "impact": impact})
    
    def get_trends(self, category: str = None) -> List[Dict]:
        if category:
            return [t for t in self.trends if t["category"] == category]
        return self.trends
    
    def get_top_trends(self, n: int = 5) -> List[Dict]:
        return sorted(self.trends, key=lambda x: x["impact"], reverse=True)[:n]

class ResearchPaper:
    def __init__(self, title: str, authors: List[str], year: int):
        self.title = title
        self.authors = authors
        self.year = year
    
    def to_dict(self) -> Dict:
        return {"title": self.title, "authors": self.authors, "year": self.year}

def run_demo():
    print("AI Agent技术趋势演示")
    analyzer = TrendAnalyzer()
    analyzer.add_trend(TrendCategory.MULTIMODAL, "GPT-4V", "多模态大模型", 95)
    analyzer.add_trend(TrendCategory.AUTONOMOUS, "AutoGPT", "自主Agent系统", 90)
    print(f"趋势: {analyzer.get_top_trends()}")

def run_tests():
    print("测试: 趋势分析")
    a = TrendAnalyzer()
    a.add_trend("test", "t1", "d1", 5)
    a.add_trend("test", "t2", "d2", 10)
    assert len(a.get_top_trends(1)) == 1
    assert a.get_top_trends(1)[0]["name"] == "t2"
    print("✓ 趋势测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
