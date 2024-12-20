import re
from datetime import datetime
from typing import List, Dict, Any
from collections import Counter, defaultdict
from .ai_client import AIClient
from ..utils.message_parser import parse_message_content, get_sender_name
from ..utils.config import Config

class MessageAnalyzer:
    """消息分析器"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.config = Config()
    
    def filter_message(self, message: Dict) -> bool:
        """过滤不需要的消息"""
        content = message['content']
        if not content or not isinstance(content, str):
            return False

        content = content.strip()
        if not content or content.isspace():
            return False

        # 过滤规则
        filter_patterns = [
            r"<[^>]+>",  # XML标签
            r"\[动画表情\]",
            r"\[表情\]",
            r"\[图片\]",
            r"\[文件\]",
            r"\[视频\]",
            r"\[语音\]",
            r"\[通话\]",
            r"\[转账\]",
            r"\[分享\]",
            r"\[聊天记录\]",
            r"撤回了一条消息",
        ]
        
        for pattern in filter_patterns:
            if re.search(pattern, content):
                return False
        
        return True
    
    def analyze_messages(self, messages: List[Dict]):
        """分析消息"""
        # 准备统计数据
        stats = {
            "total_messages": len(messages),
            "user_activity": defaultdict(int),
            "hourly_activity": defaultdict(int),
            "message_types": Counter()
        }
        
        # 准备AI分析的消息记录
        chat_records = []
        
        # 处理每条消息
        for msg in messages:
            # 基础统计
            msg_time = datetime.fromtimestamp(msg['create_time'])
            sender = get_sender_name(msg)
            content = parse_message_content(msg['type'], msg['sub_type'], msg['content'])
            
            # 过滤并添加到记录
            if self.filter_message(msg):
                time_str = msg_time.strftime("%H:%M:%S")
                chat_records.append(f"{time_str} {sender}: {content}")
            
            # 更新统计数据
            stats["user_activity"][sender] += 1
            stats["hourly_activity"][msg_time.hour] += 1
            stats["message_types"][msg['type']] += 1
        
        # AI分析
        print("\n=== 开始AI分析 ===")
        analysis_result = self.ai_client.analyze_chat(chat_records)
        
        # 输出分析结果
        print("\n=== 分析结果 ===")
        print(analysis_result["summary"])
        
        # 输出统计数据
        print("\n=== 统计数据 ===")
        print(f"总消息数: {stats['total_messages']}")
        print("\n活跃用户:")
        for user, count in sorted(stats["user_activity"].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"- {user}: {count}条消息") 