import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from datetime import datetime
import os
import re
from ..utils.ai_client import OpenAIClient, DouBaoClient
from src.core.db_reader import WeChatDBReader
from src.utils.config import Config
from src.core.wx_decrypt import WeChatDecrypt

class WeChatAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("微信群聊分析工具")
        self.root.geometry("800x700")
        
        # 初始化变量
        self.ai_type = tk.StringVar(value="openai")
        self.wxid = tk.StringVar()
        self.group_name = tk.StringVar()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill="both", expand=True)
        
        # 1. 创建数据库解密区域
        self.setup_decrypt_frame()
        
        # 2. 创建分析区域（但不显示）
        self.create_analysis_frame()
        self.analysis_frame.pack_forget()  # 初始时隐藏
        
        # 检查是否有可用的解密数据库
        self.check_decrypted_dbs()
    
    def setup_decrypt_frame(self):
        """设置解密界面"""
        self.decrypt_frame = ttk.LabelFrame(self.main_frame, text="数据库解密", padding="10")
        self.decrypt_frame.pack(fill="x", padx=10, pady=5)
        
        # 微信号输入区域
        input_frame = ttk.Frame(self.decrypt_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # 左侧：微信号输入
        left_frame = ttk.Frame(input_frame)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="微信号:").pack(side=tk.LEFT)
        self.wxid = tk.StringVar()
        ttk.Entry(left_frame, textvariable=self.wxid, width=30).pack(side=tk.LEFT, padx=5)
        
        # 右侧：按钮区
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.key_button = ttk.Button(button_frame, text="获取密钥", command=self.get_key)
        self.key_button.pack(side=tk.LEFT, padx=5)
        
        self.decrypt_button = ttk.Button(button_frame, text="解密数据库", command=self.decrypt_db, state='disabled')
        self.decrypt_button.pack(side=tk.LEFT, padx=5)
        
        # 提示信息
        ttk.Label(input_frame, 
                 text="注意：请确保微信已经登录",
                 foreground="red").pack(side=tk.LEFT, padx=10)
        
        # 显示信息
        info_frame = ttk.LabelFrame(self.decrypt_frame, text="当前信息", padding="5")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        # 微信版本
        version_frame = ttk.Frame(info_frame)
        version_frame.pack(fill="x", pady=2)
        ttk.Label(version_frame, text="微信版本:").pack(side=tk.LEFT)
        self.version_label = ttk.Label(version_frame, text="未检测")
        self.version_label.pack(side=tk.LEFT, padx=5)
        
        # 数据库密钥
        key_frame = ttk.Frame(info_frame)
        key_frame.pack(fill="x", pady=2)
        ttk.Label(key_frame, text="数据库密钥:").pack(side=tk.LEFT)
        self.key_label = ttk.Label(key_frame, text="未获取")
        self.key_label.pack(side=tk.LEFT, padx=5)
        
        # 已解密数据库
        dir_frame = ttk.Frame(info_frame)
        dir_frame.pack(fill="x", pady=2)
        ttk.Label(dir_frame, text="已解密数据库:").pack(side=tk.LEFT)
        self.dir_label = ttk.Label(dir_frame, text="未解密")
        self.dir_label.pack(side=tk.LEFT, padx=5)
    
    def get_key(self):
        """获取密钥"""
        wxid = self.wxid.get().strip()
        if not wxid:
            self.show_message("错误", "请输入微信号！", "error")
            return
            
        try:
            # 禁用按钮并显示加载状态
            self.key_button.configure(text="获取中...", state='disabled')
            
            # 在新线程中运行，避免界面卡死
            def run_decrypt():
                try:
                    decrypter = WeChatDecrypt()
                    version, key = decrypter.get_key(wxid)
                    
                    # 更新界面
                    self.root.after(0, lambda: self.version_label.config(text=version))
                    self.root.after(0, lambda: self.key_label.config(text=key))
                    
                    # 保存密钥
                    Config().save_decrypt_info(wxid, version, key)
                    
                    # 显示成功信息并启用解密按钮
                    self.root.after(0, lambda: self.show_message("成功", "密钥获取成功！"))
                    self.root.after(0, lambda: self.decrypt_button.configure(state='normal'))
                    
                except Exception as e:
                    self.root.after(0, lambda: self.show_message("错误", f"获取密钥失败：{str(e)}", "error"))
                finally:
                    # 恢复按钮状态
                    self.root.after(0, lambda: self.key_button.configure(text="获取密钥", state='normal'))
            
            thread = threading.Thread(target=run_decrypt)
            thread.start()
            
        except Exception as e:
            self.key_button.configure(text="获取密钥", state='normal')
            self.show_message("错误", f"获取密钥失败：{str(e)}")
    
    def decrypt_db(self):
        """解密数据库"""
        if not self.wxid.get():
            self.show_message("错误", "请先获取密钥！", "error")
            return
        
        try:
            # 禁用按钮并显示加载状态
            self.decrypt_button.configure(text="解密中...", state='disabled')
            
            # 创建进度弹窗
            progress_dialog = DecryptProgressDialog(self.root)
            
            # 在新线程中运行
            def run_decrypt():
                error_msg = None
                try:
                    config = Config()
                    info = config.get_decrypt_info(self.wxid.get())
                    
                    if not info:
                        raise RuntimeError("找不到钥信息，请先获取密钥！")
                    
                    from ..core.db_decrypt import DBDecrypt
                    decrypter = DBDecrypt(
                        self.wxid.get(),
                        info["key"]
                    )
                    
                    # 更新进度日志
                    progress_dialog.append_log("开始解密数据库...")
                    results = decrypter.decrypt_all(progress_callback=progress_dialog.append_log)
                    
                    # 统计结果
                    success_count = sum(1 for v in results.values() if not v.startswith("解密失败"))
                    total_count = len(results)
                    
                    # 显示结果
                    result_text = f"数据库解密完成 ({success_count}/{total_count})：\n\n"
                    for db, path in results.items():
                        if path.startswith("解密失败"):
                            result_text += f"❌ {db}: {path}\n"
                        else:
                            result_text += f"✅ {db}\n"
                    
                    # 完成解密，显示最终结果
                    progress_dialog.complete(result_text)
                    
                    # 更新配置
                    config.update_decrypted_dbs(self.wxid.get(), results)
                    
                    # 显示结果
                    self.root.after(0, lambda: self.show_message("完成", result_text))
                    
                    # 更新解密界面的显示
                    if results:
                        db_names = ", ".join(results.keys())
                        print(f"更新显示: {db_names}")
                        self.root.after(0, lambda names=db_names: self.dir_label.config(
                            text=names,
                            foreground="green"
                        ))
                        # 显示分析区域
                        self.root.after(0, lambda: self.analysis_frame.pack(
                            fill="both", expand=True, padx=10, pady=5
                        ))
                    else:
                        print("没有成功解密的数据库")
                        self.root.after(0, lambda: self.dir_label.config(
                            text="解密失败",
                            foreground="red"
                        ))
                        # 隐藏分析区域
                        self.root.after(0, self.analysis_frame.pack_forget)
                    
                except Exception as e:
                    error_msg = str(e)
                    progress_dialog.complete(f"解密失败：{error_msg}")
                    self.root.after(0, lambda msg=error_msg: self.show_message("错误", f"解密过程出错：{msg}", "error"))
                    self.root.after(0, lambda: self.dir_label.config(
                        text="解密出错",
                        foreground="red"
                    ))
                finally:
                    # 恢复按钮状态
                    self.root.after(0, lambda: self.decrypt_button.configure(text="解密数据库", state='normal'))
            
            thread = threading.Thread(target=run_decrypt)
            thread.start()
            
        except Exception as e:
            self.decrypt_button.configure(text="解密数据库", state='normal')
            self.show_message("错误", f"启动解密失败：{str(e)}")
    
    def show_main_frame(self):
        """显示主操作界面"""
        self.main_frame.pack(fill="both", expand=True)
        self.setup_main_ui()
        
    def setup_main_ui(self):
        """设置UI界面"""
        # 1. 创建数据库解密区域
        self.setup_decrypt_frame()
        
        # 2. 创建分析区域
        self.create_analysis_frame()
    
    def create_analysis_frame(self):
        """创建分析区域"""
        # 创建分析区域的容器
        self.analysis_frame = ttk.LabelFrame(self.main_frame, text="信息分析", padding="10")
        self.analysis_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 输入区域
        input_frame = ttk.Frame(self.analysis_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        # 第一行：群名输入和AI模型选择
        first_row = ttk.Frame(input_frame)
        first_row.pack(fill="x", pady=(0, 5))
        
        # 群名输入
        name_frame = ttk.Frame(first_row)
        name_frame.pack(side=tk.LEFT)
        ttk.Label(name_frame, text="群名:").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.group_name, width=30).pack(side=tk.LEFT, padx=5)
        
        # AI选择
        ai_select_frame = ttk.LabelFrame(first_row, text="AI模型", padding=(5, 0))
        ai_select_frame.pack(side=tk.LEFT, padx=(20, 0))
        ttk.Radiobutton(ai_select_frame, text="OpenAI", variable=self.ai_type, 
                        value="openai").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ai_select_frame, text="豆包AI", variable=self.ai_type, 
                        value="doubao").pack(side=tk.LEFT, padx=5)
        
        # 第二行：时间范围和分析按钮
        second_row = ttk.Frame(input_frame)
        second_row.pack(fill="x", pady=5)
        
        # 时间范围选择
        time_frame = ttk.Frame(second_row)
        time_frame.pack(side=tk.LEFT)
        ttk.Label(time_frame, text="时间范围:").pack(side=tk.LEFT)
        self.time_range = tk.StringVar(value="1")  # 默认最近一天
        ttk.Radiobutton(time_frame, text="最近24小时", variable=self.time_range, 
                        value="1").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(time_frame, text="最近3天", variable=self.time_range, 
                        value="3").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(time_frame, text="最近7天", variable=self.time_range, 
                        value="7").pack(side=tk.LEFT, padx=5)
        
        # 分析按钮
        self.analyze_button = ttk.Button(second_row, text="开始分析", command=self.start_analysis)
        self.analyze_button.pack(side=tk.LEFT, padx=(20, 0))
        
        # 输出区域
        output_frame = ttk.Frame(self.analysis_frame)
        output_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 文本框和滚动条
        text_frame = ttk.Frame(output_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.output_text = tk.Text(text_frame, height=15, width=60, wrap=tk.WORD)
        self.output_text.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        # 底部按钮区域
        bottom_frame = ttk.Frame(output_frame)
        bottom_frame.pack(fill="x", pady=(5, 0))
        
        # 复制按钮
        copy_button = ttk.Button(bottom_frame, text="复制内容", command=self.copy_summary)
        copy_button.pack(side=tk.RIGHT)
    
    def browse_db(self):
        """选择数据库目录"""
        folder = filedialog.askdirectory()
        if folder:
            self.db_path.set(folder)
    
    def start_analysis(self):
        """开始分析群消息"""
        group_name = self.group_name.get().strip()
        if not group_name:
            self.show_message("错误", "请输入群名称！", "error")
            return
        
        # 禁用按钮并显示加载状态
        self.analyze_button.configure(text="分析中...", state="disabled")
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "正在分析中，请稍候...\n")
        
        # 在新线程中运行分析
        thread = threading.Thread(target=self.run_analysis)
        thread.start()
    
    def run_analysis(self):
        """运行群消息分析"""
        try:
            # 显示简单的进度提示
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, "正在分析中...\n")
            
            print("开始分析群聊记录...")
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
            print(f"使用数据库目录：{db_path}")
            
            # 获取群名和AI类型
            ai_type = self.ai_type.get()
            group_name = self.group_name.get()
            days = int(self.time_range.get())
            print(f"分析群「{group_name}」最近 {days} 天的记录")
            
            try:
                # 创建数据库读取器
                reader = WeChatDBReader(db_path)
                
                # 获取聊天记���
                chat_records = reader.analyze_group(group_name, days=days)
                print(f"获取到 {len(chat_records)} 条聊天记录")
                
                # 准备过滤消息
                filtered_messages = []
                previous_messages = []
                previous_senders = []
                
                # 过滤和格式化消息
                for msg in chat_records:
                    content = msg['content']
                    sender = msg.get('sender', 'unknown')  # 获取发送者
                    
                    # 过滤消息
                    if self.filter_message(content, previous_messages, sender, previous_senders):
                        # 只保留用户名和内容，不要时间
                        formatted_msg = f"{sender}: {content}"
                        filtered_messages.append(formatted_msg)
                        
                        # 更新历记录
                        previous_messages.append(content)
                        previous_senders.append(sender)
                        
                        # 只保留最近的几条消息用于检查重复
                        if len(previous_messages) > 5:
                            previous_messages.pop(0)
                            previous_senders.pop(0)
                
                print(f"过滤后剩余 {len(filtered_messages)} 条消息")
                
                if not filtered_messages:
                    raise ValueError("过滤后没有有效的消息容")
                
                # 调用AI进行分析
                try:
                    if ai_type == "openai":
                        print("调用 OpenAI 接口...")
                        client = OpenAIClient()
                        prompt = f"请分析以下微信群「{group_name}」的聊天记录，并给出总结。"
                        summary = client.analyze(filtered_messages, prompt)
                    else:
                        print("调用豆包AI接口...")
                        client = DouBaoClient()
                        summary = client.analyze(filtered_messages)
                    
                    print("AI分析完成")
                    
                    # 显示分析结果
                    if summary:
                        self.output_text.delete(1.0, tk.END)
                        self.output_text.insert(tk.END, summary)
                    else:
                        raise RuntimeError("AI返回的分析结果为空")
                    
                except Exception as e:
                    print(f"AI调用失败：{str(e)}")
                    error_msg = f"AI分析失败：{str(e)}"
                    self.show_message("错误", error_msg, "error")
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, f"分析失败：{error_msg}")
                    
            except ValueError as e:
                print(f"数据库读取失败：{str(e)}")
                error_msg = f"读取数据库失败：{str(e)}\n请确保已经成功解密数据库。"
                self.show_message("错误", error_msg, "error")
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"分析失败：{error_msg}")
                
        except Exception as e:
            error_msg = str(e)
            print(f"分析过程出错：{error_msg}")
            self.show_message("错误", f"分析过程出错：{error_msg}", "error")
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, f"分析失败：{error_msg}")
            
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.analyze_button.configure(text="开始分析", state="normal"))
    
    def copy_summary(self):
        """复制总结内容"""
        content = self.output_text.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.show_message("提示", "内容已复制到剪贴板")
        else:
            self.show_message("提示", "没有可复制的内容！")
    
    def filter_message(self, message, previous_messages=None, current_sender=None, previous_senders=None):
        """过滤不需要的消息"""
        if not message or not isinstance(message, str):
            return False

        message = message.strip()
        if not message or message.isspace():
            return False

        # 过滤规则
        filter_patterns = [
            r"<[^>]+>",  # XML标签
            r"\[动画表情\]",
            r"\[表情\]",
            r"\[图片\]",
            r"\[文件\]",
            r"\[视频\]",
            r"\[语音\]",
            r"\[通话\]",
            r"\[转账\]",
            r"\[分享\]",
            r"\[聊天记录\]",
            r"撤回了一条消息",
        ]
        
        for pattern in filter_patterns:
            if re.search(pattern, message):
                return False
        
        # 检重复消息
        if previous_messages and previous_senders:
            # 检最近的3条消息
            recent_messages = previous_messages[-3:]
            recent_senders = previous_senders[-3:]
            
            # 如果当前消息与最近的消息相同
            if recent_messages and message == recent_messages[-1]:
                # 即使是不人发的也算复读
                return False
                
            # 检查连续的相同消息
            if len(recent_messages) >= 2:
                # 如果最近两条以上消息都相同
                if all(msg == message for msg in recent_messages):
                    return False
        
        return True

    def check_decrypted_dbs(self):
        """检查是否有可用的解密数据库"""
        config = Config()
        last_info = config.get_decrypt_info()
        
        if last_info and "decrypted_dbs" in last_info and last_info["decrypted_dbs"]:
            # 有可用的解密数据库
            # 更新显示信息
            self.wxid.set(config.decrypt_config["last_wxid"])
            self.version_label.config(text=last_info["version"])
            self.key_label.config(text=last_info["key"])
            
            # 更新数据库显示
            db_names = ", ".join(last_info["decrypted_dbs"].keys())
            self.dir_label.config(text=db_names)
            
            # 显示分析区域
            self.analysis_frame.pack(fill="both", expand=True, padx=10, pady=5)
        else:
            # 没有可用的解密数据库，隐藏分析区域
            self.analysis_frame.pack_forget()

    def show_message(self, title, message, message_type="info"):
        """显示消息框
        
        Args:
            title: 标题
            message: 消息内容
            message_type: 消息类型，可选 "info", "error", "warning"
        """
        if message_type == "error":
            messagebox.showerror(title, message, parent=self.root)
        elif message_type == "warning":
            messagebox.showwarning(title, message, parent=self.root)
        else:
            messagebox.showinfo(title, message, parent=self.root)

class DecryptProgressDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("解密进度")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)  # 设置为父窗口的临时窗口
        
        # 设置弹窗位置为主窗口中心
        self.center_window(parent)
        
        # 创建文本框和滚动条
        self.text = tk.Text(self.dialog, wrap=tk.WORD, height=15)
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(self.dialog, command=self.text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=scrollbar.set)
        
        # 确定按钮（初始时禁用）
        self.ok_button = ttk.Button(self.dialog, text="确定", state="disabled", command=self.dialog.destroy)
        self.ok_button.pack(pady=5)
        
        # 禁止关闭按钮
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def append_log(self, text):
        """添加日志"""
        self.text.insert(tk.END, text + "\n")
        self.text.see(tk.END)  # 滚动到底部
    
    def complete(self, final_text):
        """完��解密"""
        self.text.insert(tk.END, "\n" + final_text)
        self.ok_button.configure(state="normal")  # 启用确定按钮
    
    def center_window(self, parent):
        """将窗口居中显示"""
        # 获取主窗口位置和大小
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 获取弹窗大小
        dialog_width = 500
        dialog_height = 300
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 设置弹窗位置
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")