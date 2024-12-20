import requests
from typing import List, Dict, Any
from ..utils.config import Config

class AIClient:
    """AI接口客户端"""
    
    def __init__(self):
        self.config = Config()
        ai_config = self.config.get_ai_config()
        self.api_key = ai_config["api_key"]
        self.base_url = f"{ai_config['base_url']}/chat/completions"
        self.model = ai_config["model"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def analyze_chat(self, messages: List[str]) -> Dict[str, Any]:
        """分析聊天记录"""
        chat_text = "\n".join(messages)
        
        try:
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
                        2. 重要的结论或决定
                        3. 值得注意的观点
                        4. 如果有问题被提出，总结这些问题

                        聊天记录：
                        {chat_text}
                        """
                    }
                ]
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "summary": result["choices"][0]["message"]["content"],
                    "status": "success"
                }
            else:
                error = response.json().get("error", {})
                print(f"AI调用失败: {error.get('message', '未知错误')}")
                return {
                    "summary": "无法生成总结",
                    "status": "error",
                    "error": error
                }
                
        except Exception as e:
            print(f"AI调用出错: {str(e)}")
            return {
                "summary": "无法生成总结",
                "status": "error",
                "error": str(e)
            } 