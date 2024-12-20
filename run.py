#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
import logging
import platform

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)  # 只添加 wis 目录

# 现在可以直接从 src 导入
from src.gui.main_window import WeChatAnalyzerGUI  # 修改导入路径

def check_environment():
    """检查运行环境"""
    print("环境信息：")
    print(f"Python版本: {platform.python_version()}")
    print(f"Python路径: {sys.executable}")
    print(f"操作系统: {platform.platform()}")
    
    # 检查必要的库
    try:
        import tkinter
        print("✓ tkinter 已安装")
    except ImportError as e:
        print(f"✗ tkinter 未安装: {str(e)}")
        return False
        
    try:
        import pymem
        print("✓ pymem 已安装")
    except ImportError as e:
        print(f"✗ pymem 未安装: {str(e)}")
        return False
        
    try:
        from Crypto.Cipher import AES
        print("✓ pycryptodome 已安装")
    except ImportError as e:
        print(f"✗ pycryptodome 未安装: {str(e)}")
        return False
        
    try:
        import requests
        print("✓ requests 已安装")
    except ImportError as e:
        print(f"✗ requests 未安装: {str(e)}")
        return False
    
    return True

def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('debug.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        # 设置工作目录
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建主窗口
        root = tk.Tk()
        app = WeChatAnalyzerGUI(root)
        
        # 设置窗口图标
        icon_path = os.path.join("resources", "icons", "app.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        
        # 运行程序
        root.mainloop()
        
    except Exception as e:
        logger.exception("程序出错")
        if sys.platform == 'win32':
            input("\n按回车键退出...")

if __name__ == "__main__":
    main()