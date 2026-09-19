#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeCom (企业微信) AI BOT / 自建应用通道适配器
预留平滑演进底座，与 ClawBot 共享统一业务引擎与 GitHub 提单中枢
"""

import os
import json
import time
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any

from channels.base import BaseChannel, IncomingMessage

class WeComChannel(BaseChannel):
    def __init__(
        self,
        corp_id: str = "",
        corp_secret: str = "",
        agent_id: str = "",
        token: str = "",
        encoding_aes_key: str = ""
    ):
        super().__init__("wecom")
        self.corp_id = corp_id or os.environ.get("WECOM_CORP_ID", "")
        self.corp_secret = corp_secret or os.environ.get("WECOM_CORP_SECRET", "")
        self.agent_id = agent_id or os.environ.get("WECOM_AGENT_ID", "")
        self.token = token or os.environ.get("WECOM_TOKEN", "")
        self.encoding_aes_key = encoding_aes_key or os.environ.get("WECOM_ENCODING_AES_KEY", "")
        self._access_token = ""
        self._token_expires_at = 0

    def get_access_token(self) -> str:
        """获取企微 access_token"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        if not (self.corp_id and self.corp_secret):
            return ""

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("errcode") == 0:
                    self._access_token = data.get("access_token", "")
                    self._token_expires_at = time.time() + data.get("expires_in", 7200) - 200
                    return self._access_token
                else:
                    print(f"[WeComChannel] 获取Token失败: {data}")
        except Exception as e:
            print(f"[WeComChannel] 请求Token异常: {e}")
        return ""

    def send_text(self, to_user: str, text: str, **kwargs) -> bool:
        """通过企业微信应用下发文本消息"""
        token = self.get_access_token()
        if not token:
            print("[WeComChannel] 企微未配置 corp_id/secret，暂无法下发真实企微消息")
            return False

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        body = {
            "touser": to_user,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": text
            },
            "safe": 0
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("errcode") == 0
        except Exception as e:
            print(f"[WeComChannel] 发送企微消息异常: {e}")
            return False

    def send_typing(self, to_user: str, status: int = 1, **kwargs) -> bool:
        # 企微应用暂无原生 typing 接口，保持空实现
        return True

    def send_media(self, to_user: str, file_path: str, media_type: str = "image", **kwargs) -> bool:
        notice = f"【企微附件通知】收到附件：{os.path.basename(file_path)}"
        return self.send_text(to_user, notice, **kwargs)

    def handle_webhook_payload(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """供 server.py 的 /webhook/wecom 接收并转为标准 IncomingMessage 处理"""
        from_user = raw_data.get("FromUserName") or raw_data.get("from_user", "wecom_user")
        msg_type = raw_data.get("MsgType") or raw_data.get("type", "text")
        content = raw_data.get("Content") or raw_data.get("text", "")

        incoming = IncomingMessage(
            channel="wecom",
            user_id=from_user,
            content=content,
            media_type=msg_type,
            raw_data=raw_data
        )
        if self.message_handler:
            return self.message_handler(incoming)
        return "已收到企微消息。"

    def start(self):
        print("[WeComChannel] 企微适配通道已挂载准备就绪 (支持 Webhook 回调接入)")

    def stop(self):
        pass
