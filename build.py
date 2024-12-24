import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'run.py',
    '--name=WeChatAnalyzer',
    '--onefile',
    '--noconsole',
    '--clean',  # 清理临时文件
    '--exclude=config/backup',  # 排除备份目录
    '--exclude=database',  # 排除数据库目录
    '--exclude=*.db',  # 排除数据库文件
    '--add-data=config/ai_config.example.json;config',  # 添加必要的配置文件
    '--add-data=config/decrypt_config.json;config',
    # 添加隐藏导入
    '--hidden-import=babel.numbers',
    '--hidden-import=babel.dates',
    '--hidden-import=babel.localedata',
    '--workpath=build',  # 指定构建目录
    '--distpath=dist',  # 指定输出目录
])

print("\n打包完成！")
print("文件位置: ./dist/WeChatAnalyzer.exe") 