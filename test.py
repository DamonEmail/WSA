#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
from datetime import datetime
import sys
from src.utils.message_parser import get_BytesExtra

def get_latest_messages(db_dir):
    """从所有消息数据库中获取最新消息"""
    latest_messages = []
    
    # 遍历所有MSG*.db文件
    for i in range(10):  # 最多检查MSG0-MSG9
        db_path = os.path.join(db_dir, f"MSG{i}.decrypted.db")
        if not os.path.exists(db_path):
            continue
            
        print(f"\n检查数据库: {os.path.basename(db_path)}")
        print(f"文件修改时间: {datetime.fromtimestamp(os.path.getmtime(db_path))}")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取最新的消息
            cursor.execute("""
                SELECT CreateTime, StrContent, Type, IsSender, StrTalker, BytesExtra
                FROM MSG 
                WHERE Type = 1  -- 文本消息
                ORDER BY CreateTime DESC
                LIMIT 1
            """)
            
            message = cursor.fetchone()
            if message:
                create_time, content, msg_type, is_sender, talker, bytes_extra = message
                
                # 解析发送者信息
                sender = "我" if is_sender else "未知用户"
                if not is_sender and bytes_extra:
                    try:
                        bytes_extra_dict = get_BytesExtra(bytes_extra)
                        if bytes_extra_dict and '3' in bytes_extra_dict:
                            sender_id = bytes_extra_dict['3'][0]['2']
                            # 获取发送者昵称
                            cursor.execute("""
                                SELECT NickName, Remark 
                                FROM Contact 
                                WHERE UserName=?
                            """, (sender_id,))
                            user_info = cursor.fetchone()
                            if user_info:
                                sender = user_info[1] or user_info[0] or sender_id
                    except Exception as e:
                        print(f"解析发送者信息失败: {e}")
                
                latest_messages.append({
                    'db_file': f"MSG{i}.db",
                    'time': datetime.fromtimestamp(create_time),
                    'content': content,
                    'sender': sender,
                    'talker': talker,
                    'is_sender': is_sender
                })
            
            cursor.close()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"处理数据库 MSG{i}.db 时出错: {e}")
            continue
    
    return latest_messages

def get_contact_info(db_dir, talker_id):
    """获取联系人或群聊信息"""
    contact_db = os.path.join(db_dir, "MicroMsg.decrypted.db")
    if not os.path.exists(contact_db):
        return "未知"
        
    try:
        conn = sqlite3.connect(contact_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT NickName, Remark 
            FROM Contact 
            WHERE UserName=?
        """, (talker_id,))
        
        result = cursor.fetchone()
        if result:
            return result[1] or result[0] or talker_id
            
        return talker_id
        
    except sqlite3.Error as e:
        print(f"查询联系人信息失败: {e}")
        return talker_id
    finally:
        cursor.close()
        conn.close()

def main():
    # 使用项目目录下的database文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(current_dir, "database")
    
    if not os.path.exists(db_dir):
        print(f"错误：找不到数据库目录 {db_dir}")
        sys.exit(1)
    
    print(f"从目录 {db_dir} 中查找最新消息...")
    latest_messages = get_latest_messages(db_dir)
    
    if not latest_messages:
        print("未找到任何消息")
        return
    
    # 按时间排序
    latest_messages.sort(key=lambda x: x['time'], reverse=True)
    
    print("\n=== 各数据库最新消息 ===")
    for msg in latest_messages:
        chat_name = get_contact_info(db_dir, msg['talker'])
        print(f"\n数据库: {msg['db_file']}")
        print(f"聊天对象: {chat_name}")
        print(f"发送者: {msg['sender']}")
        print(f"时间: {msg['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"内容: {msg['content']}")
        print("-" * 50)
    
    # 显示最新的一条消息
    newest_msg = latest_messages[0]
    print("\n=== 所有数据库中最新的消息 ===")
    print(f"来自数据库: {newest_msg['db_file']}")
    print(f"聊天对象: {get_contact_info(db_dir, newest_msg['talker'])}")
    print(f"发送者: {newest_msg['sender']}")
    print(f"时间: {newest_msg['time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"内容: {newest_msg['content']}")

if __name__ == "__main__":
    main() 