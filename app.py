import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent, FollowEvent
from line_helper import handle_line_message
from human_takeover import notify_admin

from db.db_init import init_user_threads_table

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

app = Flask(__name__)

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
messaging_api = MessagingApi(ApiClient(config))
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("LINE Webhook Error:", e)
        abort(400)
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    handle_line_message(event, messaging_api)

@handler.add(FollowEvent)
def handle_follow(event):
    try:
        user_id = event.source.user_id
        notify_admin(
            messaging_api=messaging_api,
            user_id=user_id,
            user_msg="新用戶加入 LINE Bot"
        )
    except Exception as e:
        import logging
        logging.exception("處理新用戶 FollowEvent 時發生錯誤：%s", e)

if __name__ == "__main__":
    init_user_threads_table()
    app.run(host='0.0.0.0', port=5001)
