import time
from typing import Dict, Any
from datetime import datetime

class AnalysisStats:
    """分析统计类"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_chars = 0
        self.total_messages = 0
        self.segments_count = 0
        self.total_tokens = 0  # 实际使用的总token数
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
    
    def stop(self):
        """停止计时"""
        self.end_time = time.time()
    
    def add_segment(self, text: str):
        """添加一个分析片段"""
        self.total_chars += len(text)
        self.segments_count += 1
    
    def add_usage(self, usage: dict):
        """添加API返回的usage信息"""
        if "total_tokens" in usage:
            self.total_tokens += usage["total_tokens"]
    
    def get_duration(self) -> float:
        """获取持续时间（秒）"""
        if not self.start_time or not self.end_time:
            return 0
        return self.end_time - self.start_time
    
    def format_duration(self) -> str:
        """格式化持续时间"""
        duration = self.get_duration()
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}分{seconds}秒"
    
    def get_summary(self) -> str:
        """获取统计摘要"""
        return (
            f"\n\n------- 分析统计 -------\n"
            f"• 实际耗时：{self.format_duration()}\n"
            f"• 处理字符：{self.total_chars:,} 字\n"
            f"• 消耗Token：{self.total_tokens:,}\n"
            f"------------------------"
        )