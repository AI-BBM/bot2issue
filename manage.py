#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot2issue Management CLI - 定制软件专属微信接入管理工具
支持：
- 一键为任何定制软件发行专属微信接入二维码
- 查看当前所有客户微信绑定列表
- 解绑客户微信号
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import json

from core.router import ProjectRouter
from channels.clawbot_ilink import ClawbotIlinkChannel

def main():
    parser = argparse.ArgumentParser(description="bot2issue 定制软件专属微信绑定管理")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. bind: 为软件发行专属二维码
    bind_parser = subparsers.add_parser("bind", help="为特定定制软件发行专属微信接入二维码")
    bind_parser.add_argument("--repo", required=True, help="目标 GitHub 仓库 (如 client/smart-wms)")
    bind_parser.add_argument("--name", required=True, help="定制软件/系统名称 (如 智慧仓储系统)")
    bind_parser.add_argument("--welcome", default="", help="专属欢迎语")

    # 2. list: 查看当前绑定
    subparsers.add_parser("list", help="查看当前所有客户微信号与定制软件的绑定列表")

    # 3. unbind: 解除绑定
    unbind_parser = subparsers.add_parser("unbind", help="解除特定客户微信号的绑定")
    unbind_parser.add_argument("--user-id", required=True, help="客户微信 ID (ilink_user_id)")

    args = parser.parse_args()

    router = ProjectRouter()
    channel = ClawbotIlinkChannel()

    if args.command == "bind":
        welcome = args.welcome or f"您好！我是【{args.name}】的专属数字化服务经理。遇到任何系统使用疑问或改进建议，随时发我！"
        print(f"正在向腾讯官方 iLink 申请【{args.name}】专属二维码...")
        qr_res = channel.get_qr_code()
        if not qr_res.get("success"):
            print(f"❌ 申请二维码失败: {qr_res.get('error')}")
            sys.exit(1)

        qrcode = qr_res["qrcode"]
        router.register_pending_qr(qrcode, repo=args.repo, name=args.name, welcome=welcome)
        print(f"============================================================")
        print(f"✅ 专属接入二维码生成成功！")
        print(f"📦 目标定制系统: 【{args.name}】")
        print(f"🔗 目标代码仓库: `{args.repo}`")
        print(f"📱 微信扫码链接: {qr_res.get('qrcode_url')}")
        print(f"🖼️ 二维码预览图: {qr_res.get('qr_img')}")
        print(f"============================================================")
        print(f"💡 提示：将上述图片提供给客户扫码，扫码后该客户微信将永久直连 `{args.repo}`！")

    elif args.command == "list":
        bindings = router.user_bindings
        if not bindings:
            print("当前暂无已激活的客户微信绑定记录。")
            return
        print(f"📌 当前已绑定的客户与定制软件列表 (共 {len(bindings)} 条)：")
        print("-" * 65)
        for uid, b in bindings.items():
            print(f"• 客户微信ID: {uid}")
            print(f"  - 关联系统: 【{b.get('name')}】")
            print(f"  - 目标仓库: `{b.get('repo')}`")
            print("-" * 65)

    elif args.command == "unbind":
        uid = args.user_id
        if uid in router.user_bindings:
            del router.user_bindings[uid]
            router.save_bindings()
            print(f"✅ 已成功解除客户 {uid} 的软件仓库绑定。")
        else:
            print(f"⚠️ 未找到客户 {uid} 的绑定记录。")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
