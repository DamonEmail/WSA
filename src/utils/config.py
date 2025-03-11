import os
import json
from typing import Dict, Any
from datetime import datetime
import shutil

class Config:
    """配置管理类"""
    
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        self.ai_config_path = os.path.join(self.config_dir, "ai_config.json")
        self.decrypt_config_path = os.path.join(self.config_dir, "decrypt_config.json")
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载AI配置
        if not os.path.exists(self.ai_config_path):
            self._create_default_ai_config()
        with open(self.ai_config_path, 'r', encoding='utf-8') as f:
            self.ai_config = json.load(f)
            
        # 加载解密配置
        if not os.path.exists(self.decrypt_config_path):
            self._create_default_decrypt_config()
        with open(self.decrypt_config_path, 'r', encoding='utf-8') as f:
            self.decrypt_config = json.load(f)
    
    def _create_default_ai_config(self):
        """创建默认AI配置"""
        default_config = {
            "doubao": {
                "name": "豆包AI",
                "api_key": "1d93fe5f-af7f-435f-8a36-8466d98a4ea0",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "ep-20241219150823-d5gbj"
            }
        }
        
        with open(self.ai_config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def _create_default_decrypt_config(self):
        """创建默认解密配置"""
        default_config = {
            "last_wxid": "",
            "wechat_info": {},  # 存储每个微信号的信息
            "wechat_dir": os.path.expandvars(r"%USERPROFILE%\Documents\WeChat Files")
        }
        with open(self.decrypt_config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        self.decrypt_config = default_config
    
    def save_decrypt_info(self, wxid: str, version: str, key: str):
        """保存解密信息"""
        self.decrypt_config["last_wxid"] = wxid
        self.decrypt_config["wechat_info"][wxid] = {
            "version": version,
            "key": key,
            "last_decrypt": "",  # 最后一次解密时间
            "db_dir": os.path.join(self.decrypt_config["wechat_dir"], wxid),
            "decrypted_dbs": {}  # 存储解密后的数据库文件路径
        }
        
        with open(self.decrypt_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.decrypt_config, f, ensure_ascii=False, indent=2)
    
    def update_decrypted_dbs(self, wxid, decrypted_dbs):
        """更新已解密的数据库信息"""
        if wxid not in self.decrypt_config:
            return
        
        # 只保存验证成功的数据库路径
        valid_dbs = {
            name: path 
            for name, path in decrypted_dbs.items() 
            if not path.startswith("解密失败")
        }
        
        self.decrypt_config[wxid]["decrypted_dbs"] = valid_dbs
        self.save_config()
    
    def get_decrypt_info(self, wxid: str = None) -> Dict[str, Any]:
        """获取解密信息"""
        if not wxid:
            wxid = self.decrypt_config["last_wxid"]
        return self.decrypt_config["wechat_info"].get(wxid, {})
    
    def get_wechat_dir(self) -> str:
        """获取微信文件目录"""
        wechat_dir = self.decrypt_config["wechat_dir"]
        if not os.path.exists(wechat_dir):
            raise FileNotFoundError(f"找不到微信文件目录：{wechat_dir}")
        return wechat_dir
    
    def get_user_db_dir(self, wxid: str) -> str:
        """获取用户的数据库目录"""
        user_dir = os.path.join(self.get_wechat_dir(), wxid)
        if not os.path.exists(user_dir):
            raise FileNotFoundError(f"找不到用户目录：{user_dir}")
        return user_dir
    
    def get_ai_config(self, ai_type: str = "doubao") -> Dict[str, Any]:
        """获取AI配置"""
        if ai_type not in self.ai_config:
            raise ValueError(f"不支持的AI类型: {ai_type}")
        return self.ai_config[ai_type]
    
    def update_ai_config(self, ai_type: str, **kwargs):
        """更新AI配置"""
        if ai_type not in self.ai_config:
            raise ValueError(f"不支持的AI类型: {ai_type}")
        self.ai_config[ai_type].update(kwargs)
        
        with open(self.ai_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.ai_config, f, ensure_ascii=False, indent=2) 
    
    def update_user_dir(self, wxid: str, user_dir: str):
        """更新用户目录配置"""
        if "wechat_info" not in self.decrypt_config:
            self.decrypt_config["wechat_info"] = {}
        
        if wxid not in self.decrypt_config["wechat_info"]:
            self.decrypt_config["wechat_info"][wxid] = {}
        
        # 获取真实的目录名（而不是用户输入的微信号）
        real_dir = os.path.basename(user_dir)
        parent_dir = os.path.dirname(user_dir)
        
        # 使用真实的目录路径
        self.decrypt_config["wechat_info"][wxid]["db_dir"] = os.path.join(parent_dir, real_dir)
        self.save_decrypt_config()
    
    def save_decrypt_config(self):
        """保存解密配置到文件"""
        try:
            with open(self.decrypt_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.decrypt_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败：{str(e)}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.decrypt_config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.decrypt_config[key] = value
    
    def save(self):
        """保存配置"""
        try:
            with open(self.decrypt_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.decrypt_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")