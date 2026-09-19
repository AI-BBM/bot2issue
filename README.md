# 🤖 bot2issue (Universal Bot-to-Issue Hub)

> **全局通用需求智能中枢**：微信 ClawBot / 企业微信 ➔ 资深数字化 PM 引导澄清 ➔ 跨仓库自动化 GitHub Issue 交付平台。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/Repo-michmingcao%2Fbot2issue-black?logo=github)](https://github.com/michmingcao/bot2issue)

---

## 1. 业务全景与核心价值

无论是为餐饮企业交付数字门店、为制造业定制 CRM、还是为初创团队研发内部系统，客户与管理者往往习惯**在微信里发语音、随手拍截图、发碎片化想法**。传统外包模式下，这些想法容易被遗漏，或者因为“只有现象、没有边界”而导致研发来回扯皮。

**bot2issue** 作为一套**通用底层基础设施服务**，彻底打通了人与 GitHub 之间的壁垒：

```text
【用户端】 个人微信 (ClawBot) / 企业微信 (WeCom)
    │  (语音 / 截图 / 文字随性表达)
    ▼
【通道层】 腾讯官方 iLink 正规军协议 (免封号) + 企微应用 Webhook
    │
    ▼
【中枢层】 资深数字化 PM 智能体 (云端兼容 OpenAI/DeepSeek 协议)
    │  (主动追问业务场景、受众、验收边界，草案预览卡点，等用户回复「确认」)
    ▼
【路由层】 多项目 / 多租户智能路由网关 (根据 Bot 标识或 [#项目] 指令分流)
    │
    ▼
【交付层】 跨组织 / 跨个人 GitHub 目标仓库自动创建结构化 Issue 并秒级回传卡片
```

---

## 2. 核心特性

- **🛡️ 腾讯官方免封正规通道**：采用微信 8.0.70+ 官方插件与 iLink 协议，零 Hook、零逆向，手机微信扫码即在微信通讯录拥有“专属需求助手”。
- **⚡ 多模态全支持**：
  - 文字、语音条（自动提取文字）；
  - 图片/视频媒体（基于 AES-128-ECB 自动解密并转储至本地媒体附件库）；
  - 0.1秒级输入态通知（微信界面即时显示“对方正在输入...”）；
  - 支持消息引用与防手抖 2 分钟撤回感知。
- **🧠 资深产品经理引导 (Conversational PM)**：
  - 不做机械的录音机，主动提问澄清 1~2 个核心边界；
  - 自动归纳【业务痛点】与【验收标准】；
  - 人机拍板机制：只有用户明确回复「确认 / 提交 / 发布 / 对」时才触发建单。
- **🗺️ 跨组织多仓库动态路由**：
  - 一个服务同时承载多个客户与系统；
  - 支持快捷前缀（如 `[#crm] 登录页报500` 直达 CRM 仓库）；
  - 支持通过 `config/projects.json` 灵活映射不同 Bot 到特定仓库。
- **🏢 企微平滑演进**：
  - 抽象统一 `BaseChannel` 通道标准，已内置 WeCom 适配器，随时一键接入企业微信自建应用。

---

## 3. 极速开箱使用

### 3.1 环境准备
系统仅依赖 Python 3 及标准库（多媒体解密使用标准 `cryptography`）：

```bash
pip install cryptography
```

### 3.2 配置环境变量
复制模板生成 `.env`：

```bash
cp .env.example .env
```

按需填写：
```env
# 云端 AI 密钥 (兼容 DeepSeek、通义千问、智谱等)
AI_API_BASE=https://api.deepseek.com
AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 默认 GitHub 仓库
DEFAULT_GITHUB_REPO=michmingcao/bot2issue
```

> **提示**：若本地已通过 `gh auth login` 登录个人 GitHub，系统将自动读取本机凭证，无需在 `.env` 中硬编码 `GITHUB_TOKEN`！

### 3.3 启动服务
```bash
python server.py
```

终端将打印：
```text
============================================================
🚀 bot2issue 通用中枢已拉起！
🌐 统一控制台入口: http://127.0.0.1:3006
📦 默认 GitHub 仓库: michmingcao/bot2issue
============================================================
```

打开浏览器访问 `http://127.0.0.1:3006`：
1. 页面直出微信官方授权二维码；
2. 用微信（已开启 ClawBot 插件）扫码确认；
3. 扫码成功后，直接在手机微信对管家发消息、发语音、发截图即可！

### 3.4 为任意定制软件程序化发行专属微信 Bot (零门槛免指定)

当您为任何客户交付定制软件系统时（如 ERP、CRM、物流平台等），可通过以下任意方式**一秒生成该软件专属的微信接入二维码**：

#### 姿势 1：浏览器 URL 参数直出
在浏览器打开带参数的网址：
```text
http://127.0.0.1:3006/?repo=clientA/smart-wms&name=智慧仓储系统
```
- 控制台自动打出【智慧仓储系统】专属授权码；
- 客户扫码后，其微信号**永久暗桩锁定**至 `clientA/smart-wms` 仓库；
- 客户在微信随性发语音/截图，**100% 自动投递到该仓库，无需输入任何指令或标签**！

#### 姿势 2：使用命令行工具 (CLI) 一键发行
```bash
# 为任何定制软件发行专属微信接入二维码
python manage.py bind --repo clientA/smart-wms --name "智慧仓储系统"

# 查看当前已绑定的客户与系统列表
python manage.py list

# 解绑特定客户
python manage.py unbind --user-id wx_user_xxx
```

#### 姿势 3：通过后台 REST API 程序化自动化开通
```bash
curl -X POST http://127.0.0.1:3006/api/tenant/bind-qrcode \
  -H "Content-Type: application/json" \
  -d '{"repo": "clientA/smart-wms", "name": "智慧仓储系统"}'
```
直接返回微信官方授权二维码链接与预览图，可直接无缝嵌入您主系统的“帮助与反馈”界面！

---

## 4. 目录结构

```text
bot2issue/
├── channels/                    # 通道适配层
│   ├── base.py                 # 统一通道基类与消息结构
│   ├── clawbot_ilink.py        # 微信 ClawBot (腾讯 iLink) 适配器
│   └── wecom.py                # 企业微信 AI BOT 适配器
├── core/                       # 核心业务引擎
│   ├── ai_engine.py            # 资深 PM 智能对话引导与提单抽取引导
│   ├── cloud_ai.py             # 通用云端大模型驱动器 (OpenAI 协议)
│   ├── router.py               # 多项目 / 多仓库智能路由分发
│   └── session.py              # 多用户多轮对话状态机
├── publishers/                 # 资产交付层
│   └── github_publisher.py     # 跨仓库 GitHub Issue 自动创建与图片挂载
├── config/                     # 路由与项目映射配置
│   └── projects.json           # 静态项目映射表
├── tests/                      # 自动化测试套件
│   └── test_all.py             # 单元与集成测试
├── server.py                   # 服务主入口与轻奢网页大盘
├── .env.example                # 环境变量模板
└── README.md                   # 本文档
```

---

## 5. 自动化测试

运行内建全套单元测试：

```bash
python tests/test_all.py
```

---

## 6. 许可证

[MIT License](LICENSE) © 2026 michmingcao
