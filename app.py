import os
import time
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage as LineTextMessage
from linebot.v3.webhook import WebhookHandler, MessageEvent
import openai
from dotenv import load_dotenv
load_dotenv()

# ====== 參數設定 ======
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "YOUR_OPENAI_ASSISTANT_ID") # Assistant id

# ====== 初始化 ======
app = Flask(__name__)

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
messaging_api = MessagingApi(ApiClient(config))
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# ====== LINE Webhook 入口 ======
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

# ====== 訊息事件處理 ======
@handler.add(MessageEvent)
def handle_message(event):
    # 只處理文字訊息
    if not hasattr(event.message, 'text'):
        return

    user_input = event.message.text

    # 1. 建立 OpenAI thread & 傳訊息
    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=OPENAI_ASSISTANT_ID
    )

    # 2. 輪詢等待 assistant 回覆（最多等 10 秒）
    for _ in range(10):
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)

    # 3. 取得 assistant 回覆
    reply = ""
    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            reply = msg.content[0].text.value
            break

    # 4. 回傳給 LINE
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
