import sqlite3
import os
import time
from ..utils.config import Config
from ..utils.message_parser import get_BytesExtra, get_sender_name
from datetime import datetime, timedelta, date

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
            print(f"找到联系人数据库：{self.contact_db}")
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
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(MSG)")
            columns = cursor.fetchall()
            print(f"\n===== MSG表结构 =====")
            for col in columns:
                print(f"列名: {col[1]}, 类型: {col[2]}")
            print("====================")
            
            return True
        except sqlite3.Error as e:
            raise ValueError(f"数据库验证失败: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def get_chatroom_id(self, room_name: str) -> list:
        """根据群名获取群ID
        Args:
            room_name: 群名称（支持部分匹配）
        Returns:
            List[Tuple[str, str]]: [(群ID, 数据库路径), ...]
        """
        print(f"\n尝试查找群：{room_name}")
        found_groups = []
        
        try:
            # 1. 先从联系人数据库查找
            conn = sqlite3.connect(self.contact_db)
            cursor = conn.cursor()
            
            # 查找匹配的群
            cursor.execute("""
                SELECT UserName, NickName, Remark 
                FROM Contact 
                WHERE (NickName LIKE ? OR Remark LIKE ?) 
                AND Type = 2  -- 群聊类型
                ORDER BY NickName
            """, (f"%{room_name}%", f"%{room_name}%"))
            
            groups = cursor.fetchall()
            print(f"找到 {len(groups)} 个可能匹配的群聊")
            
            # 2. 遍历每个群，找到所有包含其消息的数据库
            for group in groups:
                chatroom_id = group[0]  # UserName 作为群ID
                chatroom_name = group[2] or group[1]  # 优先使用备注名
                
                # 在每个消息数据库中查找
                for msg_db in self.msg_dbs:
                    try:
                        msg_conn = sqlite3.connect(msg_db)
                        msg_cursor = msg_conn.cursor()
                        
                        # 验证群ID是否在此数据库中
                        msg_cursor.execute("""
                            SELECT COUNT(*) FROM MSG 
                            WHERE StrTalker = ? 
                            LIMIT 1
                        """, (chatroom_id,))
                        
                        if msg_cursor.fetchone()[0] > 0:
                            found_groups.append((chatroom_id, msg_db))
                            print(f"✓ 群「{chatroom_name}」({chatroom_id}) 的消息在数据库: {msg_db}")
                            # 移除这里的 break，继续查找其他数据库
                    
                    except sqlite3.Error as e:
                        print(f"检查数据库 {msg_db} 时出错: {str(e)}")
                    finally:
                        msg_cursor.close()
                        msg_conn.close()
            
            return found_groups
            
        except sqlite3.Error as e:
            print(f"查询群ID时出错: {str(e)}")
            raise ValueError(f"查询群ID失败: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    
    def get_user_info(self, user_id: str) -> str:
        """获取用户信息，优先使用缓存"""
        # 如果已经在缓存中，直接返回
        if user_id in self.user_cache:
            return self.user_cache[user_id]
            
        try:
            conn = sqlite3.connect(self.contact_db)
            cursor = conn.cursor()
            
            # 精确查找户
            cursor.execute("""
                SELECT UserName, NickName, Remark, Type, Alias 
                FROM Contact
                WHERE UserName = ?
            """, (user_id,))
            user = cursor.fetchone()
            
            if user:
                # 优先级：备注名 > 昵称 > 号 > 用户ID
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
            
            # 查询聊天记录
            cursor.execute("""
                SELECT CreateTime, StrContent, Type, IsSender, BytesExtra
                FROM MSG 
                WHERE StrTalker = ? 
                ORDER BY CreateTime DESC
            """, (chatroom_id,))
            
            records = cursor.fetchall()
            print(f"数据库中共找到 {len(records)} 条聊天记录")
            
            # 打印最近一条消息的信息
            if records:
                latest_record = records[0]
                latest_time = datetime.fromtimestamp(latest_record[0])
                latest_content = latest_record[1]
                # print(f"\n最近一条消息信息:")
                # print(f"时间: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
                # print(f"内容: {latest_content[:100]}..." if len(latest_content) > 100 else f"内容: {latest_content}")
                # print(f"消息类型: {latest_record[2]}")
                # print("=" * 50)
            
            # 在内存中筛选时间范围
            filtered_records = []
            for record in records:
                msg_time = datetime.fromtimestamp(record[0])
                msg_date = msg_time.date()
                days_diff = (target_date - msg_date).days
                if 0 <= days_diff < days:  # 在指定天数范围内
                    filtered_records.append(record)
            
            print(f"数据库中共找到 {len(records)} 条记录，时间范围内有 {len(filtered_records)} 条")
            
            # 如果没有在间范围内找到记录，显示时间范围信息
            if not filtered_records and records:
                earliest_time = datetime.fromtimestamp(records[-1][0])
                print(f"\n消息时间范围:")
                print(f"最早消息: {earliest_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"最近消息: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"查询范围: {start_date.strftime('%Y-%m-%d')} 至 {target_date.strftime('%Y-%m-%d')}")
            
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
    
    def analyze_group(self, group_name: str, start_date: date = None, end_date: date = None):
        """分析群聊记录"""
        try:
            # 参数验证
            if not start_date or not end_date:
                start_date = end_date = date.today()
            
            if end_date < start_date:
                raise ValueError("结束日期不能早于开始日期")
            
            # 转换日期为时间戳（确保包含完整的日期）
            start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())  # 当天 00:00:00
            end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())    # 当天 23:59:59
            
            print(f"\n===== 查询时间范围 =====")
            print(f"开始时间: {datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"结束时间: {datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            print("=====================")
            
            # 1. 获取所有匹配的群ID
            found_groups = self.get_chatroom_id(group_name)
            if not found_groups:
                raise ValueError(f"找不到名称包含「{group_name}」的群聊")
            
            print(f"找到 {len(found_groups)} 个匹配的群聊")
            
            # 2. 获取所有群天记录
            all_records = []
            total_messages = 0
            total_text_messages = 0
            
            for chatroom_id, msg_db in found_groups:
                try:
                    sql = """
                        SELECT CreateTime, StrContent, Type, IsSender, BytesExtra
                        FROM MSG 
                        WHERE StrTalker = ? 
                        AND CreateTime BETWEEN ? AND ?
                        ORDER BY CreateTime DESC
                    """
                    
                    conn = sqlite3.connect(msg_db)
                    cursor = conn.cursor()
                    
                    # 先检查一下最新消息
                    test_sql = """
                        SELECT CreateTime, StrContent, Type, IsSender, BytesExtra
                        FROM MSG 
                        WHERE StrTalker = ? 
                        ORDER BY CreateTime DESC
                        LIMIT 1
                    """
                    
                    # 打印调试信息
                    print(f"\n===== 调试信息 =====")
                    print(f"数据库: {msg_db}")
                    print(f"群ID: {chatroom_id}")
                    print(f"时间范围: {start_timestamp} ~ {end_timestamp}")
                    
                    # 先测试最新消息
                    cursor.execute(test_sql, (chatroom_id,))
                    latest = cursor.fetchone()
                    if latest:
                        latest_time = datetime.fromtimestamp(latest[0])
                        print(f"最新消息时间: {latest_time}")
                        print(f"最新消息内容: {latest[1][:100]}")
                    
                    # 执行实际查询
                    cursor.execute(sql, (chatroom_id, start_timestamp, end_timestamp))
                    records = cursor.fetchall()
                    print(f"查询到记录数: {len(records)}")
                    print("===================")
                    
                    if records:
                        print(f"\n处理数据库: {msg_db}")
                        print(f"• 原始记录: {len(records):,} 条")
                        
                        # 记录时间范围
                        earliest = datetime.fromtimestamp(records[-1][0])
                        latest = datetime.fromtimestamp(records[0][0])
                        print(f"• 时间范围: {earliest.strftime('%Y-%m-%d %H:%M:%S')} ~ {latest.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 格式化消息记录
                        text_count = 0
                        for timestamp, content, msg_type, is_sender, bytes_extra in records:
                            total_messages += 1
                            if msg_type == 1:  # 只处理文本消息
                                text_count += 1
                                total_text_messages += 1
                                try:
                                    sender = "我" if is_sender else self._get_sender_info(bytes_extra)
                                    all_records.append({
                                        'create_time': timestamp,
                                        'content': content,
                                        'sender': sender,
                                        'is_sender': is_sender,
                                        'bytes_extra': bytes_extra
                                    })
                                except Exception as e:
                                    print(f"处理消息失败: {str(e)}")
                                    continue
                        
                        print(f"• 文本消息: {text_count:,} 条")
                
                except Exception as e:
                    print(f"获取群 {chatroom_id} 的记录失败: {str(e)}")
                    continue
                finally:
                    cursor.close()
                    conn.close()
            
            # 3. 按时间排序
            all_records.sort(key=lambda x: x['create_time'], reverse=True)
            
            # 4. 检查结果
            if not all_records:
                date_range = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
                if total_messages == 0:
                    raise ValueError(
                        f"群「{group_name}」在 {date_range} 期间没有任何消息记录。\n"
                        f"请尝试选择更长的时���范围。"
                    )
                else:
                    raise ValueError(
                        f"群「{group_name}」在 {date_range} 期间共有 {total_messages} 条消息，\n"
                        f"但都是非文本消息（图片、表情等），无法进行分析。\n"
                        f"请尝试选择更长的时间范围。"
                    )
            
            print(f"\n处理完成:")
            print(f"• 消息数: {total_messages:,} 条")
            print(f"• 文本消息: {total_text_messages:,} 条")
            print(f"• 有效消息: {len(all_records):,} 条")
            print(f"• 时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            
            return all_records
            
        except ValueError as e:
            raise
        except Exception as e:
            print(f"分析群聊记录出错: {str(e)}")
            raise ValueError(
                f"分析群「{group_name}」的聊天记录时出错。\n"
                f"错误信息：{str(e)}\n"
                f"请确认群名称是否正确，或尝试重新解密数据库。"
            )
    
    def _get_sender_info(self, bytes_extra) -> str:
        """从 BytesExtra 中获取发送者信息"""
        try:
            bytes_extra_dict = get_BytesExtra(bytes_extra)
            if bytes_extra_dict and '3' in bytes_extra_dict:
                sender_id = bytes_extra_dict['3'][0]['2']
                return self.get_user_info(sender_id)
            return "未知用户"
        except Exception as e:
            print(f"解析发送者信息失败: {str(e)}")
            return "未知用户"