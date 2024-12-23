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
from ..core.db_decrypt import DBDecrypt

class WeChatAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("微信群聊分析工具")
        self.root.geometry("800x700")
        
        # 初始化变量
        self.ai_type = tk.StringVar(value="openai")
        self.wxid = tk.StringVar()
        self.group_name = tk.StringVar()
        self.prompt_type = tk.StringVar(value="default")
        self.default_prompt = "你是一位专业的群聊分析师，简明扼要地总结重点。"
        
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
        
        # 只保留一个解密按钮
        self.decrypt_btn = ttk.Button(
            button_frame, 
            text="解密数据库",
            command=self.decrypt_database,
            width=12  # 设置按钮宽度
        )
        self.decrypt_btn.pack(side=tk.LEFT, padx=5)
        
        # 调整按钮字体大小
        style = ttk.Style()
        style.configure('TButton', 
            font=('微软雅黑', 10),  # 置体
            padding=(10, 5)  # 增加内边距
        )
        
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
    
    def decrypt_database(self):
        """解密数据库的统一流程"""
        wxid = self.wxid.get().strip()
        if not wxid:
            messagebox.showerror("错误", "请输入微信号")
            return
        
        try:
            # 禁用按钮
            self.decrypt_btn.configure(text="解密中...", state='disabled')
            
            # 创建进度窗口
            progress_dialog = DecryptProgressDialog(self.root)
            
            def run_decrypt():
                try:
                    # 1. 获取密钥 (占20%)
                    progress_dialog.set_progress(0)
                    progress_dialog.append_log("正在获取密钥...")
                    decrypter = WeChatDecrypt()
                    version, key = decrypter.get_key(wxid)
                    
                    # 更新界面显示
                    self.root.after(0, lambda: [
                        self.version_label.config(text=version),
                        self.key_label.config(text=key[:10] + "..." + key[-10:])
                    ])
                    
                    progress_dialog.append_log("✅ 获取密钥成功")
                    progress_dialog.set_progress(20)
                    
                    # 2. 解密数据库 (占80%)
                    progress_dialog.append_log("\n开始解密数据库...")
                    db_decrypter = DBDecrypt(wxid, key)
                    
                    def progress_callback(msg):
                        if "找到以下数据库文件" in msg:
                            progress_dialog.set_progress(30)
                        elif "开始准备数据库" in msg:
                            progress_dialog.set_progress(40)
                        elif "开始解密数据库" in msg:
                            progress_dialog.set_progress(50)
                        elif "联系人数据库解密成功" in msg:
                            progress_dialog.set_progress(70)
                        elif "MSG" in msg and "解密成功" in msg:
                            # 剩余30%平均分配给消息数据库
                            progress_dialog.increment_progress(5)
                        elif "数据库解密成功" in msg and "AI分析" in msg:
                            progress_dialog.set_progress(100)
                        
                        progress_dialog.append_log(f"  {msg}" if not msg.startswith("\n") else msg)
                    
                    results = db_decrypter.decrypt_all(progress_callback=progress_callback)
                    
                    # 统计结果
                    success_count = sum(1 for v in results.values() if not v.startswith("解密失败"))
                    total_count = len(results)
                    
                    # 更新主界面显示
                    if success_count > 0:
                        db_names = ", ".join(name for name, path in results.items() 
                                          if not path.startswith("解密失败"))
                        self.root.after(0, lambda: [
                            self.dir_label.config(text=db_names, foreground="green"),
                            self.analysis_frame.pack(fill="both", expand=True, padx=10, pady=5)
                        ])
                        
                        # 更新配置
                        Config().update_decrypted_dbs(wxid, results)
                        
                        # 启用确定按钮
                        progress_dialog.complete("")  # 不需要额外的文本，因为日志已经显示了结果
                    else:
                        self.root.after(0, lambda: self.dir_label.config(
                            text="解密失败", foreground="red"
                        ))
                        # 启用确定按钮，显示失败信息
                        progress_dialog.complete("解密失败，请检查错误信息")
                    
                except Exception as e:
                    error_msg = str(e)
                    # 使用 after 方法在主线程中更新 UI
                    self.root.after(0, lambda: progress_dialog.append_log(f"\n❌ 发生错误: {error_msg}"))
                    self.root.after(0, lambda: self.dir_label.config(
                        text="解密出错", foreground="red"
                    ))
                    # 使用 after 方法在主线程中更新 UI
                    self.root.after(0, lambda: progress_dialog.complete("解密出错，请查看错误信息"))
                finally:
                    # 使用 after 方法在主线程中更新 UI
                    self.root.after(0, lambda: self.decrypt_btn.configure(
                        text="解密数据库", state='normal'
                    ))
            
            # 在新线程中运行
            thread = threading.Thread(target=run_decrypt)
            thread.daemon = True  # 设置为守护线程
            thread.start()
            
        except Exception as e:
            self.decrypt_btn.configure(text="解密数据库", state='normal')
            messagebox.showerror("错误", f"启动解密失败：{str(e)}")
    
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
        self.analysis_frame = ttk.LabelFrame(self.main_frame, text="群聊分析", padding="10")
        
        # 1. 第一行：群名称、AI模型和提示词设置
        first_row = ttk.Frame(self.analysis_frame)
        first_row.pack(fill="x", pady=5)
        
        # 群名称
        name_frame = ttk.Frame(first_row)
        name_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(name_frame, text="群名称:").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.group_name, width=30).pack(side=tk.LEFT, padx=5)
        
        # AI模型选择
        ai_frame = ttk.Frame(first_row)
        ai_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(ai_frame, text="AI模型:").pack(side=tk.LEFT)
        ttk.Radiobutton(ai_frame, text="OpenAI", variable=self.ai_type, value="openai").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(ai_frame, text="豆包AI", variable=self.ai_type, value="doubao").pack(side=tk.LEFT, padx=5)
        
        # 提示词设置
        prompt_type_frame = ttk.Frame(first_row)
        prompt_type_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(prompt_type_frame, text="提示词设置:").pack(side=tk.LEFT)
        ttk.Radiobutton(prompt_type_frame, text="默认", variable=self.prompt_type, value="default",
                       command=self.update_prompt_input).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(prompt_type_frame, text="自定义", variable=self.prompt_type, value="custom",
                       command=self.update_prompt_input).pack(side=tk.LEFT, padx=5)
        
        # 2. 第二行：时间范围、分析按钮和提示词输入
        second_row = ttk.Frame(self.analysis_frame)
        second_row.pack(fill="x", pady=5)
        
        # 时间范围选择
        time_frame = ttk.Frame(second_row)
        time_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(time_frame, text="时间范围:").pack(side=tk.LEFT)
        self.time_range = tk.StringVar(value="1")
        ttk.Radiobutton(time_frame, text="最近24小时", variable=self.time_range, value="1").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(time_frame, text="最近3天", variable=self.time_range, value="3").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(time_frame, text="最近7天", variable=self.time_range, value="7").pack(side=tk.LEFT, padx=5)
        
        # 分析按钮
        self.analyze_button = ttk.Button(
            second_row,
            text="开始分析",
            command=self.start_analysis,
            width=12
        )
        self.analyze_button.pack(side=tk.LEFT, padx=10)
        
        # 提示词输入框 - 改用 Text 组��替代 Entry
        prompt_frame = ttk.Frame(second_row)
        prompt_frame.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        self.default_prompt = "你是一位专业的群聊分析师，简明扼要地总结重点。"
        self.prompt_input = tk.Text(
            prompt_frame,
            wrap=tk.WORD,  # 自动换行
            height=2,      # 设置为2行高度
            font=('微软雅黑', 10)
        )
        self.prompt_input.pack(fill="x", expand=True)
        self.prompt_input.insert("1.0", self.default_prompt)
        self.prompt_input.configure(state="disabled")
        
        # 3. 第三行：分析结果
        result_frame = ttk.LabelFrame(self.analysis_frame, text="分析结果", padding="5")
        result_frame.pack(fill="both", expand=True, pady=5)
        
        # 创建一个内部框架来包含文本框和按钮
        inner_frame = ttk.Frame(result_frame)
        inner_frame.pack(fill="both", expand=True)
        
        # 文本框和滚动条
        text_frame = ttk.Frame(inner_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.output_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            height=15,
            font=('微软雅黑', 10)
        )
        self.output_text.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.output_text.configure(yscrollcommand=scrollbar.set)
        
        # 复制按钮放在文本框下方
        button_frame = ttk.Frame(inner_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        copy_button = ttk.Button(
            button_frame,
            text="复制结果",
            command=self.copy_summary,
            width=12
        )
        copy_button.pack(side=tk.RIGHT, padx=5)
    
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
        self.output_text.insert(tk.END, "正在析中，请稍候...\n")
        
        # 在新线程中运行分析
        thread = threading.Thread(target=self.run_analysis)
        thread.start()
    
    def run_analysis(self):
        """运行群消息分析"""
        try:
            def update_ui(text):
                """在主线程中更新UI"""
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, text)
                
            def show_error(title, message):
                """在主线程中显示错误"""
                self.root.after(0, lambda: self.show_message(title, message, "error"))
                
            def update_button():
                """在主线程中更新按钮状态"""
                self.analyze_button.configure(text="开始分析", state="normal")
            
            # 在主线程中更新初始状态
            self.root.after(0, lambda: update_ui("正在分析中...\n"))
            
            try:
                # 创建数据库读取器
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
                reader = WeChatDBReader(db_path)
                
                # 获取聊天记录
                chat_records = reader.analyze_group(self.group_name.get(), days=int(self.time_range.get()))
                record_count = len(chat_records)
                
                # 在主线程中更新进度提示
                if record_count > 800:
                    self.root.after(0, lambda: update_ui(
                        "正在分析中(聊天记录较多，可能需要较长时间)...\n"
                        f"共发现 {record_count} 条记录，请耐心等待\n"
                    ))
                else:
                    self.root.after(0, lambda: update_ui(f"正在分析 {record_count} 条聊天记录...\n"))
                
                # 过滤消息
                filtered_records = []
                for msg in chat_records:
                    if self.filter_message(msg['content'], [], msg.get('sender', 'unknown'), []):
                        filtered_records.append(msg)
                
                if not filtered_records:
                    raise ValueError("过滤后没有有效的消息")
                
                # 获取提示词
                system_prompt = self.prompt_input.get("1.0", tk.END).strip() if self.prompt_type.get() == "custom" else self.default_prompt
                
                # 调用AI分析
                ai_type = self.ai_type.get()
                if ai_type == "openai":
                    client = OpenAIClient()
                else:
                    client = DouBaoClient()
                    
                summary = client.analyze(
                    messages=filtered_records,
                    group_name=self.group_name.get(),
                    system_prompt=system_prompt
                )
                
                # 在主线程中显示结果
                self.root.after(0, lambda: update_ui(summary))
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: show_error("错误", f"分析失败：{error_msg}"))
                
        finally:
            # 在主线程中恢复按钮状态
            self.root.after(0, update_button)
    
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

    def update_prompt_input(self):
        """更新提示词输入框状态"""
        if self.prompt_type.get() == "default":
            self.prompt_input.configure(state="normal")
            self.prompt_input.delete("1.0", tk.END)
            self.prompt_input.insert("1.0", self.default_prompt)
            self.prompt_input.configure(state="disabled")
        else:
            self.prompt_input.configure(state="normal")
            self.prompt_input.delete("1.0", tk.END)

class DecryptProgressDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.progress = 0  # 添加进度变量
        self.update_title()  # 更新标题
        self.dialog.geometry("500x450")
        self.dialog.transient(parent)
        
        # 设置弹窗位置为主窗口中心
        self.center_window(parent)
        
        # 创建主框架
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建文本框框架
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建文本框和滚动条
        self.text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            height=14,
            font=('微软雅', 10),
            background='#f0f0f0'
        )
        self.text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # 配置文本标签
        self.text.tag_configure('success', foreground='#00d26a')      # 绿色 - ✅
        self.text.tag_configure('complete', foreground='#00d26a')     # 翡翠绿 - 完成提示
        self.text.tag_configure('error', foreground='#dc3545')        # 红色 - ❌
        self.text.tag_configure('info', foreground='#17a2b8')         # 蓝色 - 进度信息
        
        # 设置字体样式
        self.text.tag_configure('bold', font=('微软黑', 10, 'bold'))  # 加粗样式
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_frame, command=self.text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=scrollbar.set)
        
        # 创建底部按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 确定按钮（居中显示）
        self.ok_button = ttk.Button(
            button_frame,
            text="确定",
            command=self.close_dialog,
            state="disabled",
            width=15
        )
        self.ok_button.pack(pady=5)
        
        # 初始时禁用关闭按钮
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 记录是否完成
        self.is_completed = False
    
    def on_close(self):
        """处理窗口关闭事件"""
        if self.is_completed:
            self.dialog.destroy()
    
    def close_dialog(self):
        """关闭对话框"""
        self.dialog.destroy()
    
    def append_log(self, text):
        """添加日志"""
        # 插入文本
        end_pos = self.text.index(tk.END)
        self.text.insert(tk.END, text + "\n")
        
        # 为不同的文本应用不同的样式
        line_start = f"{end_pos} linestart"
        line_end = f"{end_pos} lineend + 1c"
        
        # 检查并应用标签
        if '✅' in text:
            self.text.tag_add('success', line_start, line_end)
        elif '✨' in text and '🎉' in text and '💡' in text:
            # 为完成提示应用特殊样式
            self.text.tag_add('complete', line_start, line_end)
            self.text.tag_add('bold', line_start, line_end)  # 添加加粗效果
        elif '❌' in text:
            self.text.tag_add('error', line_start, line_end)
        elif text.startswith('正在'):
            self.text.tag_add('info', line_start, line_end)
        
        self.text.see(tk.END)  # 滚动到底
    
    def complete(self, final_text):
        """完成解密"""
        if final_text:
            self.append_log("\n" + final_text)
        
        # 标记完成状态
        self.is_completed = True
        
        # 启用确定按钮
        self.ok_button.configure(state="normal")
        
        # 允许通过关闭按钮关闭窗口
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)
    
    def center_window(self, parent):
        """将窗口居中显示"""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 调整弹窗大小
        dialog_width = 500
        dialog_height = 450
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 设置弹窗位置
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def update_title(self):
        """更新窗口标题，显示进度"""
        self.dialog.title(f"解密进度 ({self.progress}%)")
    
    def set_progress(self, value):
        """设置进度值"""
        self.progress = value
        self.update_title()
    
    def increment_progress(self, increment):
        """增加进度值"""
        self.progress = min(100, self.progress + increment)
        self.update_title()