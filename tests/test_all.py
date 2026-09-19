#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot2issue 自动化全套单元测试与集成测试
测试覆盖：
1. 项目路由与多仓库匹配 (ProjectRouter)
2. 腾讯 iLink 媒体解密算法 (AES-128-ECB)
3. 会话状态机与多轮上下文 (SessionManager)
4. PM 智能引导对话与确认拦截 (ConversationalPMEngine)
5. 企微适配通道消息标准化 (WeComChannel)
"""

import os
import sys
import unittest
import base64
import json

# 加入当前目录至 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from channels.base import IncomingMessage
from channels.clawbot_ilink import ClawbotIlinkChannel
from channels.wecom import WeComChannel
from core.session import SessionManager
from core.router import ProjectRouter
from core.cloud_ai import CloudAIClient
from core.ai_engine import ConversationalPMEngine
from publishers.github_publisher import GitHubPublisher

class DummyPublisher(GitHubPublisher):
    """用于测试的模拟 GitHub 发布器"""
    def __init__(self):
        self.created_issues = []

    def create_issue(self, repo, title, body, labels=None, assignees=None):
        record = {
            "success": True,
            "repo": repo,
            "title": title,
            "body": body,
            "labels": labels or [],
            "issue_url": f"https://github.com/{repo}/issues/999",
            "issue_number": 999
        }
        self.created_issues.append(record)
        return record

class TestBot2Issue(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = "data/test_run"
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.session_file = os.path.join(self.test_data_dir, "test_sessions.json")
        self.session_mgr = SessionManager(storage_path=self.session_file)
        self.router = ProjectRouter(config_path="config/projects.json")
        self.ai_client = CloudAIClient()
        self.publisher = DummyPublisher()
        self.engine = ConversationalPMEngine(
            self.session_mgr, self.router, self.ai_client, self.publisher
        )

    def test_01_router_resolution(self):
        """测试多项目/多仓库路由解析"""
        # 默认回退
        repo, labels, cleaned, name = self.router.resolve_target("我想加个登录按钮")
        self.assertEqual(repo, self.router.default_repo)
        self.assertEqual(cleaned, "我想加个登录按钮")

        # 动态指定完整 owner/repo
        repo2, labels2, cleaned2, name2 = self.router.resolve_target("[#someorg/superapp] 修复闪退")
        self.assertEqual(repo2, "someorg/superapp")
        self.assertEqual(cleaned2, "修复闪退")

        # 快捷别名指定
        repo3, labels3, cleaned3, name3 = self.router.resolve_target("[#bot2issue] 优化手机扫码体验")
        self.assertEqual(repo3, "michmingcao/bot2issue")
        self.assertEqual(cleaned3, "优化手机扫码体验")

    def test_02_media_decrypt(self):
        """测试腾讯 iLink AES-128-ECB 媒体解密"""
        channel = ClawbotIlinkChannel()
        raw_key = "1234567890123456"
        plain_text = b"Hello WeChat ClawBot Image Payload"
        # 手工使用 AES ECB 加密模拟腾讯发包
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        # PKCS7 pad to 16
        pad_len = 16 - (len(plain_text) % 16)
        padded = plain_text + bytes([pad_len]) * pad_len
        cipher = Cipher(algorithms.AES(raw_key.encode("utf-8")), modes.ECB(), backend=default_backend())
        enc = cipher.encryptor()
        encrypted = enc.update(padded) + enc.finalize()

        # 调用解密
        decrypted = channel.decrypt_media(encrypted, raw_key)
        self.assertEqual(decrypted, plain_text)

    def test_03_pm_conversational_guidance(self):
        """测试 PM 智能引导式对话"""
        user_msg = IncomingMessage(
            channel="clawbot",
            user_id="test_boss",
            content="[#bot2issue] 我们需要一个微信导出报表功能"
        )
        reply = self.engine.process_incoming(user_msg)
        # 验证 PM 回复包含提问或引导
        self.assertTrue(len(reply) > 10)
        self.assertIn("bot2issue", reply.lower() + self.session_mgr.get_or_create("test_boss").target_repo.lower())

    def test_04_user_confirmation_and_issue_creation(self):
        """测试用户回复确认时触发结构化提单"""
        # 第一轮: 提出需求
        msg1 = IncomingMessage(
            channel="clawbot",
            user_id="test_boss_2",
            content="详情页希望加一个导出Excel按钮"
        )
        self.engine.process_incoming(msg1)

        # 第二轮: 用户确认拍板
        msg2 = IncomingMessage(
            channel="clawbot",
            user_id="test_boss_2",
            content="对，确认提交"
        )
        reply2 = self.engine.process_incoming(msg2)
        # 验证是否成功调用创建了 Issue
        self.assertTrue(len(self.publisher.created_issues) > 0)
        created = self.publisher.created_issues[-1]
        self.assertIn("github.com", reply2)
        self.assertEqual(created["issue_number"], 999)

    def test_05_wecom_adapter(self):
        """测试企业微信通道消息转接入"""
        wecom = WeComChannel()
        wecom.register_handler(lambda msg: f"企微收到: {msg.content}")

        raw_payload = {
            "FromUserName": "wecom_staff_01",
            "MsgType": "text",
            "Content": "企微员工测试消息"
        }
        res = wecom.handle_webhook_payload(raw_payload)
        self.assertEqual(res, "企微收到: 企微员工测试消息")

    def test_06_server_module_and_routes(self):
        """测试 server.py 模块导入无语法崩溃与关键端点解析"""
        import server
        self.assertIsNotNone(server.BotHubHandler)
        self.assertEqual(server.router.default_repo, "michmingcao/bot2issue")

    def test_07_programmatic_qr_binding_and_routing(self):
        """测试后台程序化暗桩绑定与零标签客户自动路由"""
        qr_code = "test_qr_wms_999"
        target_repo = "clientA/smart-wms"
        software_name = "智慧仓储管理系统"

        # 1. 后台程序化登记待扫码专属二维码
        self.router.register_pending_qr(qr_code, repo=target_repo, name=software_name)
        self.assertIn(qr_code, self.router.pending_qr_bindings)

        # 2. 客户微信扫码确认落锁
        client_uid = "wx_wms_manager_001"
        binding = self.router.confirm_qr_binding(qr_code, user_id=client_uid)
        self.assertEqual(binding["repo"], target_repo)
        self.assertEqual(binding["name"], software_name)

        # 3. 客户发消息零标签，自动识别目标软件与仓库
        repo, labels, clean_text, name = self.router.resolve_target("出库单扫码一直卡顿转圈500", user_id=client_uid)
        self.assertEqual(repo, target_repo)
        self.assertEqual(name, software_name)

        # 4. 驱动 PM 对话与确认建单闭环
        msg1 = IncomingMessage(channel="clawbot", user_id=client_uid, content="出库单扫码一直卡顿转圈500")
        self.engine.process_incoming(msg1)

        msg2 = IncomingMessage(channel="clawbot", user_id=client_uid, content="好的，确认发布工单")
        self.engine.process_incoming(msg2)

        # 验证建单已精准直达 clientA/smart-wms 仓库
        self.assertTrue(len(self.publisher.created_issues) > 0)
        last_issue = self.publisher.created_issues[-1]
        self.assertEqual(last_issue["repo"], target_repo)
        self.assertIn("智慧仓储", last_issue["title"])

if __name__ == "__main__":
    unittest.main()
