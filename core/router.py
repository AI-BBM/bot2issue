#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Project & Multi-Repo Router - 多项目/多仓库智能路由网关
根据对话前缀、Bot 标识或上下文，精准定位目标 GitHub 仓库
"""

import os
import re
import json
from typing import Dict, Any, Optional, Tuple, List

class ProjectRouter:
    def __init__(self, config_path: str = "config/projects.json"):
        self.config_path = config_path
        self.default_repo = os.environ.get("DEFAULT_GITHUB_REPO", "michmingcao/bot2issue")
        self.default_labels = ["via-bot", "needs-triage"]
        self.projects: List[Dict[str, Any]] = []
        self.load_config()

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

    def resolve_target(self, text: str, current_repo: str = "") -> Tuple[str, List[str], str]:
        """
        解析文本中的目标仓库指令与纯净文本
        返回: (target_repo, labels, cleaned_text)
        """
        cleaned_text = text.strip()

        # 1. 检查快捷标签语法，例如: [#crm] 或 [#pos-system] 或 [#owner/repo]
        tag_match = re.match(r"^\[#([a-zA-Z0-9_\-\./]+)\]\s*(.*)$", cleaned_text)
        if tag_match:
            specifier = tag_match.group(1).lower()
            cleaned_text = tag_match.group(2).strip()

            # 若直接指定了完整 repo (含斜杠)
            if "/" in specifier:
                return specifier, self.default_labels, cleaned_text

            # 在 projects 列表中根据 id 或 keywords 查找
            for p in self.projects:
                if specifier == p.get("id", "").lower() or specifier in [k.lower() for k in p.get("keywords", [])]:
                    return p.get("repo", self.default_repo), p.get("labels", self.default_labels), cleaned_text

        # 2. 检查会话已有设定的 target_repo
        if current_repo:
            # 找到对应 project 的 labels
            for p in self.projects:
                if p.get("repo", "").lower() == current_repo.lower():
                    return current_repo, p.get("labels", self.default_labels), cleaned_text
            return current_repo, self.default_labels, cleaned_text

        # 3. 兜底使用全局默认配置
        return self.default_repo, self.default_labels, cleaned_text

    def find_project_by_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        kw = keyword.strip().lower()
        for p in self.projects:
            if kw == p.get("id", "").lower() or kw in [k.lower() for k in p.get("keywords", [])]:
                return p
        return None

    def add_or_update_project(self, project_id: str, repo: str, name: str = "", keywords: Optional[List[str]] = None, labels: Optional[List[str]] = None):
        for p in self.projects:
            if p.get("id") == project_id:
                p["repo"] = repo
                if name: p["name"] = name
                if keywords is not None: p["keywords"] = keywords
                if labels is not None: p["labels"] = labels
                self.save_config()
                return p
        new_p = {
            "id": project_id,
            "name": name or project_id,
            "repo": repo,
            "keywords": keywords or [project_id],
            "labels": labels or self.default_labels
        }
        self.projects.append(new_p)
        self.save_config()
        return new_p

    def format_projects_summary(self) -> str:
        """返回格式化的可用项目列表"""
        lines = ["📌 当前中枢支持的直达项目仓库列表："]
        for p in self.projects:
            kws = "/".join(p.get("keywords", []))
            lines.append(f"• 【{p.get('name', p.get('id'))}】")
            lines.append(f"  - 目标仓库: `{p.get('repo')}`")
            lines.append(f"  - 快捷指令: `[#{p.get('id')}]` 或 包含关键字 `{kws}`")
        lines.append(f"\n🌐 未指定时，默认派发至: `{self.default_repo}`")
        lines.append("💡 提示：您可直接发诸如 `[#crm] 修复登录异常` 快速定向提单！")
        return "\n".join(lines)
