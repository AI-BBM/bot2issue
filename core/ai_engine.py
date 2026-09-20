#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversational PM Engine - 智能产品经理对话引擎
核心职责：
1. 倾听客户的大白话与多模态输入（截图、语音、文字）；
2. 交互式引导：澄清业务边界、使用人群与验收标准；
3. 草案呈现与人机拍板确认卡点；
4. 确认后自动抽取结构化 Issue 并跨仓库发布。
"""

import os
import re
import json
import time
import urllib.request
from typing import Optional, Dict, Any, List

from channels.base import IncomingMessage
from core.session import SessionManager, Session
from core.router import ProjectRouter
from core.cloud_ai import CloudAIClient
from publishers.github_publisher import GitHubPublisher

class ConversationalPMEngine:
    def __init__(
        self,
        session_manager: SessionManager,
        router: ProjectRouter,
        ai_client: CloudAIClient,
        publisher: GitHubPublisher
    ):
        self.sessions = session_manager
        self.router = router
        self.ai = ai_client
        self.publisher = publisher

    def process_incoming(self, msg: IncomingMessage) -> str:
        """主业务入口：处理来自微信/企微的单条消息并返回管家式回复"""
        user_id = msg.user_id
        session = self.sessions.get_or_create(user_id, channel=msg.channel)

        raw_text = msg.content.strip()

        # 0. 撤回感知
        if msg.media_type == "revoke":
            if session.pending_issue:
                session.pending_issue = None
                self.sessions.save()
                return "已检测到您撤回了上一条消息！拟提单草案已帮您安全取消，随时可以重新发送。"
            return "已检测到您撤回了上一条消息，已同步清理上下文。"

        # 1. 快捷控制指令处理
        if raw_text in ["项目列表", "查看项目", "有哪些项目", "支持的项目", "help", "帮助"]:
            return self.router.format_projects_summary()

        if any(raw_text.startswith(k) for k in ["清空", "重置", "重新开始", "新建需求"]):
            session.clear()
            self.sessions.save()
            return "已为您重置会话上下文！请随时通过文字、语音或截图告诉我您或客户的新想法。"

        # 2. 解析目标仓库与项目路由 (支持微信暗桩自动绑定)
        target_repo, labels, cleaned_text, software_name = self.router.resolve_target(
            raw_text, user_id=user_id, current_repo=session.target_repo
        )
        if target_repo != session.target_repo:
            session.target_repo = target_repo

        # 2.5 希沃白板正向激励大屏 (class_motivation) 口头打分特快直通专线
        if "class_motivation" in session.target_repo.lower() or "class_motivation" in software_name.lower():
            whiteboard_url = os.environ.get("WHITEBOARD_URL", "http://127.0.0.1:8088").rstrip("/")
            try:
                wb_req = urllib.request.Request(
                    f"{whiteboard_url}/api/bot/command",
                    data=json.dumps({"text": cleaned_text}).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(wb_req, timeout=3) as wb_resp:
                    wb_data = json.loads(wb_resp.read().decode("utf-8"))
                    if wb_data.get("status") == "ok":
                        # 成功打分，秒级把大屏反馈回传给老师手机微信
                        return wb_data.get("reply", "✅ 口头打分已成功记录，白板大屏已同步响应！")
            except Exception as e:
                # 白板若未开机或网络暂时不通，记录日志并放行进入下方 PM 需求引导
                print(f"[ConversationalPMEngine] 尝试直通白板打分异常/跳过: {e}")

        # 3. 记录附件
        if msg.media_path:
            session.add_attachment(msg.media_path)

        # 4. 构建上下文与多模态补充提示
        media_notice = ""
        if msg.media_type == "image":
            media_notice = f"\n[用户发送了一张截图/照片，已保存在本地附件: {os.path.basename(msg.media_path)}]"
        elif msg.media_type in ["video", "file"]:
            media_notice = f"\n[用户发送了多媒体文件: {os.path.basename(msg.media_path)}]"

        user_turn_content = cleaned_text + media_notice
        if msg.ref_context:
            user_turn_content = f"[引用历史消息: {msg.ref_context}]\n{user_turn_content}"

        # 5. 提示词工程：资深数字化产品经理
        system_prompt = f"""你是专为定制系统【{software_name}】赋能的【资深数字化产品经理兼解决方案架构师】。
用户正在通过手机微信 (ClawBot) 或企业微信与你沟通该系统的使用体验、缺陷报错或新需求想法。

【当前定制系统与交付目标】
- 目标软件名称: 【{software_name}】
- 目标 GitHub 仓库: `{session.target_repo}`
- 预置标签: `{', '.join(labels)}`
- 已收集附件数量: {len(session.attachments)} 个

【行为守则与交付阶段】
1. 沟通风格：极高情商、客气干练、大白话交流。严禁给用户甩代码、JSON 报错或技术黑话。
2. 阶段一（需求引导与追问）：
   - 倾听用户的原话（文字、语音、随手拍截图）；
   - 像资深顾问一样，主动抛出 1~2 个最核心的业务场景问题（如在哪个模块发生、对业务操作有何影响、期望怎样算解决）；
   - 快速整理出初步的【需求草案预览】（大白话标题、核心痛点、建议验收标准）；
   - 提示用户：“如果您觉得当前描述已满足，请回复【确认】或【提交】，我将立即直通 GitHub 发布工单！”
3. 阶段二（人机拍板与结构化提单）：
   - 当且仅当用户明确表达了确认意向（例如回复“确认”、“提交”、“发布”、“对”、“好的”、“批准”、“就按这个做”等）：
   - 你必须在你的回复末尾，严格附带一个 ```issue 代码块，遵循 GitHub SSOT 规范：
```issue
{{
  "title": "大白话清晰标题 (例如: 【{software_name}】出库扫码报500且转圈优化)",
  "body": "### 🗣️ 客户微信原话 (Customer Verbatim)\\n...\\n\\n### 🎯 怎样算做成 (Definition of Done / 验收标准)\\n- 步骤1: ...\\n- 步骤2: ...\\n\\n### ⚙️ 关联定制系统\\n- 系统: {software_name}\\n- 仓库: {session.target_repo}",
  "labels": ["via-clawbot", "customer-request", "needs-triage"]
}}
```
4. 如果用户询问项目支持、或者切换仓库，热情指引他们使用 [#项目名] 快速切换。
"""

        # 组装上下文发送大模型
        messages = [{"role": "system", "content": system_prompt}]
        for m in session.messages[-8:]:
            messages.append(m)
        messages.append({"role": "user", "content": user_turn_content})

        # 6. 调用云端大模型
        reply_content = self.ai.chat_completion(messages)

        # 7. 检测是否触发了结构化提单信号 ```issue
        issue_match = re.search(r"```issue\s*([\s\S]*?)\s*```", reply_content)
        if issue_match:
            try:
                issue_data = json.loads(issue_match.group(1))
                raw_title = issue_data.get("title", f"需求整理-{int(time.time())}")
                if f"【{software_name}】" not in raw_title:
                    issue_title = f"【{software_name}】{raw_title}"
                else:
                    issue_title = raw_title
                issue_body = issue_data.get("body", cleaned_text)
                issue_labels = issue_data.get("labels", labels)

                # 拼接附件到 Issue Body (SSOT 规范)
                if session.attachments:
                    att_md = ["\n\n### 📎 微信随信附件资产 (Screenshots & Media Assets)"]
                    for idx, att in enumerate(session.attachments, 1):
                        bname = os.path.basename(att)
                        att_md.append(f"{idx}. 本地留档附件: `{bname}`")
                    issue_body += "\n".join(att_md)

                # 调取 GitHub 交付器创建真实 Issue
                res = self.publisher.create_issue(
                    repo=session.target_repo,
                    title=issue_title,
                    body=issue_body,
                    labels=issue_labels
                )

                # 剔除原始的 issue json 代码块
                clean_reply = re.sub(r"```issue\s*[\s\S]*?\s*```", "", reply_content).strip()

                if res.get("success"):
                    issue_num = res.get("issue_number", 0)
                    if issue_num:
                        self.router.register_issue_creator(
                            repo=session.target_repo,
                            issue_number=issue_num,
                            user_id=user_id,
                            software_name=software_name,
                            title=issue_title
                        )
                    card = self.publisher.format_success_card(
                        repo=res.get("repo", session.target_repo),
                        title=issue_title,
                        issue_url=res.get("issue_url", ""),
                        issue_num=issue_num
                    )
                    final_reply = (clean_reply + "\n\n" + card).strip()
                    # 提单完成，重置暂存
                    session.clear()
                    self.sessions.save()
                    return final_reply
                else:
                    err_hint = f"\n\n⚠️ 尝试同步至 GitHub 时遇到异常：{res.get('error', '未知错误')}\n建议检查 Token 权限或目标仓库是否存在。"
                    final_reply = clean_reply + err_hint
                    return final_reply

            except Exception as e:
                print(f"[ConversationalPMEngine] 解析 Issue 失败: {e}")

        # 8. 未触发提单，记录会话并保存
        session.add_message("user", user_turn_content)
        session.add_message("assistant", reply_content)
        self.sessions.save()

        return reply_content
