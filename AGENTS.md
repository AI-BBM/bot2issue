# bot2issue · Agent 开发者协作指南 (AGENTS.md)

> 致所有协同开发与审查本项目的 AI Agent（Cursor、Antigravity、Claude Code 等）：  
> 本项目为通用的「微信 ClawBot / 企业微信 ➔ 智能 PM 引导 ➔ 跨仓库 GitHub Issue 自动化中枢」。  
> 请严格遵守以下规范进行维护与演进。

---

## 1. 核心宪法原则
1. **真实价值第一**：代码是负债，优先用极简标准库解决业务问题，严禁引入未经讨论的笨重框架。
2. **安全底线（Zero Trust）**：
   - 绝不在 Git 仓库内提交任何真实的 `AI_API_KEY`、`GITHUB_TOKEN` 或个人密钥。
   - 所有密钥严格通过 `.env` 或运行时系统环境变量注入。
3. **奥卡姆剃刀**：
   - 保持通道抽象与业务中枢解耦（`channels/` vs `core/` vs `publishers/`）。
   - 扩展新通道（如飞书、钉钉）时，只需实现 `BaseChannel` 并在 `server.py` 挂载，严禁入侵 `core/ai_engine.py` 的核心业务逻辑。

---

## 2. 核心架构速览
- `channels/clawbot_ilink.py`：腾讯 iLink 协议长轮询与媒体解密（AES-128-ECB）。
- `channels/wecom.py`：企业微信应用 Webhook 与消息通道。
- `core/router.py`：多仓库路由解析器（支持前缀 `[#repo]` 与项目配置）。
- `core/ai_engine.py`：资深产品经理对话提示词与 Issue 抽取引导。
- `core/cloud_ai.py`：标准 OpenAI 协议驱动器。
- `publishers/github_publisher.py`：跨仓库 Issue 创建器。

---

## 3. 下游生态协同约定 (以 ClassMotivation 希沃白板为例)
- **定位分工**：`bot2issue` 为**云端公网调度网关**；下游白板终端为**离线单机纯 Go 客户端**。
- **动态暗桩规则**：下游客户端（如 `class_motivation`）在开箱时通过 URL `http://<bot2issue-host>:3006/?repo=<target_repo>&name=<app_name>` 申请专属绑定码。
- **打分指令分流**：涉及即时加减分业务（“张三+2分”）可直接透传至下游白板终端；涉及系统改进与长文反馈的，全权由 `ai_engine.py` 引导并转为 GitHub Issue。

---

## 4. 本地验证指令
每次提交代码前，必须确保测试通过：
```bash
python tests/test_all.py
```
