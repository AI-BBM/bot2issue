#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Channel Interface - 通道抽象基类
支持多通道统一解耦接入（微信 ClawBot / 企业微信 WeCom）
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class IncomingMessage:
    def __init__(
        self,
        channel: str,
        user_id: str,
        content: str = "",
        user_name: str = "",
        media_type: str = "text",  # text, image, voice, video, file, revoke
        media_path: str = "",
        media_url: str = "",
        ref_context: str = "",
        raw_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ):
        self.channel = channel
        self.user_id = user_id
        self.user_name = user_name or user_id
        self.content = content.strip()
        self.media_type = media_type
        self.media_path = media_path
        self.media_url = media_url
        self.ref_context = ref_context.strip()
        self.raw_data = raw_data or {}
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"<IncomingMessage {self.channel}:{self.user_id} type={self.media_type} text={self.content[:20]!r}>"

class BaseChannel(ABC):
    """通用通道标准基类"""

    def __init__(self, name: str):
        self.name = name
        self.message_handler = None

    def register_handler(self, handler_func):
        """注册消息接收回调 (handler_func(IncomingMessage) -> str)"""
        self.message_handler = handler_func

    @abstractmethod
    def send_text(self, to_user: str, text: str, **kwargs) -> bool:
        """向用户回复文本消息"""
        pass

    @abstractmethod
    def send_typing(self, to_user: str, status: int = 1, **kwargs) -> bool:
        """发送正在输入状态 (status=1 输入中, status=2 取消)"""
        pass

    @abstractmethod
    def send_media(self, to_user: str, file_path: str, media_type: str = "image", **kwargs) -> bool:
        """向用户发送多媒体附件"""
        pass

    @abstractmethod
    def start(self):
        """启动通道守护进程或服务"""
        pass

    @abstractmethod
    def stop(self):
        """停止通道"""
        pass
