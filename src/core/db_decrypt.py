import os
import shutil
from typing import List, Dict
from Crypto.Cipher import AES
import sqlite3
import hashlib
import time
import hmac
import ctypes
from ..utils.config import Config

class DBDecrypt:
    """数据库解密工具"""
    
    def __init__(self, wxid: str, key: str):
        self.wxid = wxid
        # 修改密钥处理方式
        try:
            # 如果输入的是十六进制字符串
            if len(key) == 64:  # 32字节的十六进制字符串
                print(f"使用原始密钥：{key}")
                self.key = bytes.fromhex(key)
            else:
                # 如果不是，使用MD5处理
                print(f"对密钥进行MD5处理：{key}")
                self.key = hashlib.md5(key.encode()).digest()
            
            print(f"最终使用的密钥：{self.key.hex()}")
        except Exception as e:
            raise ValueError(f"密钥格式错误：{str(e)}")
        
        # 设置工作目录
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 设置原始数据库目录（存放备份的加��数据库）
        self.original_dir = os.path.join(self.base_dir, "original_dbs")
        os.makedirs(self.original_dir, exist_ok=True)
        
        # 设置解密后的数据库目录
        self.output_dir = os.path.join(self.base_dir, "database")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 获取微信文件目录
        self.wechat_files_dir = os.path.expandvars(r"%USERPROFILE%\Documents\WeChat Files")
        if not os.path.exists(self.wechat_files_dir):
            raise FileNotFoundError(f"找不到微信文件目录：{self.wechat_files_dir}")
        
        # 查找用户目录
        self.user_dir = self._find_user_dir()
        
        # 设置数据库目录
        self.msg_dir = os.path.join(self.user_dir, "Msg")
        self.multi_msg_dir = os.path.join(self.msg_dir, "Multi")

    def _find_user_dir(self) -> str:
        """查找用户目录"""
        try:
            # 存储所有有效的目录
            valid_paths = []
            
            # 遍历 WeChat Files 下的所有目录
            for dirname in os.listdir(self.wechat_files_dir):
                full_path = os.path.join(self.wechat_files_dir, dirname)
                if not os.path.isdir(full_path):
                    continue
                    
                # 检查是���存在 Msg/Multi 目录结构
                multi_path = os.path.join(full_path, "Msg", "Multi")
                if not os.path.exists(multi_path):
                    continue
                    
                # 检查是否存在 MSG*.db 文件
                has_msg_db = any(f.startswith("MSG") and f.endswith(".db") 
                               for f in os.listdir(multi_path))
                if not has_msg_db:
                    continue
                    
                # 如果目录名包含微信号，优先尝试
                if self.wxid.lower() in dirname.lower():
                    valid_paths.insert(0, full_path)  # 放在列表开头
                else:
                    valid_paths.append(full_path)
            
            if not valid_paths:
                raise FileNotFoundError("找不到包含消息数据库的目录")
            
            # 尝试每个有效目录
            for path in valid_paths:
                print(f"尝试目录: {path}")
                try:
                    # 尝试解密该目录下的数据库
                    test_db_path = os.path.join(path, "Msg", "Multi", "MSG0.db")
                    if not os.path.exists(test_db_path):
                        continue
                    
                    # 读取加密数据
                    with open(test_db_path, 'rb') as f:
                        test_data = f.read(4096)  # 只读取第一页进行测试
                    
                    # 尝试解密
                    try:
                        self.decrypt_file(test_data)
                        print(f"✅ 成功解密目录: {path}")
                        
                        try:
                            # 更新配置文件
                            config = Config()
                            config.update_user_dir(self.wxid, path)
                        except Exception as e:
                            # 即使配置更新失败，也不影响主流程
                            print(f"更新配置失败: {str(e)}")
                        
                        # 成功解密后直接返回路径
                        return path
                        
                    except Exception as e:
                        print(f"该目录解密失败: {str(e)}")
                        continue
                    
                except Exception as e:
                    print(f"尝试目录 {path} 时出错: {str(e)}")
                    continue
            
            # 所有目录都尝试失败后才抛出异常
            raise FileNotFoundError("所有可能的目录都解密失败")
                
        except Exception as e:
            raise FileNotFoundError(f"查找用户目录时出错：{str(e)}")

    def decrypt_file(self, encrypted_data: bytes) -> bytes:
        """解密数据"""
        try:
            print(f"开始解密，数据长度：{len(encrypted_data)} 字节")
            
            # 常量定义
            KEY_SIZE = 32
            DEFAULT_ITER = 64000
            DEFAULT_PAGESIZE = 4096  # 4048数据 + 16IV + 20 HMAC + 12
            SQLITE_FILE_HEADER = bytes("SQLite format 3", encoding="ASCII") + bytes(1)
            
            # 1. 获取盐值和生成密钥
            salt = encrypted_data[:16]  # 前16字节为盐
            print(f"获取到salt：{salt.hex()}")
            
            # 使用 PBKDF2 生成密钥
            key = hashlib.pbkdf2_hmac("sha1", self.key, salt, DEFAULT_ITER, KEY_SIZE)
            print(f"生成的key：{key.hex()}")
            
            # 2. 处理第一页
            page1 = encrypted_data[16:DEFAULT_PAGESIZE]  # 丢掉salt
            
            # 3. 验证MAC
            mac_salt = bytes([x ^ 0x3a for x in salt])
            mac_key = hashlib.pbkdf2_hmac("sha1", key, mac_salt, 2, KEY_SIZE)
            
            hash_mac = hmac.new(mac_key, digestmod="sha1")
            hash_mac.update(page1[:-32])
            hash_mac.update(bytes(ctypes.c_int(1)))
            
            if hash_mac.digest() != page1[-32:-12]:
                raise RuntimeError("密码错误！MAC验证失败")
            
            # 4. 解密数据
            # 分页处理
            pages = [encrypted_data[i:i+DEFAULT_PAGESIZE] 
                    for i in range(DEFAULT_PAGESIZE, len(encrypted_data), DEFAULT_PAGESIZE)]
            pages.insert(0, page1)  # 把第一页补上
            
            # 解密所有页
            decrypted_data = bytearray()
            decrypted_data.extend(SQLITE_FILE_HEADER)  # 写入SQLite文件头
            
            for page in pages:
                cipher = AES.new(key, AES.MODE_CBC, page[-48:-32])
                decrypted_page = cipher.decrypt(page[:-48])
                decrypted_data.extend(decrypted_page)
                decrypted_data.extend(page[-48:])
            
            print("解密成功！")
            return bytes(decrypted_data)
            
        except Exception as e:
            print(f"解密过程出错：{str(e)}")
            raise

    def decrypt_db(self, db_path: str) -> str:
        """解密单个数据库文件"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"找不到数据库文件：{db_path}")
        
        # 读取加密数据
        with open(db_path, 'rb') as f:
            encrypted_data = f.read()
        
        try:
            # 解密数据
            decrypted_data = self.decrypt_file(encrypted_data)
            
            # 保存解密后的文件，添加 .decrypted 后缀
            db_name = os.path.basename(db_path)
            base_name, ext = os.path.splitext(db_name)
            decrypted_name = f"{base_name}.decrypted{ext}"  # 例如: MSG0.decrypted.db
            decrypted_path = os.path.join(self.output_dir, decrypted_name)
            
            # 如果文件已存在，先尝试删除
            if os.path.exists(decrypted_path):
                try:
                    os.remove(decrypted_path)
                except Exception as e:
                    print(f"警告无法删除已存在的文件 {decrypted_path}: {str(e)}")
                    # 使用一个新的文件名
                    decrypted_name = f"{base_name}.decrypted.{int(time.time())}{ext}"
                    decrypted_path = os.path.join(self.output_dir, decrypted_name)
            
            # 写入解密后的数据
            try:
                with open(decrypted_path, 'wb') as f:
                    f.write(decrypted_data)
            except PermissionError:
                # 如果写入失败，尝试使用一个临时文件
                temp_path = os.path.join(self.output_dir, f"temp_{int(time.time())}_{decrypted_name}")
                with open(temp_path, 'wb') as f:
                    f.write(decrypted_data)
                # 然后尝试移动到目标位置
                try:
                    if os.path.exists(decrypted_path):
                        os.remove(decrypted_path)
                    os.rename(temp_path, decrypted_path)
                except:
                    # 如果移动失败，就使用临时文件
                    decrypted_path = temp_path
            
            # 验证解密后的数据库
            try:
                conn = sqlite3.connect(decrypted_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                cursor.fetchall()
                cursor.close()
                conn.close()
                return decrypted_path
            except sqlite3.Error:
                if os.path.exists(decrypted_path):
                    try:
                        os.remove(decrypted_path)
                    except:
                        pass
                raise ValueError("解密后的数据库无效")
                
        except Exception as e:
            raise RuntimeError(f"解密失败：{str(e)}")

    def decrypt_all(self, progress_callback=None):
        """解密所有数据库"""
        def log(msg):
            print(msg)  # 保留控制台完整日志
            if progress_callback:
                # 过滤不需要显示的信息
                if not any(skip in msg for skip in [
                    "-> ", "备份", r"C:\Users"
                ]):
                    progress_callback(msg)
        
        results = {}
        try:
            log("开始准备数据库...")
            
            # 0. 备份原始数据库
            original_contact_db = os.path.join(self.msg_dir, "MicroMsg.db")
            if not os.path.exists(original_contact_db):
                raise FileNotFoundError(f"找不到联系人数据库")
            
            backup_contact_path = os.path.join(self.original_dir, "MicroMsg.db")
            shutil.copy2(original_contact_db, backup_contact_path)
            
            # 聊天记录数据库
            msg_dbs_found = False
            for i in range(10):
                original_msg_db = os.path.join(self.multi_msg_dir, f"MSG{i}.db")
                if os.path.exists(original_msg_db):
                    backup_msg_path = os.path.join(self.original_dir, f"MSG{i}.db")
                    shutil.copy2(original_msg_db, backup_msg_path)
                    msg_dbs_found = True
                else:
                    break
            
            if not msg_dbs_found:
                raise FileNotFoundError("未找到任何消息数据库文件")
            
            log("开始解析数据库...")
            
            # 1. 解密联系人数据库
            try:
                decrypted_path = self.decrypt_db(backup_contact_path)
                results["MicroMsg.db"] = decrypted_path
                log(f"✅ 联系人数据库解密成功")
            except Exception as e:
                results["MicroMsg.db"] = f"解密失败：{str(e)}"
                log(f"❌ 联系人数据库解密失败：{str(e)}")
            
            # 2. 解密聊天记录数据库
            for i in range(10):
                backup_msg_db = os.path.join(self.original_dir, f"MSG{i}.db")
                if os.path.exists(backup_msg_db):
                    try:
                        decrypted_path = self.decrypt_db(backup_msg_db)
                        results[f"MSG{i}.db"] = decrypted_path
                        log(f"✅ MSG{i}.db 解密成功")
                    except Exception as e:
                        results[f"MSG{i}.db"] = f"解密失败：{str(e)}"
                        log(f"❌ MSG{i}.db 解密失败：{str(e)}")
                else:
                    break
            
            if not results:
                raise RuntimeError("所有数据库解密都失败了")
            
            # 添加美化的成功提示
            log("\n✨ 数据库解密成功！🎉 您现在可以进行AI分析！💡")
            
        except Exception as e:
            log(f"解密过程出错：{str(e)}")
            raise
            
        return results