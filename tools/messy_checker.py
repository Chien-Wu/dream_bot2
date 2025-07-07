import re
import logging

logger = logging.getLogger(__name__)

def is_messy(text: str) -> bool:
    """檢查輸入文字是否為亂碼/不合理內容。"""
    if not isinstance(text, str):
        return True
    text = text.strip()

    # 常見錯誤訊息、exception 或 API 回傳
    if re.search(r'(error|stack trace|traceback|exception|invalid|not found|bad request|KeyError|TypeError|RuntimeError)', text, re.I):
        return True

    # 明顯不是人類語言：過多特殊符號
    if len(re.findall(r'[^\w\s,.!?:;\'"「」\u4e00-\u9fffA-Za-z0-9]', text)) > 30:
        return True

    # 連續奇怪字元
    if re.search(r'(.)\1{8,}', text):
        return True

    # 含有特殊佔位符或 html/xml 標籤
    if re.search(r'<.*?>', text):
        return True

    return False