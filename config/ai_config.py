"""AI模型配置"""

AI_CONFIGS = {
    "openai": {
        "name": "OpenAI GPT-3.5",
        "api_key": "sk-XSfRztQaVch68gGtxQnn1dEhtBgYqZu5fz3Mtct1likGpv1x",  # 替换为实际的key
        "base_url": "https://api.chatanywhere.tech",
        "model": "gpt-3.5-turbo",
        "max_tokens": 2000
    },
    "doubao": {
        "name": "豆包AI",
        "api_key": "1d93fe5f-af7f-435f-8a36-8466d98a4ea0",  # 替换为实际的key
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
    
    @staticmethod
    def list_supported_ais() -> list:
        """获取支持的AI列表"""
        return list(AI_CONFIGS.keys())
    
    @staticmethod
    def update_config(ai_type: str, **kwargs):
        """更新AI配置"""
        if ai_type not in AI_CONFIGS:
            raise ValueError(f"不支持的AI类型: {ai_type}")
        AI_CONFIGS[ai_type].update(kwargs) 