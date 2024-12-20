from openai import OpenAI
import requests
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

# AI配置
AI_CONFIGS = {
    "openai": {
        "name": "OpenAI GPT-3.5",
        "api_key": "sk-XSfRztQaVch68gGtxQnn1dEhtBgYqZu5fz3Mtct1likGpv1x",
        "base_url": "https://api.chatanywhere.tech/v1",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2000
    },
    "doubao": {
        "name": "豆包AI",
        "api_key": "1d93fe5f-af7f-435f-8a36-8466d98a4ea0",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "ep-20241219150823-d5gbj",
        "max_tokens": 4096
    }
}

class AIConfig:
    """AI配置管理类"""
    
    @staticmethod
    def get_config(ai_type: str) -> dict:
        """获取指定AI的配置"""
        if ai_type not in AI_CONFIGS:
            raise ValueError(f"不支持的AI类型: {ai_type}")
        return AI_CONFIGS[ai_type]

class BaseAIClient(ABC):
    """AI客户端基类"""
    
    def __init__(self, max_segment_length: int = 4000):
        self.max_segment_length = max_segment_length
    
    def split_messages_by_length(self, messages: List[str]) -> List[List[str]]:
        """按长度分段消息
        Args:
            messages: 消息列表
        Returns:
            List[List[str]]: 分段后的消息列表
        """
        segments = []
        current_segment = []
        current_length = 0
        
        for msg in messages:
            msg_length = len(msg)
            if current_length + msg_length > self.max_segment_length:
                if current_segment:
                    segments.append(current_segment)
                current_segment = [msg]
                current_length = msg_length
            else:
                current_segment.append(msg)
                current_length += msg_length
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def split_messages_by_date(self, messages: List[dict], group_name: str) -> List[Tuple[str, List[str]]]:
        """按日期分段消息"""
        date_groups: Dict[str, List[str]] = {}
        
        # 1. 首先按日期分组
        for msg in messages:
            create_time = datetime.fromtimestamp(msg['create_time'])
            date_str = create_time.strftime('%Y年%m月%d日')
            
            formatted_msg = f"{msg.get('sender', 'unknown')}: {msg['content']}"
            if date_str not in date_groups:
                date_groups[date_str] = []
            date_groups[date_str].append(formatted_msg)
        
        # 2. 处理每个日期的消息
        segments = []
        dates = sorted(date_groups.keys())
        for date in dates:
            title = f"{date} 「{group_name}」群聊内容分析"
            messages = date_groups[date]
            
            # 检查该日期的消息是否需要子分段
            total_length = sum(len(msg) for msg in messages)
            if total_length > self.max_segment_length:
                # 需要子分段
                sub_segments = self.split_messages_by_length(messages)
                for i, sub_segment in enumerate(sub_segments, 1):
                    sub_title = f"{title} (第{i}/{len(sub_segments)}部分)"
                    segments.append((sub_title, sub_segment))
            else:
                # 不需要子分段
                segments.append((title, messages))
        
        return segments
    
    @abstractmethod
    def analyze_segment(self, messages: List[str], prompt: str, system_prompt: str) -> str:
        """分析单个片段，需要子类实现
        Args:
            messages: 消息列表
            prompt: 用户提示词
            system_prompt: 系统提示词
        Returns:
            str: 分析结果
        """
        pass
    
    def analyze(self, messages: List[dict], group_name: str, system_prompt: str = None) -> str:
        """分析聊天记录"""
        try:
            if not system_prompt:
                system_prompt = "你是一位专业的群聊分析师，简明扼要地总结重点。"
            
            # 按日期分段（包含必要的子分段）
            segments = self.split_messages_by_date(messages, group_name)
            summaries = []
            
            # 分析每个分段
            for title, segment_messages in segments:
                prompt = f"请分析以下微信群在{title}的聊天记录，并给出总结。"
                summary = self.analyze_segment(segment_messages, prompt, system_prompt)
                if summary:
                    summaries.append(f"{title}：\n{summary}")
            
            # 合并所有分析结果
            return "\n\n".join(summaries)
            
        except Exception as e:
            print(f"AI分析失败: {str(e)}")
            raise RuntimeError(f"AI分析失败: {str(e)}")

class OpenAIClient(BaseAIClient):
    def __init__(self):
        config = AI_CONFIGS["openai"]
        # OpenAI免费API的token限制约为4096，保守估计中文字符
        super().__init__(max_segment_length=2000)  # 设置较小的分段长度
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.max_tokens = config["max_tokens"]
    
    def analyze_segment(self, messages: List[str], prompt: str, system_prompt: str) -> str:
        """分析单个片段"""
        try:
            chat_text = "\n".join(messages)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n聊天记录：\n{chat_text}"
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI分析片段失败: {str(e)}")
            raise

class DouBaoClient(BaseAIClient):
    def __init__(self):
        config = AI_CONFIGS["doubao"]
        # 豆包AI支持更长的上下文，可以设置更大的分段长度
        super().__init__(max_segment_length=6000)  # 恢复到更大的分段长度
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.max_tokens = config["max_tokens"]
    
    def analyze_segment(self, messages: List[str], prompt: str, system_prompt: str) -> str:
        """分析单个片段"""
        try:
            chat_text = "\n".join(messages)
            
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\n\n聊天记录：\n{chat_text}"
                        }
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise RuntimeError("豆包AI返回结果格式错误")
            else:
                error = response.json().get("error", {})
                error_msg = error.get("message", "未知错误")
                raise RuntimeError(f"豆包AI调用失败: {error_msg}")
                
        except Exception as e:
            print(f"豆包AI分析失败: {str(e)}")
            raise