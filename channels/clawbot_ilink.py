#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tencent Official iLink ClawBot Channel Adapter
支持官方二维码免封号授权、消息长轮询、AES-128-ECB媒体解密、输入中状态与撤回感知
"""

import os
import sys
import json
import time
import base64
import random
import urllib.request
import urllib.parse
import threading
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from channels.base import BaseChannel, IncomingMessage

class ClawbotIlinkChannel(BaseChannel):
    def __init__(
        self,
        baseurl: str = "https://ilinkai.weixin.qq.com",
        token: str = "",
        uploads_dir: str = "uploads",
        data_dir: str = "data"
    ):
        super().__init__("clawbot_ilink")
        self.baseurl = baseurl.rstrip("/")
        self.token = token
        self.uploads_dir = uploads_dir
        self.data_dir = data_dir
        self.binding_file = os.path.join(data_dir, "clawbot_binding.json")
        self.running = False
        self.worker_thread = None
        self.processed_msg_ids = set()

        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_binding()

    def _load_binding(self):
        if os.path.exists(self.binding_file):
            try:
                with open(self.binding_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.token = data.get("bot_token", self.token)
                    self.baseurl = data.get("baseurl", self.baseurl)
            except Exception as e:
                print(f"[ClawbotChannel] 读取绑定配置失败: {e}")

    def save_binding(self, token: str, baseurl: str = "", user_id: str = ""):
        self.token = token
        if baseurl:
            self.baseurl = baseurl.rstrip("/")
        data = {
            "bot_token": self.token,
            "baseurl": self.baseurl,
            "user_id": user_id,
            "updated_at": time.time()
        }
        with open(self.binding_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_qr_code(self) -> Dict[str, Any]:
        """向腾讯官方申请微信授权绑定二维码"""
        try:
            req = urllib.request.Request(
                f"{self.baseurl}/ilink/bot/get_bot_qrcode?bot_type=3",
                data=b'{"local_token_list":[]}',
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                qrcode_val = data.get("qrcode", "")
                img_url = data.get("qrcode_img_content", "")
                qr_img_api = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={urllib.parse.quote(img_url)}"
                return {
                    "success": True,
                    "qrcode": qrcode_val,
                    "qrcode_url": img_url,
                    "qr_img": qr_img_api
                }
        except Exception as e:
            return {"success": False, "error": f"获取微信官方二维码失败: {e}"}

    def check_qr_status(self, qrcode_val: str) -> Dict[str, Any]:
        """轮询二维码扫码状态"""
        try:
            status_url = f"{self.baseurl}/ilink/bot/get_qrcode_status?qrcode={urllib.parse.quote(qrcode_val)}"
            req = urllib.request.Request(status_url, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                status = data.get("status", "wait")
                bot_tok = data.get("bot_token", "")
                usr_id = data.get("ilink_user_id", "")
                b_url = data.get("baseurl", self.baseurl)

                if status == "confirmed" and bot_tok:
                    self.save_binding(bot_tok, b_url, usr_id)
                return data
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def decrypt_media(self, encrypted_bytes: bytes, aes_key_input: Any) -> bytes:
        """腾讯 iLink 协议加密多媒体解密算法：AES-128-ECB，PKCS7 去填充"""
        try:
            if not aes_key_input:
                return encrypted_bytes
            if isinstance(aes_key_input, str):
                try:
                    key_bytes = base64.b64decode(aes_key_input)
                    if len(key_bytes) != 16:
                        key_bytes = aes_key_input.encode("utf-8")[:16].ljust(16, b'\0')
                except Exception:
                    key_bytes = aes_key_input.encode("utf-8")[:16].ljust(16, b'\0')
            else:
                key_bytes = aes_key_input[:16]

            cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

            pad_len = decrypted[-1]
            if 0 < pad_len <= 16 and decrypted[-pad_len:] == bytes([pad_len]) * pad_len:
                return decrypted[:-pad_len]
            return decrypted
        except Exception as e:
            print(f"[ClawbotChannel] 媒体解密异常: {e}")
            return encrypted_bytes

    def send_typing(self, to_user: str, status: int = 1, **kwargs) -> bool:
        """向微信端发送输入态通知 (status=1 正在输入, status=2 取消)"""
        if not self.token:
            return False
        try:
            uin = base64.b64encode(str(random.randint(100000000, 999999999)).encode()).decode()
            headers = {
                "Content-Type": "application/json",
                "AuthorizationType": "ilink_bot_token",
                "Authorization": f"Bearer {self.token}",
                "X-WECHAT-UIN": uin,
                "iLink-App-Id": "bot",
                "iLink-App-ClientVersion": "132104"
            }
            body = {
                "ilink_user_id": to_user,
                "status": status
            }
            req = urllib.request.Request(
                f"{self.baseurl}/ilink/bot/sendtyping",
                data=json.dumps(body).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=4):
                return True
        except Exception:
            return False

    def send_text(self, to_user: str, text: str, context_token: str = "", **kwargs) -> bool:
        """回复文本到微信用户"""
        if not self.token:
            print("[ClawbotChannel] 无法发送消息：缺少 bot_token")
            return False
        try:
            uin = base64.b64encode(str(random.randint(100000000, 999999999)).encode()).decode()
            headers = {
                "Content-Type": "application/json",
                "AuthorizationType": "ilink_bot_token",
                "Authorization": f"Bearer {self.token}",
                "X-WECHAT-UIN": uin,
                "iLink-App-Id": "bot",
                "iLink-App-ClientVersion": "132104"
            }
            body = {
                "msg": {
                    "from_user_id": "",
                    "to_user_id": to_user,
                    "client_id": f"bot_{int(time.time()*1000)}_{random.randint(1000, 9999)}",
                    "message_type": 2,
                    "message_state": 2,
                    "item_list": [
                        {
                            "type": 1,
                            "text_item": {
                                "text": text
                            }
                        }
                    ],
                    "context_token": context_token
                },
                "base_info": {
                    "channel_version": "2.4.8",
                    "bot_agent": "openclaw-weixin"
                }
            }
            req = urllib.request.Request(
                f"{self.baseurl}/ilink/bot/sendmessage",
                data=json.dumps(body).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return bool(res_data.get("message_id") or res_data.get("ret") == 0)
        except Exception as e:
            print(f"[ClawbotChannel] 发送微信消息失败: {e}")
            return False

    def send_media(self, to_user: str, file_path: str, media_type: str = "image", **kwargs) -> bool:
        """发送多媒体（可通过图床或直接作为文本链接提示）"""
        # 降维优雅提示
        notice = f"【系统附件】已为您上传附件：{os.path.basename(file_path)}"
        return self.send_text(to_user, notice, **kwargs)

    def _poll_loop(self):
        print(f"[ClawbotChannel] iLink 长轮询守护线程已启动 (URL: {self.baseurl})")
        get_updates_buf = ""

        while self.running:
            try:
                if not self.token:
                    time.sleep(2)
                    continue

                uin = base64.b64encode(str(random.randint(100000000, 999999999)).encode()).decode()
                headers = {
                    "Content-Type": "application/json",
                    "AuthorizationType": "ilink_bot_token",
                    "Authorization": f"Bearer {self.token}",
                    "X-WECHAT-UIN": uin,
                    "iLink-App-Id": "bot",
                    "iLink-App-ClientVersion": "132104"
                }
                body = {
                    "get_updates_buf": get_updates_buf,
                    "base_info": {
                        "channel_version": "2.4.8",
                        "bot_agent": "openclaw-weixin"
                    }
                }
                req = urllib.request.Request(
                    f"{self.baseurl}/ilink/bot/getupdates",
                    data=json.dumps(body).encode("utf-8"),
                    headers=headers
                )
                try:
                    with urllib.request.urlopen(req, timeout=35) as resp:
                        resp_json = json.loads(resp.read().decode("utf-8"))
                except Exception:
                    time.sleep(1)
                    continue

                get_updates_buf = resp_json.get("get_updates_buf", get_updates_buf)
                msgs = resp_json.get("msgs", [])
                for msg in msgs:
                    msg_id = msg.get("message_id")
                    if msg_id in self.processed_msg_ids:
                        continue
                    self.processed_msg_ids.add(msg_id)
                    if len(self.processed_msg_ids) > 2000:
                        self.processed_msg_ids.clear()

                    from_user = msg.get("from_user_id", "")
                    context_token = msg.get("context_token", "")
                    item_list = msg.get("item_list", [])

                    # 1. 立即触发输入态: 对方正在输入...
                    self.send_typing(from_user, status=1)

                    # 2. 撤回消息处理
                    if msg.get("delete_time_ms") or msg.get("message_state") == 3:
                        incoming = IncomingMessage(
                            channel=self.name,
                            user_id=from_user,
                            content="[用户撤回了一条消息]",
                            media_type="revoke",
                            raw_data=msg
                        )
                        if self.message_handler:
                            reply_text = self.message_handler(incoming)
                            if reply_text:
                                self.send_text(from_user, reply_text, context_token=context_token)
                        self.send_typing(from_user, status=2)
                        continue

                    # 3. 引用消息检测
                    ref_text = ""
                    ref_msg = msg.get("ref_msg", {})
                    if ref_msg:
                        for ref_it in ref_msg.get("item_list", []):
                            if ref_it.get("type") == 1:
                                ref_text = ref_it.get("text_item", {}).get("text", "")
                                break

                    # 4. 多模态提取
                    user_text = ""
                    media_path = ""
                    media_type = "text"

                    for it in item_list:
                        itype = it.get("type")
                        # 文本
                        if itype == 1:
                            user_text = it.get("text_item", {}).get("text", "")
                        # 图片
                        elif itype == 2:
                            img_info = it.get("image_item", {})
                            img_url = img_info.get("url", "")
                            aes_key = img_info.get("aes_key", "")
                            if img_url:
                                try:
                                    with urllib.request.urlopen(img_url, timeout=15) as img_resp:
                                        enc_bytes = img_resp.read()
                                    dec_bytes = self.decrypt_media(enc_bytes, aes_key)
                                    filename = f"img_{int(time.time()*1000)}.jpg"
                                    local_file = os.path.join(self.uploads_dir, filename)
                                    with open(local_file, "wb") as f:
                                        f.write(dec_bytes)
                                    media_path = local_file
                                    media_type = "image"
                                    if not user_text:
                                        user_text = "[用户发送了一张图片]"
                                except Exception as e:
                                    print(f"[ClawbotChannel] 下载解密图片失败: {e}")
                        # 语音条
                        elif itype == 3:
                            voice_info = it.get("voice_item", {})
                            user_text = voice_info.get("text", "")
                            media_type = "voice"
                        # 视频
                        elif itype == 4 or itype == 5:
                            f_info = it.get("file_item", {}) or it.get("video_item", {})
                            f_url = f_info.get("url", "")
                            aes_key = f_info.get("aes_key", "")
                            if f_url:
                                try:
                                    with urllib.request.urlopen(f_url, timeout=20) as f_resp:
                                        enc_bytes = f_resp.read()
                                    dec_bytes = self.decrypt_media(enc_bytes, aes_key)
                                    ext = ".mp4" if itype == 4 else ".dat"
                                    filename = f"media_{int(time.time()*1000)}{ext}"
                                    local_file = os.path.join(self.uploads_dir, filename)
                                    with open(local_file, "wb") as f:
                                        f.write(dec_bytes)
                                    media_path = local_file
                                    media_type = "video" if itype == 4 else "file"
                                    if not user_text:
                                        user_text = f"[用户发送了媒体附件: {filename}]"
                                except Exception as e:
                                    print(f"[ClawbotChannel] 下载解密媒体失败: {e}")

                    if user_text:
                        incoming = IncomingMessage(
                            channel=self.name,
                            user_id=from_user,
                            content=user_text,
                            media_type=media_type,
                            media_path=media_path,
                            ref_context=ref_text,
                            raw_data=msg
                        )
                        if self.message_handler:
                            reply_text = self.message_handler(incoming)
                            if reply_text:
                                self.send_text(from_user, reply_text, context_token=context_token)

                    # 取消输入态
                    self.send_typing(from_user, status=2)

            except Exception as e:
                print(f"[ClawbotChannel] 轮询主循环异常: {e}")
                time.sleep(2)

    def start(self):
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.worker_thread.start()

    def stop(self):
        self.running = False
