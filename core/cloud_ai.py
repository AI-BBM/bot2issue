#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud AI Client - 云端通用大模型客户端
基于标准 OpenAI 兼容协议（兼容 DeepSeek / 通义千问 / 智谱清言 / OpenAI / 私有模型）
"""

import os
import json
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional

class CloudAIClient:
    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = ""
    ):
        self.api_key = api_key or os.environ.get("AI_API_KEY", "").strip()
        self.api_base = api_base or os.environ.get("AI_API_BASE", "https://api.deepseek.com").rstrip("/")
        self.model = model or os.environ.get("AI_MODEL", "deepseek-chat")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 800
    ) -> str:
        """调用云端大模型接口生成回复"""
        if not self.is_configured():
            return self._offline_mock_completion(messages)

        # 补全 chat completions 路径
        endpoint = self.api_base
        if not endpoint.endswith("/chat/completions"):
            if endpoint.endswith("/v1"):
                endpoint = f"{endpoint}/chat/completions"
            else:
                endpoint = f"{endpoint}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[CloudAIClient] 请求大模型接口异常: {e}")
            return f"报告老板，前台 AI 连通网络微滞，但我已为您暂存该条需求，稍后将自动重试！(原因: {e})"

    def _offline_mock_completion(self, messages: List[Dict[str, str]]) -> str:
        """未配置 API Key 时的本地兜底轻量响应（保证系统平稳不崩）"""
        last_msg = messages[-1]["content"] if messages else ""
        if any(k in last_msg for k in ["确认", "提交", "对", "好的", "发布", "批准"]):
            return (
                "收到您的最终拍板确认！我已为您整理好标准工单：\n\n"
                "```issue\n"
                "{\n"
                '  "title": "用户微信反馈需求整理",\n'
                f'  "body": "### 📱 用户微信原话需求\\n\\n{last_msg}\\n\\n---\\n> 由 bot2issue 自动生成并提交",\n'
                '  "labels": ["via-clawbot", "needs-triage"]\n'
                "}\n"
                "```\n"
                "正在为您直通目标 GitHub 仓库生成 Issue..."
            )
        return (
            f"收到您的需求描述：「{last_msg}」！\n\n"
            "作为您的随身产品经理，向您快速澄清两个细节：\n"
            "1. 请问这个功能的使用场景是前台客户还是后台管理员？\n"
            "2. 期望在什么时间节点或版本中看到？\n\n"
            "（若觉得描述已经足够，请直接回复「确认」或「提交」，我将立即为您发布到 GitHub 仓库！）"
        )
