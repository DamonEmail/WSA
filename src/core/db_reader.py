import sqlite3
import os
import time
from ..utils.config import Config
from ..utils.message_parser import get_BytesExtra, get_sender_name
from datetime import datetime, timedelta

class WeChatDBReader:
    def __init__(self, db_path):
        """初始化数据库读取器"""
        self.db_path = db_path
        self.msg_dbs = []  # 改为存储所有消息数据库路径
        self.contact_db = None  # MicroMsg.db 文件路径
        self.user_cache = {}  # 添加用户缓存
        
        print(f"初始化数据库读取器，路径：{db_path}")
        
        # 直接初始化数据库路径
        self._init_db_paths()
    
    def _init_db_paths(self):
        """初始化数据库文件路径"""
        print(f"正在搜索已解密的数据库文件...")
        
        # 列出目录中的所有文件
        print(f"数据库目录内容：{os.listdir(self.db_path)}")
        
        # 查找联系人数据库
        contact_db = os.path.join(self.db_path, "MicroMsg.decrypted.db")
        if os.path.exists(contact_db):
            self.contact_db = contact_db
            print(f"找���联系人数据库：{self.contact_db}")
        else:
            raise ValueError(f"找不到联系人数据库：{contact_db}")
        
        # 查找所有消息数据库
        for i in range(10):
            msg_db = os.path.join(self.db_path, f"MSG{i}.decrypted.db")
            if os.path.exists(msg_db):
                self.msg_dbs.append(msg_db)
                print(f"找到消息数据库：{msg_db}")
        
        if not self.msg_dbs:
            raise ValueError("未找到任何消息数据库文件")
    
    def _verify_db_file(self, db_path):
        """验证数据库文件是否可用"""
        if not os.path.exists(db_path):
            raise ValueError(f"数据库文件不存在：{db_path}")
            
        # 尝试打开数据库
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"数据库 {db_path} 中的表：{tables}")  # 调试信息
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            raise ValueError(f"无法打开数据库 {db_path}：{str(e)}")
    
    def get_chatroom_id(self, room_name):
        """根据群名获取群ID
        
        Returns:
            list: [(chatroom_id, msg_db), ...] 所有匹配的群ID和对应的数据库路径
        """
        print(f"尝试查找群：{room_name}")
        
        if not self.msg_dbs:
            raise ValueError("未找到消息数据库")
        
        # 存储所有找到的群ID和对应的数据库
        found_groups = []
        
        # 遍历所有消息数据库查找群
        for msg_db in self.msg_dbs:
            cursor = sqlite3.connect(msg_db).cursor()
            
            try:
                # 1. 获取所有群聊ID
                cursor.execute("""
                    SELECT DISTINCT StrTalker 
                    FROM MSG 
                    WHERE StrTalker LIKE '%chatroom'
                """)
                chatrooms = cursor.fetchall()
                print(f"在数据库 {msg_db} 中找到 {len(chatrooms)} 个群聊")
                
                # 2. 先尝试从系统消息中查找
                for room_id in chatrooms:
                    room_id = room_id[0]
                    cursor.execute("""
                        SELECT StrContent 
                        FROM MSG 
                        WHERE StrTalker = ? 
                        AND Type = 10000
                        AND StrContent LIKE ?
                    """, (room_id, f"%{room_name}%"))
                    result = cursor.fetchone()
                    if result:
                        print(f"在数据库 {msg_db} 的系统消息中找到群: {room_name}")
                        found_groups.append((room_id, msg_db))
                        continue  # 继续搜索其他群
                    
                    # 3. 尝试从普通消息中查找
                    cursor.execute("""
                        SELECT StrContent 
                        FROM MSG 
                        WHERE StrTalker = ? 
                        AND StrContent LIKE ?
                        LIMIT 1
                    """, (room_id, f"%{room_name}%"))
                    result = cursor.fetchone()
                    if result:
                        print(f"在数据库 {msg_db} 的消息内容中找到群: {room_name}")
                        found_groups.append((room_id, msg_db))
                
            finally:
                cursor.close()
        
        if not found_groups:
            raise ValueError(f"未找到群「{room_name}」")
        
        # 如果找到多个匹配的群，打印信息
        if len(found_groups) > 1:
            print(f"找到 {len(found_groups)} 个匹配的群:")
            for group_id, db in found_groups:
                print(f"- 群ID: {group_id}, 数据库: {db}")
        
        # 返回所有找到的群
        return found_groups
    
    def get_user_info(self, user_id: str) -> str:
        """获取用户信息，优先使用缓存"""
        # 如果已经在缓存中，直接返回
        if user_id in self.user_cache:
            return self.user_cache[user_id]
            
        try:
            conn = sqlite3.connect(self.contact_db)
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
                self.user_cache[user_id] = display_name
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
                    self.user_cache[user_id] = display_name
                    return display_name
            
            # 如果是wxid_开头，使用美化显示
            if user_id.startswith('wxid_'):
                display_name = f"微信用户({user_id})"
                self.user_cache[user_id] = display_name
                return display_name
                
            # 都找不到，用原始ID
            self.user_cache[user_id] = user_id
            return user_id
            
        except sqlite3.Error as e:
            print(f"查询用户信息出错: {str(e)}")
            return "未知用户"
        finally:
            cursor.close()
            conn.close()
    
    def get_chat_records(self, chatroom_info, days=1):
        """获取指定群的聊天记录"""
        chatroom_id, msg_db = chatroom_info
        print(f"尝试获取群 {chatroom_id} 的聊天记录，从数据库：{msg_db}")
        
        # 计算目标日期
        current_time = int(time.time())
        target_date = datetime.fromtimestamp(current_time).date()
        start_date = target_date - timedelta(days=days)
        
        print(f"===== 时间范围 =====")
        print(f"开始日期: {start_date}")
        print(f"结束日期: {target_date}")
        print(f"时间跨度: {days} 天")
        print("==================")
        
        # 验证数据库文件
        self._verify_db_file(msg_db)
        
        conn = sqlite3.connect(msg_db)
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='MSG'")
            if not cursor.fetchone():
                raise ValueError("MSG表不存在")
            
            # 获取表结构
            cursor.execute("PRAGMA table_info(MSG)")
            columns = cursor.fetchall()
            # print(f"MSG表结构：{columns}")
            
            # 查询聊天记录 - 不使用时间过滤，在内存中筛选
            cursor.execute("""
                SELECT CreateTime, StrContent, Type, IsSender, BytesExtra
                FROM MSG 
                WHERE StrTalker = ? 
                ORDER BY CreateTime DESC
            """, (chatroom_id,))
            
            records = cursor.fetchall()
            print(f"数据库中共找到 {len(records)} 条聊天记录")
            
            # 在内��中筛选时间范围
            filtered_records = []
            for record in records:
                msg_time = datetime.fromtimestamp(record[0])
                msg_date = msg_time.date()
                days_diff = (target_date - msg_date).days
                if 0 <= days_diff < days:  # 在指定天数范围内
                    filtered_records.append(record)
            
            print(f"数据库中共找到 {len(records)} 条记录，时间范围内有 {len(filtered_records)} 条")
            
            # 格式化消息记录
            messages = []
            for timestamp, content, msg_type, is_sender, bytes_extra in filtered_records:
                # 只处理文本消息
                if msg_type == 1:  # 文本消息类型
                    try:
                        # 获取发送者信息
                        if is_sender:
                            sender = "我"
                        else:
                            # 从 BytesExtra 中解析发送者信息
                            bytes_extra_dict = get_BytesExtra(bytes_extra)
                            if bytes_extra_dict and '3' in bytes_extra_dict:
                                sender_id = bytes_extra_dict['3'][0]['2']
                                sender = self.get_user_info(sender_id)
                            else:
                                sender = "未知用户"
                    except Exception as e:
                        print(f"获取发送者信息失败: {str(e)}")
                        sender = "未知用户"
                    
                    messages.append({
                        'create_time': timestamp,
                        'content': content,
                        'sender': sender,
                        'is_sender': is_sender,
                        'bytes_extra': bytes_extra
                    })
            
            return messages
            
        finally:
            cursor.close()
            conn.close()
    
    def analyze_group(self, group_name, days=1):
        """分析群聊记录"""
        try:
            # 1. 获取所有匹配的群ID
            found_groups = self.get_chatroom_id(group_name)
            
            # 2. 获取所有群的聊天记录
            all_records = []
            total_messages = 0  # 记录总消息数
            
            for chatroom_id, msg_db in found_groups:
                try:
                    records = self.get_chat_records((chatroom_id, msg_db), days=days)
                    if records:
                        print(f"从数据库 {msg_db} 中获取到 {len(records)} 条记录")
                        all_records.extend(records)
                        total_messages += len(records)
                except Exception as e:
                    print(f"获取群 {chatroom_id} 的记录失败: {str(e)}")
                    continue
            
            # 3. 按时间排序 - 修改这里：使用 create_time 而不是 time
            all_records.sort(key=lambda x: x['create_time'], reverse=True)
            
            print(f"合并后共有 {len(all_records)} 条记录")
            
            if not all_records:
                # 根据不同情况给出不同的提示
                if total_messages == 0:
                    raise ValueError(
                        f"群「{group_name}」在最近 {days} 天内没有任何消息记录。\n"
                        f"请尝试选择更长的时间范围，或确认群名称是否正确。"
                    )
                else:
                    raise ValueError(
                        f"群「{group_name}」在最近 {days} 天内的消息都是非文本消息（图片、表情等），"
                        f"无法进行分析。\n请尝试选择更长的时间范围。"
                    )
            
            return all_records
            
        except ValueError as e:
            # 直接抛出 ValueError，保持原有的错误信息
            raise
        except Exception as e:
            print(f"分析群聊记录出错: {str(e)}")
            raise ValueError(
                f"分析群「{group_name}」的聊天记录时出错：{str(e)}\n"
                f"请确认群名称是否正确，或尝试重新解密数据库。"
            )