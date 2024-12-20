from openai import OpenAI
import requests

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
        "max_tokens": 2000
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

class OpenAIClient:
    def __init__(self):
        config = AI_CONFIGS["openai"]
        print(f"初始化OpenAI客户端: 使用API地址 {config['base_url']}")
        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        self.model = config["model"]
        self.max_tokens = config["max_tokens"]
        self.max_segment_length = 2000
        print(f"OpenAI客户端初始化完成: model={self.model}")
    
    def split_messages(self, messages):
        """将消息分段"""
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
    
    def analyze_segment(self, messages, prompt):
        """分析单个片段"""
        try:
            chat_text = "\n".join(messages)
            print(f"发送请求到 {self.client.base_url}")
            print(f"分析片段，长度：{len(chat_text)}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位信息总结大师，擅长将复杂的对话浓缩成简洁有力的总结。"
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\n聊天记录：\n{chat_text}"
                    }
                ],
                temperature=0.7,
                max_tokens=self.max_tokens,
                timeout=30  # 添加超时设置
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI请求失败: {str(e)}")
            raise RuntimeError(f"OpenAI调用失败: {str(e)}")
    
    def merge_summaries(self, summaries):
        """合并多个总结"""
        try:
            if not summaries:
                return "没有有效内容需要总结"
            
            if len(summaries) == 1:
                return summaries[0]
            
            combined_summary = "\n\n".join(summaries)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位信息整理专家，擅长去除重复信息，突出重点，内容清晰易读。"
                    },
                    {
                        "role": "user",
                        "content": f"""以下是多段聊天记录的总结，请整理并去除重复信息，保持要点清晰：

                        {combined_summary}

                        请按以下格式输出：
                        
                        【主要话题】
                        1. ...
                        
                        【重要结论】
                        1. ...
                        
                        【关键观点】
                        1. ...
                        
                        【提出的问题】
                        1. ...
                        """
                    }
                ],
                temperature=0.7,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"合并总结失败: {str(e)}")
            return "\n\n".join(summaries)
    
    def analyze(self, messages, prompt):
        """使用OpenAI分析聊天记录"""
        try:
            print(f"开始分析，消息总数：{len(messages)}")
            
            # 1. 分段处理
            segments = self.split_messages(messages)
            print(f"分成 {len(segments)} 个片段")
            
            # 2. 分别分析每个片段
            summaries = []
            for i, segment in enumerate(segments):
                print(f"分析第 {i+1}/{len(segments)} 个片段")
                summary = self.analyze_segment(segment, prompt)
                if summary:
                    summaries.append(summary)
            
            # 3. 合并所有总结
            print("合并所有片段的分析结果")
            final_summary = self.merge_summaries(summaries)
            
            return final_summary
            
        except Exception as e:
            print(f"OpenAI分析失败: {str(e)}")
            raise RuntimeError(f"OpenAI分析失败: {str(e)}")

class DouBaoClient:
    def __init__(self):
        config = AI_CONFIGS["doubao"]  # 直接使用配置
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]
        self.max_tokens = config["max_tokens"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        print(f"初始化豆包AI客户端: model={self.model}")
    
    def analyze(self, messages):
        """使用豆包AI分析聊天记录"""
        try:
            chat_text = "\n".join(messages)
            print(f"准备发送到豆包AI，消息长度：{len(chat_text)}")
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位信息总结大师，擅长将复杂的对话浓缩成简洁有力的总结。"
                    },
                    {
                        "role": "user",
                        "content": f"""请对以下聊天记录进行总结，重点关注：
                        1. 主要讨论的话题
                        2. 重要的结论决定
                        3. 值得注意的观点
                        4. 如果有问题被提出，总结这些问题

                        聊天记录：
                        {chat_text}
                        """
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": 0.7
            }
            
            print(f"发送请求到豆包AI: {self.base_url}")
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30  # 添加超时设置
            )
            
            print(f"豆包AI响应状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    raise RuntimeError("豆包AI返回结果格式错误")
            else:
                error = response.json().get("error", {})
                error_msg = error.get("message", "未知错误")
                print(f"豆包AI错误响应: {response.text}")
                raise RuntimeError(f"豆包AI调用失败: {error_msg}")
                
        except requests.exceptions.Timeout:
            print("豆包AI请求超时")
            raise RuntimeError("请求超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            print(f"豆包AI网络请求错误: {str(e)}")
            raise RuntimeError(f"网络请求错误: {str(e)}")
        except Exception as e:
            print(f"豆包AI分析失败: {str(e)}")
            raise RuntimeError(f"分析失败: {str(e)}")