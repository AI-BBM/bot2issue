#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot2issue - 全局通用需求中枢主服务 (Universal Bot-to-Issue Hub)
支持微信 ClawBot (腾讯 iLink) 扫码接入、多项目路由、云端 AI 引导、GitHub 自动提单
"""

import os
import sys
import json
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Any, Dict, Optional, List

# 自动载入本地 .env 文件 (轻量零依赖实现)
def load_dotenv(env_path=".env"):
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception as e:
            print(f"[Dotenv] 载入 .env 失败: {e}")

load_dotenv()

from channels.base import IncomingMessage
from channels.clawbot_ilink import ClawbotIlinkChannel
from channels.wecom import WeComChannel
from core.session import SessionManager
from core.router import ProjectRouter
from core.cloud_ai import CloudAIClient
from core.ai_engine import ConversationalPMEngine
from publishers.github_publisher import GitHubPublisher

PORT = int(os.environ.get("CLAWBOT_PORT", "3006"))
HOST = os.environ.get("HOST", "0.0.0.0")

# 初始化基础设施组件
session_mgr = SessionManager(storage_path="data/sessions.json")
router = ProjectRouter(config_path="config/projects.json")
cloud_ai = CloudAIClient()
publisher = GitHubPublisher()
engine = ConversationalPMEngine(session_mgr, router, cloud_ai, publisher)

# 初始化并启动通道
clawbot_channel = ClawbotIlinkChannel(
    baseurl=os.environ.get("CLAWBOT_BASEURL", "https://ilinkai.weixin.qq.com"),
    uploads_dir="uploads",
    data_dir="data"
)
wecom_channel = WeComChannel()

def handle_incoming_message(msg: IncomingMessage) -> str:
    return engine.process_incoming(msg)

clawbot_channel.register_handler(handle_incoming_message)
wecom_channel.register_handler(handle_incoming_message)

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>bot2issue · 通用需求智能中枢</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(18, 24, 38, 0.85);
      --border: rgba(255, 255, 255, 0.08);
      --text: #f3f4f6;
      --subtext: #9ca3af;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.15);
      --success: #10b981;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; padding: 30px 20px; }
    .container { max-width: 1080px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }
    h1 { font-size: 24px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
    .badge { font-size: 12px; padding: 4px 10px; border-radius: 20px; background: var(--accent-glow); color: var(--accent); border: 1px solid var(--accent); }
    .grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 24px; margin-bottom: 24px; }
    @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 24px; box-shadow: 0 8px 30px rgba(0,0,0,0.3); backdrop-filter: blur(12px); }
    .card-title { font-size: 16px; font-weight: 600; color: #fff; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between; }
    .qr-box { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px 0; }
    .qr-img { width: 220px; height: 220px; border-radius: 12px; border: 2px solid var(--accent); background: #fff; padding: 8px; }
    .status-pill { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; margin-top: 15px; color: var(--subtext); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--warning); }
    .dot.active { background: var(--success); box-shadow: 0 0 10px var(--success); }
    .btn { padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; transition: 0.2s; }
    .btn-primary { background: var(--accent); color: #000; }
    .btn-primary:hover { opacity: 0.9; }
    .btn-outline { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
    .table-box { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
    .table-box th, .table-box td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
    .table-box th { color: var(--subtext); font-weight: 500; }
    .chat-box { display: flex; flex-direction: column; height: 320px; border: 1px solid var(--border); border-radius: 10px; background: rgba(0,0,0,0.2); }
    .chat-messages { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; font-size: 13px; }
    .msg { max-width: 85%; padding: 10px 14px; border-radius: 10px; line-height: 1.5; white-space: pre-wrap; }
    .msg.user { align-self: flex-end; background: #2563eb; color: #fff; }
    .msg.bot { align-self: flex-start; background: #1f2937; border: 1px solid var(--border); color: #e5e7eb; }
    .chat-input-bar { display: flex; border-top: 1px solid var(--border); padding: 8px; gap: 8px; }
    .chat-input { flex: 1; background: #111827; border: 1px solid var(--border); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 13px; outline: none; }
    .chat-input:focus { border-color: var(--accent); }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>🤖 bot2issue <span class="badge">通用需求智能中枢</span></h1>
        <p style="color:var(--subtext); font-size: 13px; margin-top: 6px;">微信 ClawBot / 企业微信 ➔ 资深数字化 PM 引导 ➔ 跨仓库自动化 GitHub Issue</p>
      </div>
      <div>
        <span class="status-pill"><span class="dot active"></span> 服务常驻运行中</span>
      </div>
    </header>

    <div class="grid">
      <!-- 微信 ClawBot 授权卡片 -->
      <div class="card">
        <div class="card-title">
          <span>📲 微信 ClawBot 官方免封绑定</span>
          <button class="btn btn-outline" onclick="fetchQRCode()">🔄 刷新二维码</button>
        </div>
        <div id="target-software-banner" style="display:none; margin-bottom:12px; padding:10px 14px; border-radius:8px; background:rgba(56,189,248,0.12); border:1px solid var(--accent); font-size:12px; color:#fff;">
          🎯 专属开通中：<strong id="banner-name" style="color:var(--accent);"></strong> ➔ 目标仓库：<code id="banner-repo" style="color:var(--accent);"></code>
        </div>
        <div class="qr-box">
          <img id="qr-image" class="qr-img" src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><text x='50%25' y='50%25' text-anchor='middle' fill='%23666'>加载二维码中...</text></svg>" alt="授权二维码" />
          <div class="status-pill">
            <span id="qr-dot" class="dot"></span>
            <span id="qr-status-text">正在向腾讯 iLink 申请安全授权...</span>
          </div>
          <p style="font-size:12px; color:var(--subtext); margin-top: 10px; text-align: center;">
            用已开启「微信 ClawBot」插件的微信扫一扫确认<br/>扫码后在微信即可 1 对 1 语音/发图聊需求！
          </p>
        </div>
      </div>

      <!-- 快速调试模拟器 -->
      <div class="card">
        <div class="card-title">
          <span>💬 在线交互与 PM 需求引导模拟舱</span>
          <span style="font-size: 12px; color: var(--subtext);">无缝联调云端 AI</span>
        </div>
        <div class="chat-box">
          <div id="chat-msgs" class="chat-messages">
            <div class="msg bot">您好！我是您的随身数字化产品经理。无论是前台客户反馈、还是新功能构想，您可以随时在下方打字发给我，我将帮您深度梳理并同步至对应的 GitHub 仓库！</div>
          </div>
          <div class="chat-input-bar">
            <input id="chat-in" class="chat-input" placeholder="例如：[#bot2issue] 详情页希望能加个导出 Excel 按钮..." onkeydown="if(event.key==='Enter') sendSimChat()" />
            <button class="btn btn-primary" onclick="sendSimChat()">发送</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 仓库路由配置 -->
    <div class="card">
      <div class="card-title">
        <span>🗺️ 当前项目与 GitHub 仓库智能路由表</span>
        <span style="font-size: 12px; color: var(--accent);">支持跨个人 / 跨组织派发</span>
      </div>
      <table class="table-box">
        <thead>
          <tr>
            <th>项目代号</th>
            <th>项目名称</th>
            <th>目标 GitHub 仓库</th>
            <th>快捷指令</th>
            <th>默认标签</th>
          </tr>
        </thead>
        <tbody id="projects-table">
          <tr><td colspan="5" style="text-align:center; color:var(--subtext);">加载配置中...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <script>
    let currentQr = "";
    let pollInterval = null;

    async function fetchQRCode() {
      const statusText = document.getElementById("qr-status-text");
      const dot = document.getElementById("qr-dot");
      statusText.innerText = "正在向腾讯 iLink 申请二维码...";
      dot.className = "dot";

      if (pollInterval) clearInterval(pollInterval);

      const urlParams = new URLSearchParams(window.location.search);
      const targetRepo = urlParams.get('repo') || '';
      const targetName = urlParams.get('name') || '';
      const targetWelcome = urlParams.get('welcome') || '';

      if (targetRepo || targetName) {
        document.getElementById("target-software-banner").style.display = "block";
        document.getElementById("banner-name").innerText = targetName || "定制软件系统";
        document.getElementById("banner-repo").innerText = targetRepo || "默认仓库";
      }

      try {
        let apiUrl = "/api/wechat/qrcode";
        if (targetRepo || targetName) {
          apiUrl += `?repo=${encodeURIComponent(targetRepo)}&name=${encodeURIComponent(targetName)}&welcome=${encodeURIComponent(targetWelcome)}`;
        }
        const res = await fetch(apiUrl);
        const data = await res.json();
        if (data.success && data.qr_img) {
          document.getElementById("qr-image").src = data.qr_img;
          currentQr = data.qrcode;
          statusText.innerText = "请打开微信扫码确认授权";
          startPolling(currentQr);
        } else {
          statusText.innerText = "获取二维码异常: " + (data.error || "未知");
        }
      } catch (e) {
        statusText.innerText = "请求错误: " + e;
      }
    }

    function startPolling(qrcode) {
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch("/api/wechat/qrcode-status?qrcode=" + encodeURIComponent(qrcode));
          const data = await res.json();
          const dot = document.getElementById("qr-dot");
          const statusText = document.getElementById("qr-status-text");

          if (data.status === "confirmed") {
            clearInterval(pollInterval);
            dot.className = "dot active";
            statusText.innerText = "✅ 微信已成功绑定！可在微信通讯录畅聊！";
          } else if (data.status === "scaned") {
            statusText.innerText = "📱 已扫码，请在手机微信点击【确认】";
          }
        } catch (e) {
          console.error(e);
        }
      }, 2500);
    }

    async function loadProjects() {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        const tbody = document.getElementById("projects-table");
        tbody.innerHTML = "";
        data.projects.forEach(p => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><code>${p.id}</code></td>
            <td style="font-weight:600; color:#fff;">${p.name}</td>
            <td><code style="color:var(--accent);">${p.repo}</code></td>
            <td><code>[#${p.id}]</code></td>
            <td>${(p.labels||[]).map(l => '<span class="badge">'+l+'</span>').join(' ')}</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function sendSimChat() {
      const input = document.getElementById("chat-in");
      const text = input.value.trim();
      if (!text) return;

      const chatMsgs = document.getElementById("chat-msgs");
      const userDiv = document.createElement("div");
      userDiv.className = "msg user";
      userDiv.innerText = text;
      chatMsgs.appendChild(userDiv);
      input.value = "";
      chatMsgs.scrollTop = chatMsgs.scrollHeight;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: json_str = JSON.stringify({message: text, user_id: "web_simulator"})
        });
        const data = await res.json();
        const botDiv = document.createElement("div");
        botDiv.className = "msg bot";
        botDiv.innerText = data.reply;
        chatMsgs.appendChild(botDiv);
        chatMsgs.scrollTop = chatMsgs.scrollHeight;
      } catch (e) {
        alert("通讯异常: " + e);
      }
    }

    window.onload = () => {
      fetchQRCode();
      loadProjects();
    };
  </script>
</body>
</html>
"""

class BotHubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. 首页控制台
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            return

        # 2. 获取微信授权二维码 (支持程序化指定目标定制系统与仓库)
        if path == "/api/wechat/qrcode":
            repo = query.get("repo", [""])[0]
            name = query.get("name", [""])[0]
            welcome = query.get("welcome", [""])[0]
            qr_res = clawbot_channel.get_qr_code()
            if qr_res.get("success") and (repo or name):
                router.register_pending_qr(qr_res["qrcode"], repo=repo, name=name, welcome=welcome)
            self._send_json(qr_res)
            return

        # 3. 轮询扫码状态 (确认扫码即自动永久落锁客户微信ID与目标仓库)
        if path == "/api/wechat/qrcode-status":
            qr_val = query.get("qrcode", [""])[0]
            status_res = clawbot_channel.check_qr_status(qr_val)
            if status_res.get("status") == "confirmed" and status_res.get("ilink_user_id"):
                usr_id = status_res.get("ilink_user_id")
                bot_tok = status_res.get("bot_token", "")
                binding = router.confirm_qr_binding(qr_val, user_id=usr_id, bot_token=bot_tok)
                if binding and binding.get("welcome"):
                    clawbot_channel.send_text(usr_id, binding["welcome"])
            self._send_json(status_res)
            return

        # 4. 系统运行状态与路由表
        if path == "/api/status":
            info = {
                "status": "running",
                "default_repo": router.default_repo,
                "ai_configured": cloud_ai.is_configured(),
                "ai_model": cloud_ai.model,
                "projects": router.projects,
                "user_bindings": router.user_bindings
            }
            self._send_json(info)
            return

        # 5. 查看当前客户与定制系统绑定表
        if path == "/api/bindings":
            self._send_json({
                "bindings": router.user_bindings,
                "pending_qrs": router.pending_qr_bindings
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        # 1. 网页模拟联调接口
        if path == "/api/chat":
            msg_text = payload.get("message", "")
            user_id = payload.get("user_id", "web_simulator")
            incoming = IncomingMessage(
                channel="web_sim",
                user_id=user_id,
                content=msg_text
            )
            reply = engine.process_incoming(incoming)
            self._send_json({"reply": reply})
            return

        # 2. 程序化发行定制软件专属二维码 API
        if path == "/api/tenant/bind-qrcode":
            repo = payload.get("repo", router.default_repo)
            name = payload.get("name", "定制系统")
            welcome = payload.get("welcome", f"您好！我是【{name}】的专属数字化技术经理。遇到任何使用疑问或改进建议，随时发我！")
            qr_res = clawbot_channel.get_qr_code()
            if qr_res.get("success"):
                router.register_pending_qr(qr_res["qrcode"], repo=repo, name=name, welcome=welcome)
                qr_res["software_name"] = name
                qr_res["repo"] = repo
            self._send_json(qr_res)
            return

        # 3. 企微 Webhook 预留通道
        if path == "/webhook/wecom":
            reply = wecom_channel.handle_webhook_payload(payload)
            self._send_json({"reply": reply})
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data: Any, code: int = 200):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

def run_server():
    clawbot_channel.start()
    wecom_channel.start()
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, BotHubHandler)
    print(f"============================================================")
    print(f"🚀 bot2issue 通用中枢已拉起！")
    print(f"🌐 统一控制台入口: http://127.0.0.1:{PORT}")
    print(f"📦 默认 GitHub 仓库: {router.default_repo}")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] 优雅关闭中...")
        clawbot_channel.stop()
        httpd.server_close()

if __name__ == "__main__":
    run_server()
