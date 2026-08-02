#!/usr/bin/env python3
"""从 Twilio WhatsApp 拉取客户消息，写回 data.json（由 GitHub Action 调用）。

配置（环境变量 / GitHub Secrets，缺失即安全跳过）：
  TWILIO_ACCOUNT_SID   Twilio 账号 SID
  TWILIO_AUTH_TOKEN    Twilio Auth Token
  WHATSAPP_FROM        你的 WhatsApp 号码（E.164，如 +14155238886）

说明：
  - 通过 Twilio Messages API 拉取"发往本号"的最近消息（即客户来讯），去重后写入
    data["whatsapp"]["messages"]，并更新 metrics.messages 与今日动态。
  - 若以后改用 Meta 官方 Cloud API，需要 webhook 接收实时消息（无法纯定时拉取），
    可在此函数内替换为对应实现。
"""
import os
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data.json"


def _norm_phone(p):
    return p.split(":", 1)[-1] if ":" in p else p


def sync_from_whatsapp(data):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    own = os.environ.get("WHATSAPP_FROM")
    if not (sid and token and own):
        print("[whatsapp] 未配置 Twilio 凭证，跳过")
        return False

    try:
        from twilio.rest import Client
    except ImportError:
        print("[whatsapp] 未安装 twilio 库（GitHub Action 会 pip install），本地跳过")
        return False

    try:
        client = Client(sid, token)
        msgs = client.messages.list(to=f"whatsapp:{own}", limit=50)
    except Exception as e:  # noqa: BLE001
        print(f"[whatsapp] 拉取失败: {e}")
        return False

    wa = data.setdefault("whatsapp", {"connected": True, "messages": []})
    wa["connected"] = True
    seen = {m.get("sid") for m in wa["messages"]}
    added = 0
    for m in msgs:
        if m.sid in seen:
            continue
        wa["messages"].insert(0, {
            "sid": m.sid,
            "from": _norm_phone(m.from_),
            "text": m.body or "",
            "time": m.date_sent.isoformat() if m.date_sent else "",
        })
        seen.add(m.sid)
        added += 1
    wa["messages"] = wa["messages"][:200]

    # 更新指标：客户留言数 = WhatsApp 来讯数（后续可与 Zoho 合并）
    data.setdefault("metrics", {})["messages"] = len(wa["messages"])

    # 同步到今日动态（去重，避免每日重复）
    today = data.setdefault("today", [])
    ids = {a.get("sid") for a in today if isinstance(a, dict)}
    for m in wa["messages"]:
        if m.get("sid") and m["sid"] not in ids:
            today.insert(0, {
                "sid": m["sid"],
                "tag": "WhatsApp",
                "cls": "green",
                "text": f"客户 {m['from']}：{m['text']}",
                "time": m["time"],
            })
            ids.add(m["sid"])
    data["today"] = today[:50]

    print(f"[whatsapp] 新增 {added} 条，共 {len(wa['messages'])} 条")
    return added > 0
