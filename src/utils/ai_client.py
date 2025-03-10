import json
import os
from typing import Dict, Any
from openai import OpenAI
import requests
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from .stats import AnalysisStats
import urllib3
import certifi
import re
import math

def load_ai_config() -> Dict[str, Any]:
    """加载AI配置"""
    config_path = os.path.join("config", "ai_config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载AI配置失败: {e}")
        return {}

# AI配置
AI_CONFIGS = load_ai_config()

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
        self.stats = AnalysisStats()
    
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
            title = f"「{group_name}」{date}群聊内容分析"
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
        """分析单个片段，需类实现
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
            self.stats = AnalysisStats()  # 重置统计
            self.stats.start()  # 开始计时
            
            if not system_prompt:
                system_prompt = "你是一位专业的群聊分析师，简明扼要地总结重点。"
            
            # 按日期分段
            segments = self.split_messages_by_date(messages, group_name)
            summaries = []
            
            # 分析每个分段
            for title, segment_messages in segments:
                chat_text = "\n".join(segment_messages)
                self.stats.add_segment(chat_text)  # 统计字符
                
                prompt = f"请分析以下微信群在{title}的聊天记录，并给出总结。"
                summary = self.analyze_segment(segment_messages, prompt, system_prompt)
                if summary:
                    summaries.append(f"{title}：\n{summary}")
            
            # 停止计时
            self.stats.stop()
            
            # 合并所有分析结果，添加统计信息
            return "\n\n".join(summaries) + self.stats.get_summary()
            
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
            
            # 记录token使用情况
            if hasattr(response, 'usage'):
                usage = {
                    'total_tokens': response.usage.total_tokens
                }
                self.stats.add_usage(usage)
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"OpenAI分析失败: {str(e)}")
            raise

def calculate_tokens(text: str) -> int:
    """估算文本的 token 数量
    Args:
        text: 需要计算 token 数的文本
    Returns:
        估算的 token 数量
    """
    if not text:
        return 0
        
    # 中文、日文、韩文等 CJK 字符的正则表达式
    cjk_regex = re.compile(
        r'[\u4E00-\u9FFF\u3400-\u4DBF\u20000-\u2A6DF\u2A700-\u2B73F'
        r'\u2B740-\u2B81F\u2B820-\u2CEAF\uF900-\uFAFF\u3040-\u309F'
        r'\u30A0-\u30FF\uAC00-\uD7AF]'
    )
    
    # 英文单词、数字、标点符号的正则表达式
    word_regex = re.compile(r'\w+|\s+|[^\w\s]')
    
    token_count = 0
    
    # 计算 CJK 字符的 token 数（每个字符 2 个 token）
    cjk_chars = len(re.findall(cjk_regex, text))
    token_count += cjk_chars * 2
    
    # 移除已计算的 CJK 字符，处理剩余文本
    remaining_text = re.sub(cjk_regex, '', text)
    tokens = re.findall(word_regex, remaining_text)
    
    # 计算英文单词和标点的 token 数
    for token in tokens:
        if re.match(r'\s+', token):  # 空格
            continue
        elif re.match(r'^\w+$', token):  # 英文单词
            token_count += math.ceil(len(token) / 3.5)
        else:  # 标点符号
            token_count += 1
    
    return token_count

class DeepSeekClient(BaseAIClient):
    def __init__(self):
        config = AI_CONFIGS["deepseek"]
        self.api_key = config["api_key"]
        self.base_url = f"{config['base_url']}/chat/completions"
        self.model = "deepseek-ai/DeepSeek-R1"
        self.max_tokens = 8192
        # 使用 95% 的 token 限制作为安全阈值
        self.safe_token_limit = int(self.max_tokens * 0.95)
        super().__init__(max_segment_length=self.safe_token_limit)
    
    def analyze_segment(self, messages: List[str], prompt: str, system_prompt: str) -> str:
        """分析单个片段，使用流式请求"""
        try:
            chat_text = "\n".join(messages)
            
            # 构建请求体
            payload = {
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
                "stream": True,
                "max_tokens": self.max_tokens,
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 50,
                "frequency_penalty": 0.5,
                "response_format": {"type": "text"}
            }
            
            # 发送流式请求
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                error = response.json().get("error", {})
                raise RuntimeError(f"DeepSeek AI调用失败: {error.get('message', '未知错误')}")
            
            # 处理流式响应
            full_response = ""
            for line in response.iter_lines():
                if line:
                    # 移除 "data: " 前缀
                    line = line.decode('utf-8').replace("data: ", "")
                    
                    # 检查是否是结束标记
                    if line.strip() == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(line)
                        # 只获取内容，忽略思考过程
                        content = data["choices"][0]["delta"].get("content", "")
                        if content:
                            full_response += content
                    except json.JSONDecodeError:
                        continue
            
            # 记录 token 使用情况（如果有）
            if hasattr(response, 'usage'):
                self.stats.add_usage(response.usage)
            
            return full_response.strip()
            
        except Exception as e:
            print(f"DeepSeek AI分析失败: {str(e)}")
            raise