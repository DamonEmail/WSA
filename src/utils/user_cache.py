import sqlite3
from typing import Dict

class UserCache:
    """用户信息缓存"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.cache = {}  # 用户ID到用户信息的映射缓存
    
    def get_user_info(self, user_id: str) -> str:
        """获取用户信息，优先使用缓存"""
        if user_id in self.cache:
            return self.cache[user_id]
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT UserName, NickName, Remark, Type, Alias 
                    FROM Contact
                    WHERE UserName = ?
                """, (user_id,))
                user = cursor.fetchone()
                
                if user:
                    # 优先级：备注名 > 昵称 > 微信号 > 用户ID
                    display_name = user[2] or user[1] or user[4] or user[0]
                    self.cache[user_id] = display_name
                    return display_name
                    
                # 如果找不到，尝试不带@的匹配
                if '@' in user_id:
                    wxid = user_id.split('@')[0]
                    cursor.execute("""
                        SELECT UserName, NickName, Remark, Type, Alias 
                        FROM Contact
                        WHERE UserName LIKE ?
                    """, (f"%{wxid}%",))
                    user = cursor.fetchone()
                    if user:
                        display_name = user[2] or user[1] or user[4] or user[0]
                        self.cache[user_id] = display_name
                        return display_name
                
                # 如果是wxid_开头，使用美化显示
                if user_id.startswith('wxid_'):
                    display_name = f"微信用户({user_id})"
                    self.cache[user_id] = display_name
                    return display_name
                    
                # 都找不到，使用原始ID
                self.cache[user_id] = user_id
                return user_id
                
        except sqlite3.Error as e:
            print(f"查询用户信息出错: {str(e)}")
            return "未知用户" 