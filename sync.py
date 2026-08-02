#!/usr/bin/env python3
"""桑怡工作台 — 数据自动同步脚本（由 GitHub Action 定时/手动调用）。

职责：
  1. 刷新同步时间戳 updatedAt；
  2. 重新计算展会倒计时 daysLeft（每天自动递减，无需手工改）；
  3. 【可扩展】在 SYNC_SOURCES 中接入真实数据源（Zoho CRM / 邮件 / 表格等）后，
     自动把业务数据写回 data.json，首页即自动更新。

仅当数据发生实际变化时，GitHub Action 的 commit 步骤才会产生提交。
"""
import json
import datetime
from pathlib import Path

import sync_whatsapp  # WhatsApp 客户消息自动同步（凭证缺失时安全跳过）

DATA = Path(__file__).resolve().parent / "data.json"


def refresh_meta(data):
    """更新同步时间与展会倒计时，返回是否有变化。"""
    changed = False
    today = datetime.date.today().isoformat()
    if data.get("updatedAt") != today:
        data["updatedAt"] = today
        changed = True

    expo = data.get("expo") or {}
    start = expo.get("start")
    if start:
        try:
            days = (datetime.date.fromisoformat(start) - datetime.date.today()).days
            if expo.get("daysLeft") != days:
                expo["daysLeft"] = days
                changed = True
        except ValueError:
            pass
    return changed


# === 真实数据源接入区（示例，按需启用）================================
# 每个函数接收 data 字典，按需修改 data["metrics"] / data["today"] 等，
# 返回 True 表示产生了变化。接入后把函数加入 SYNC_SOURCES 即可生效。
#
# def sync_from_zoho(data):
#     """从 Zoho CRM 拉取客户/询盘/订单，写回 metrics 与 today。"""
#     # import os
#     # token = os.environ["ZOHO_TOKEN"]
#     # ... 调用 Zoho API，把结果写进 data ...
#     # return True  # 有变化时返回 True
#
# SYNC_SOURCES = [sync_from_zoho]
# =====================================================================

# WhatsApp 客户消息同步（Twilio API 拉取，凭证由环境变量 / GitHub Secrets 提供）
SYNC_SOURCES = [sync_whatsapp.sync_from_whatsapp]


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    changed = refresh_meta(data)
    for fn in SYNC_SOURCES:
        try:
            if fn(data):
                changed = True
        except Exception as e:  # noqa: BLE001
            print(f"[sync] {fn.__name__} 失败: {e}")

    if changed:
        DATA.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("[sync] 数据已更新")
    else:
        print("[sync] 无变化")


if __name__ == "__main__":
    main()
