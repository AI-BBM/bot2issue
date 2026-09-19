#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issue Publisher - 跨仓库自动化工单交付器
支持通过 GITHUB_TOKEN 或本地已授权的 gh CLI 直通任何指定的 GitHub 仓库
"""

import os
import json
import time
import subprocess
import urllib.request
from typing import Dict, Any, List, Optional

class GitHubPublisher:
    def __init__(self, token: str = ""):
        self.token = token or os.environ.get("GITHUB_TOKEN", "").strip()
        if not self.token:
            self.token = self._get_token_from_gh_cli()

    def _get_token_from_gh_cli(self) -> str:
        """从本地 gh CLI 自动读取已登录的 GitHub 凭证"""
        try:
            res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return ""

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        在目标仓库 (owner/repo) 创建 Issue
        """
        repo = repo.strip()
        if not repo or "/" not in repo:
            return {"success": False, "error": f"无效的 GitHub 仓库路径: {repo}"}

        # 优先使用 REST API (若有 token)
        if self.token:
            url = f"https://api.github.com/repos/{repo}/issues"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Bot2Issue-Universal-Hub"
            }
            payload = {
                "title": title,
                "body": body,
                "labels": labels or ["via-clawbot", "needs-triage"]
            }
            if assignees:
                payload["assignees"] = assignees

            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return {
                        "success": True,
                        "issue_url": data.get("html_url", ""),
                        "issue_number": data.get("number", 0),
                        "repo": repo
                    }
            except urllib.error.HTTPError as he:
                err_msg = he.read().decode("utf-8", errors="ignore")
                print(f"[GitHubPublisher] API 建单失败 HTTP {he.code}: {err_msg}")
            except Exception as e:
                print(f"[GitHubPublisher] API 建单异常: {e}")

        # 降级使用本地 gh CLI
        try:
            cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
            for lbl in (labels or ["via-clawbot"]):
                cmd.extend(["--label", lbl])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                issue_url = res.stdout.strip()
                return {
                    "success": True,
                    "issue_url": issue_url,
                    "repo": repo
                }
            else:
                return {
                    "success": False,
                    "error": f"gh CLI 建单失败: {res.stderr.strip()}"
                }
        except Exception as e:
            return {"success": False, "error": f"执行 gh 命令异常: {e}"}

    def format_success_card(self, repo: str, title: str, issue_url: str, issue_num: int = 0) -> str:
        """生成推回微信的大白话成功通知卡片"""
        num_str = f"#{issue_num} " if issue_num else ""
        return (
            f"🎉 报告老板！需求已成功提报并同步至目标仓库：\n\n"
            f"📦 目标项目：`{repo}`\n"
            f"🏷️ 工单标题：{num_str}{title}\n"
            f"🔗 GitHub 工单链接：\n{issue_url}\n\n"
            f"已自动指派研发团队跟进，后续开发状态我将实时关注！您也可以继续随时发新需求！"
        )
