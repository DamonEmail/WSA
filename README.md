# WeChatAnalyzer - 微信群聊分析工具

WeChatAnalyzer 是一个基于 Python 的微信群聊分析工具，支持使用 AI 智能分析群聊内容，生成聊天摘要。

## ⚠️ 免责声明

1. 本工具仅供学习和研究使用，禁止用于任何商业用途
2. 使用本工具需遵守以下条款：
   - 不得将本工具用于任何非法目的
   - 不得侵犯他人隐私权和数据安全
   - 不得违反微信软件的使用协议
   - 不得将获取的数据用于任何商业用途
3. 使用本工具产生的任何后果由使用者自行承担，与作者无关
4. 作者不对以下情况负责：
   - 任何数据丢失或损坏
   - 任何隐私泄露或安全问题
   - 任何违法或侵权行为
   - 任何间接或直接损失
5. 如果您继续使用本工具，即表示您同意以上免责条款

## 功能特点

- 🔒 安全解密微信数据库
- 📊 群聊记录分析
- 🤖 AI 智能总结（支持 OpenAI3.5/deepseek-r1）
- 🕒 灵活的时间范围选择（最近 24 小时/3 天/7 天）
- 📝 可复制分析结果

## 安装使用

### 环境要求

- Windows 操作系统
- Python 3.8 或更高版本
- 已安装并登录的微信客户端

### 安装步骤

1. 安装依赖：

```sh
pip install -r requirements.txt
```

2. 配置 AI API：
   - `config/ai_config.json`
   - 在配置文件中填入你的 API key - deepseek 是填入硅基流动的接口密钥

### 运行程序

```sh
python run.py
```

## 使用说明

1. 输入微信号并获取密钥
2. 点击"解密数据库"
3. 在分析区域输入群名称
4. 选择时间范围和 AI 模型
5. 点击"开始分析"
6. 等待分析结果生成

## 注意事项

- ⚠️ 本工具仅供学习研究使用
- 请确保微信客户端已登录
- 首次使用需要解密数据库
- 分析大量消息可能需要较长时间
- 请妥善保管 AI API key
- 建议定期备份重要数据
- 使用前请仔细阅读免责声明

## 常见问题

**Q: 为什么找不到数据库文件？**  
A: 请确保微信已登录，且输入了正确的微信号。

**Q: 解密数据库失败怎么办？**  
A: 请检查微信是否正在运行，以及是否有正确的访问权限。

**Q: 找不到指定的群聊？**  
A: 请确保群名称输入正确，可以尝试输入群名称的一部分。

## 开发说明

### 项目结构

```
WeChatAnalyzer/
├── src/                    # 源代码目录
│   ├── core/              # 核心功能模块
│   │   ├── __init__.py
│   │   ├── db_decrypt.py  # 数据库解密
│   │   ├── db_reader.py   # 数据库读取
│   │   ├── analyzer.py    # 消息分析
│   │   ├── wx_decrypt.py  # 微信密钥获取
│   │   └── ai_client.py   # AI 接口客户端
│   ├── utils/             # 工具类
│   │   ├── __init__.py
│   │   ├── config.py      # 配置管理
│   │   ├── message_parser.py  # 消息解析
│   │   ├── user_cache.py  # 用户信息缓存
│   │   └── stats.py       # 统计信息
│   ├── gui/               # 图形界面
│   │   ├── __init__.py
│   │   ├── main_window.py # 主窗口
│   │   └── widgets/       # 自定义控件
│   └── __init__.py
├── config/                # 配置文件目录
│   ├── ai_config.json     # AI 配置
│   ├── decrypt_config.json # 解密配置
│   └── wechat_path.json   # 微信路径缓存
├── database/             # 解密后的数据库目录
├── assets/              # 资源文件目录
│   └── icon.ico         # 程序图标
├── test.py              # 测试脚本
├── run.py               # 程序入口
├── requirements.txt     # 依赖清单
├── README.md           # 项目说明
└── LICENSE             # 许可证文件
```

### 文件说明

1. **核心模块**

   - `db_decrypt.py`: 实现微信数据库解密
   - `db_reader.py`: 读取和解析数据库内容
   - `analyzer.py`: 消息分析和统计
   - `wx_decrypt.py`: 获取微信密钥
   - `ai_client.py`: AI 接口调用

2. **工具类**

   - `config.py`: 配置文件管理
   - `message_parser.py`: 消息内容解析
   - `user_cache.py`: 用户信息缓存
   - `stats.py`: 统计信息处理

3. **配置文件**

   - `ai_config.json`: AI API 配置
   - `decrypt_config.json`: 解密相关配置
   - `wechat_path.json`: 微信安装路径缓存

4. **入口文件**
   - `run.py`: 主程序入口
   - `test.py`: 功能测试脚本

### 核心模块说明

1. **数据库解密 (db_decrypt.py)**

   - 负责微信数据库文件的解密
   - 支持多个数据库文件的批量解密
   - 自动查找微信安装目录

2. **数据库读取 (db_reader.py)**

   - 读取解密后的数据库内容
   - 支持多数据库并行查询
   - 实现消息内容和用户信息的关联

3. **消息分析 (analyzer.py)**

   - 实现消息统计和分析
   - 支持 AI 智能分析
   - 生成分析报告

4. **配置管理 (config.py)**
   - 管理 AI 接口配置
   - 存储解密信息
   - 记录用户配置

### 开发指南

1. **环境配置**

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

2. **运行测试**

```bash
# 运行测试脚本
python test.py

# 运行主程序
python run.py
```

3. **代码规范**

- 遵循 PEP 8 编码规范
- 使用类型注解
- 添加必要的注释
- 使用 markdown 格式编写文档

4. **调试建议**

- 使用 test.py 脚本测试基本功能
- 检查 debug.log 获取详细日志
- 使用 print 输出关键信息
- 善用异常处理和错误提示

### 常见开发问题

1. **数据库解密失败**

   - 检查微信是否正在运行
   - 验证输入的微信号
   - 确认程序权限

2. **找不到数据库文件**

   - 检查微信安装路径
   - 验证文件权限
   - 查看日志输出

3. **AI 分析失败**
   - 检查网络连接
   - 验证 API 密钥
   - 确认配置文件正确

### 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

### 开发计划

- [ ] 支持更多 AI 模型
- [ ] 优化数据库搜索算法
- [ ] 添加导出功能
- [ ] 改进用户界面
- [ ] 增加数据可视化
