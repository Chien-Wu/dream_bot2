from linebot.v3.messaging import ReplyMessageRequest, TextMessage as LineTextMessage
import assistant_helper

def handle_line_message(event, messaging_api):
    if not hasattr(event.message, 'text'):
        return

    user_input = event.message.text
    user_id = event.source.user_id

    if user_input.strip() in ["重置", "重新開始"]:
        assistant_helper.reset_user_thread(user_id)
        reply = "你已經重新開始新的對話！"
    else:
        reply = assistant_helper.get_assistant_reply(user_id, user_input)

    # 回傳給 LINE
    if reply:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[LineTextMessage(text=reply)]
            )
        )
    else:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[LineTextMessage(text="抱歉，AI暫時沒有回應，請稍後再試！")]
            )
        )