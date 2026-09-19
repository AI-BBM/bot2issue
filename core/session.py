#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager - 多用户多轮对话状态机
维护与微信/企微用户的连续交互上下文、暂存附件与拟提单草案
"""

import os
import json
import time
import threading
from typing import Dict, Any, List, Optional

class Session:
    def __init__(self, user_id: str, channel: str = "clawbot"):
        self.user_id = user_id
        self.channel = channel
        self.project_id = ""          # 当前聚焦的项目/仓库 ID
        self.target_repo = ""        # 当前目标 GitHub 仓库 (owner/repo)
        self.messages: List[Dict[str, str]] = []  # 多轮对话历史
        self.attachments: List[str] = []         # 上传的媒体文件路径
        self.pending_issue: Optional[Dict[str, Any]] = None # 等待用户拍板确认的 Issue 草案
        self.created_at = time.time()
        self.updated_at = time.time()

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        # 上限保护：保持最近 20 条，避免上下文膨胀
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]
        self.updated_at = time.time()

    def add_attachment(self, file_path: str):
        if file_path and file_path not in self.attachments:
            self.attachments.append(file_path)
            self.updated_at = time.time()

    def clear(self):
        self.messages.clear()
        self.attachments.clear()
        self.pending_issue = None
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "channel": self.channel,
            "project_id": self.project_id,
            "target_repo": self.target_repo,
            "messages": self.messages,
            "attachments": self.attachments,
            "pending_issue": self.pending_issue,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        s = cls(d.get("user_id", ""), d.get("channel", "clawbot"))
        s.project_id = d.get("project_id", "")
        s.target_repo = d.get("target_repo", "")
        s.messages = d.get("messages", [])
        s.attachments = d.get("attachments", [])
        s.pending_issue = d.get("pending_issue")
        s.created_at = d.get("created_at", time.time())
        s.updated_at = d.get("updated_at", time.time())
        return s

class SessionManager:
    def __init__(self, storage_path: str = "data/sessions.json"):
        self.storage_path = storage_path
        self.lock = threading.RLock()
        self.sessions: Dict[str, Session] = {}
        self._load()

    def _load(self):
        with self.lock:
            if os.path.exists(self.storage_path):
                try:
                    with open(self.storage_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for uid, item in data.items():
                            self.sessions[uid] = Session.from_dict(item)
                except Exception as e:
                    print(f"[SessionManager] 加载会话历史异常: {e}")

    def save(self):
        with self.lock:
            try:
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                out = {uid: s.to_dict() for uid, s in self.sessions.items()}
                with open(self.storage_path, "w", encoding="utf-8") as f:
                    json.dump(out, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[SessionManager] 持久化会话异常: {e}")

    def get_or_create(self, user_id: str, channel: str = "clawbot") -> Session:
        with self.lock:
            if user_id not in self.sessions:
                self.sessions[user_id] = Session(user_id, channel)
            return self.sessions[user_id]
