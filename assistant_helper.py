import os
import openai
import time
import thread_manager

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "YOUR_OPENAI_ASSISTANT_ID")
openai.api_key = OPENAI_API_KEY

def get_assistant_reply(user_id, user_input):
    thread_id = thread_manager.get_thread_id(user_id)
    if not thread_id:
        thread = openai.beta.threads.create()
        thread_id = thread.id
        thread_manager.set_thread_id(user_id, thread_id)

    openai.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input,
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=OPENAI_ASSISTANT_ID
    )
    for _ in range(30):
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    reply = ""
    for msg in messages.data:
        if msg.role == "assistant":
            if msg.content and hasattr(msg.content[0], "text") and hasattr(msg.content[0].text, "value"):
                reply = msg.content[0].text.value
                break
    return reply

def reset_user_thread(user_id):
    thread_manager.reset_thread_id(user_id)