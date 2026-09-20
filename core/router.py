#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Project & Multi-Repo Router - 多软件/多仓库智能路由与暗桩绑定引擎
支持：
1. 后台程序化关联：为任意定制软件发行专属二维码，扫码即落锁
2. 客户零门槛免指定：已绑定的微信客户直接对话，自动分流至特定仓库
3. 动态标签与全项目列表查询
"""

import os
import re
import json
import time
from typing import Dict, Any, Optional, Tuple, List

class ProjectRouter:
    def __init__(
        self,
        config_path: str = "config/projects.json",
        bindings_path: str = "data/bindings.json"
    ):
        self.config_path = config_path
        self.bindings_path = bindings_path
        self.default_repo = os.environ.get("DEFAULT_GITHUB_REPO", "AI-BBM/bot2issue")
        self.default_labels = ["via-clawbot", "needs-triage"]
        self.projects: List[Dict[str, Any]] = []

        # 客户微信持久化暗桩绑定表
        self.user_bindings: Dict[str, Dict[str, Any]] = {}
        # 待核销的临时二维码关联表 {qrcode: {repo, name, welcome, labels}}
        self.pending_qr_bindings: Dict[str, Dict[str, Any]] = {}
        # 工单与微信提单人反向关联表 {"repo#issue_num": {user_id, software_name, title, created_at}}
        self.issue_bindings: Dict[str, Dict[str, Any]] = {}

        self.load_config()
        self.load_bindings()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.default_repo = data.get("default_repo", self.default_repo)
                    self.default_labels = data.get("default_labels", self.default_labels)
                    self.projects = data.get("projects", [])
            except Exception as e:
                print(f"[ProjectRouter] 加载项目路由配置失败: {e}")

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            data = {
                "default_repo": self.default_repo,
                "default_labels": self.default_labels,
                "projects": self.projects
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ProjectRouter] 保存路由配置异常: {e}")

    def load_bindings(self):
        if os.path.exists(self.bindings_path):
            try:
                with open(self.bindings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_bindings = data.get("user_bindings", {})
                    self.pending_qr_bindings = data.get("pending_qr_bindings", {})
                    self.issue_bindings = data.get("issue_bindings", {})
            except Exception as e:
                print(f"[ProjectRouter] 加载绑定表失败: {e}")

    def save_bindings(self):
        try:
            os.makedirs(os.path.dirname(self.bindings_path), exist_ok=True)
            data = {
                "user_bindings": self.user_bindings,
                "pending_qr_bindings": self.pending_qr_bindings,
                "issue_bindings": self.issue_bindings,
                "updated_at": time.time()
            }
            with open(self.bindings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ProjectRouter] 保存绑定表异常: {e}")

    def register_issue_creator(self, repo: str, issue_number: int, user_id: str, software_name: str = "", title: str = ""):
        """登记工单提单人微信号，支持后续闭环通知"""
        key = f"{repo.strip().lower()}#{issue_number}"
        self.issue_bindings[key] = {
            "user_id": user_id,
            "repo": repo,
            "issue_number": issue_number,
            "software_name": software_name,
            "title": title,
            "created_at": time.time()
        }
        self.save_bindings()

    def get_issue_creator(self, repo: str, issue_number: int) -> Optional[Dict[str, Any]]:
        key = f"{repo.strip().lower()}#{issue_number}"
        return self.issue_bindings.get(key)

    # --------------------------------------------------------------------------
    # 程序化暗桩绑定机制 (Programmatic QR & User Binding)
    # --------------------------------------------------------------------------
    def register_pending_qr(
        self,
        qrcode: str,
        repo: str,
        name: str = "",
        welcome: str = "",
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """为特定定制软件登记待扫码专属二维码"""
        entry = {
            "qrcode": qrcode,
            "repo": repo.strip() or self.default_repo,
            "name": name.strip() or repo.split("/")[-1],
            "welcome": welcome.strip(),
            "labels": labels or self.default_labels,
            "created_at": time.time()
        }
        self.pending_qr_bindings[qrcode] = entry
        self.save_bindings()
        return entry

    def confirm_qr_binding(self, qrcode: str, user_id: str, bot_token: str = "") -> Optional[Dict[str, Any]]:
        """扫码确认瞬间，将客户微信号永久落锁至对应软件仓库"""
        if not user_id:
            return None

        # 检查是否有预设的专属二维码绑定
        meta = self.pending_qr_bindings.get(qrcode)
        if not meta:
            # 兜底使用默认配置
            meta = {
                "repo": self.default_repo,
                "name": "通用支持中枢",
                "welcome": "您好！我是您的随身数字化产品经理。",
                "labels": self.default_labels
            }

        binding_record = {
            "user_id": user_id,
            "bot_token": bot_token,
            "repo": meta.get("repo", self.default_repo),
            "name": meta.get("name", "定制软件系统"),
            "welcome": meta.get("welcome", ""),
            "labels": meta.get("labels", self.default_labels),
            "bound_at": time.time()
        }

        # 永久写入客户绑定表
        self.user_bindings[user_id] = binding_record
        if bot_token:
            self.user_bindings[f"bot_{bot_token[:10]}"] = binding_record

        # 清理已核销的临时绑定
        if qrcode in self.pending_qr_bindings:
            del self.pending_qr_bindings[qrcode]

        self.save_bindings()
        print(f"[ProjectRouter] 客户 {user_id} 已成功永久绑定至定制系统【{binding_record['name']}】({binding_record['repo']})")
        return binding_record

    def get_user_binding(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_bindings.get(user_id)

    # --------------------------------------------------------------------------
    # 动态路由解析
    # --------------------------------------------------------------------------
    def resolve_target(
        self,
        text: str,
        user_id: str = "",
        current_repo: str = ""
    ) -> Tuple[str, List[str], str, str]:
        """
        根据用户身份、前缀指令与配置，精准解析目标仓库
        返回: (target_repo, labels, cleaned_text, software_name)
        """
        cleaned_text = text.strip()

        # 1. 显式前缀指令最高优先（如高级管理员临时切仓 [#crm]）
        tag_match = re.match(r"^\[#([a-zA-Z0-9_\-\./]+)\]\s*(.*)$", cleaned_text)
        if tag_match:
            specifier = tag_match.group(1).lower()
            cleaned_text = tag_match.group(2).strip()

            if "/" in specifier:
                return specifier, self.default_labels, cleaned_text, specifier.split("/")[-1]

            for p in self.projects:
                if specifier == p.get("id", "").lower() or specifier in [k.lower() for k in p.get("keywords", [])]:
                    return p.get("repo", self.default_repo), p.get("labels", self.default_labels), cleaned_text, p.get("name", p.get("id"))

        # 2. 客户暗桩绑定优先（零感知：客户无需打任何标签）
        if user_id and user_id in self.user_bindings:
            bound = self.user_bindings[user_id]
            return bound.get("repo", self.default_repo), bound.get("labels", self.default_labels), cleaned_text, bound.get("name", "定制系统")

        # 3. 会话中途已有仓库
        if current_repo:
            for p in self.projects:
                if p.get("repo", "").lower() == current_repo.lower():
                    return current_repo, p.get("labels", self.default_labels), cleaned_text, p.get("name", p.get("id"))
            return current_repo, self.default_labels, cleaned_text, current_repo.split("/")[-1]

        # 4. 全局默认兜底
        return self.default_repo, self.default_labels, cleaned_text, "默认需求池"

    def format_projects_summary(self) -> str:
        """返回格式化的可用项目与当前绑定列表"""
        lines = ["📌 当前中枢支持的定制软件与代码仓库："]
        for p in self.projects:
            lines.append(f"• 【{p.get('name', p.get('id'))}】 ➔ `{p.get('repo')}` (指令: `[#{p.get('id')}]`)")
        if self.user_bindings:
            lines.append(f"\n👥 已激活客户专属绑定数: {len(self.user_bindings)} 个定制端点")
        lines.append(f"\n🌐 全局默认仓库: `{self.default_repo}`")
        return "\n".join(lines)
