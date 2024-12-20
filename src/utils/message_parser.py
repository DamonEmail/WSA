import re
import blackboxprotobuf
from typing import Dict, Any
import sqlite3

def get_BytesExtra(BytesExtra: bytes) -> Dict:
    """解析BytesExtra数据"""
    BytesExtra_message_type = {
        "1": {
            "type": "message",
            "message_typedef": {
                "1": {"type": "int", "name": ""},
                "2": {"type": "int", "name": ""}
            },
            "name": "1"
        },
        "3": {
            "type": "message",
            "message_typedef": {
                "1": {"type": "int", "name": ""},
                "2": {"type": "str", "name": ""}
            },
            "name": "3"
        }
    }
    
    if BytesExtra is None or not isinstance(BytesExtra, bytes):
        return None
    try:
        deserialize_data, message_type = blackboxprotobuf.decode_message(BytesExtra, BytesExtra_message_type)
        return deserialize_data
    except Exception as e:
        return None

def parse_message_content(msg_type: int, sub_type: int, content: str) -> str:
    """解析不同类型的消息内容"""
    try:
        if msg_type == 1:  # 文本消息
            return content
        elif msg_type == 3:  # 图片消息
            return "[图片]"
        elif msg_type == 34:  # 语音消息
            return "[语音]"
        elif msg_type == 43:  # 视频消息
            return "[视频]"
        elif msg_type == 47:  # 动画表情
            if "<emoji" in content:
                return "[动画表情]"
            return "[表情]"
        elif msg_type == 49:  # 分享消息
            if sub_type == 5:  # 卡片式链接
                return "[分享] " + content.split('<title>')[1].split('</title>')[0] if '<title>' in content else "[分享链接]"
            elif sub_type == 19:  # 合并转发的聊天记录
                return "[聊天记录]"
            elif sub_type == 2000:  # 转账消息
                return "[转账]"
            return "[文件]"
        elif msg_type == 50:  # 语音/视频通话
            return "[通话]"
        elif msg_type == 10000:  # 系统消息
            return content
        else:
            return f"[未知消息类型({msg_type}-{sub_type})]"
    except:
        return content

def get_sender_name(user_id: str, contact_db: str) -> str:
    """获取发送者名称"""
    try:
        conn = sqlite3.connect(contact_db)
        cursor = conn.cursor()
        
        # 精确查找用户
        cursor.execute("""
            SELECT UserName, NickName, Remark, Type, Alias 
            FROM Contact
            WHERE UserName = ?
        """, (user_id,))
        user = cursor.fetchone()
        
        if user:
            # 优先级：备注名 > 昵称 > 微信号 > 用户ID
            display_name = user[2] or user[1] or user[4] or user[0]
            return display_name
            
        # 如果找不到，使用美化显示
        if user_id.startswith('wxid_'):
            return f"微信用户({user_id})"
            
        return user_id
        
    except sqlite3.Error as e:
        print(f"查询用户信息出错: {str(e)}")
        return "未知用户"
    finally:
        cursor.close()
        conn.close() 