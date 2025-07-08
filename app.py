import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest
from linebot.v3.webhook import WebhookHandler, MessageEvent
from line_helper import handle_line_message

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

if __name__ == "__main__":
    init_user_threads_table()
    app.run(host='0.0.0.0', port=5001)
