import PyInstaller.__main__
import os
import shutil

def build():
    """打包应用"""
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 配置文件路径
    config_dir = os.path.join(root_dir, "config")
    icon_path = os.path.join(root_dir, "resources", "icons", "app.ico")
    
    # 创建发布目录
    release_dir = os.path.join(root_dir, "release")
    os.makedirs(release_dir, exist_ok=True)
    
    # PyInstaller参数
    params = [
        "main.py",                          # 入口文件
        "--name=WeChatAnalyzer",            # 生成的exe名称
        "--onefile",                        # 打包成单个文件
        "--windowed",                       # 使用GUI模式
        f"--add-data={config_dir};config",  # 添加配置文件
        "--clean",                          # 清理临时文件
        "--noconfirm",                      # 不确认覆盖
        f"--distpath={release_dir}",        # 指定输出目录
    ]
    
    # 如果有图标就添加
    if os.path.exists(icon_path):
        params.append(f"--icon={icon_path}")
    
    # 运行打包
    PyInstaller.__main__.run(params)
    
    # 复制必要的文件到发布目录
    readme_path = os.path.join(root_dir, "README.md")
    if os.path.exists(readme_path):
        shutil.copy2(readme_path, release_dir)
    
    # 创建数据库目录
    os.makedirs(os.path.join(release_dir, "database"), exist_ok=True)
    
    print("\n打包完成！")
    print(f"发布文件在: {release_dir}")
    print("使用说明：")
    print("1. 确保微信已经登录")
    print("2. 运行 WeChatAnalyzer.exe")
    print("3. 输入微信号并获取密钥")
    print("4. 点击解密数据库")
    print("5. 解密后的数据库文件会保存在database目录")

if __name__ == "__main__":
    build() 