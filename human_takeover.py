import os
from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "U35194e4ec4a34d20c3b9109c8a5aee34")

def notify_admin(
    messaging_api: MessagingApi,
    user_id: str,
    user_msg: str,
    ai_reply: str = "",
    confidence: float = None
):
    try:
        profile = messaging_api.get_profile(user_id)
        user_name = profile.display_name
    except Exception:
        user_name = "(無法取得)"

    admin_text = (
        "[人工接管通知]\n"
        f"【使用者】{user_name}（{user_id}）\n"
        f"【用戶訊息】{user_msg}\n"
        f"【AI 建議回覆】{ai_reply or 'AI 無法判斷或未回應'}\n"
        f"【AI 信心分數】{confidence if confidence is not None else '未知'}"
    )

    try:
        messaging_api.push_message(
            PushMessageRequest(
                to=ADMIN_USER_ID,
                messages=[TextMessage(text=admin_text)]
            )
        )
    except Exception as e:
        import logging
        logging.exception("推送管理者通知失敗：%s", e)