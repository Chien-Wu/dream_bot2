import re
import logging

logger = logging.getLogger(__name__)

def is_messy(text: str) -> bool:
    if not isinstance(text, str):
        return True
    text = text.strip()

    # 判斷是不是明顯亂碼：過多奇怪符號
    messy_chars = re.findall(r'[^\w\s,.!?:;\'"「」\u4e00-\u9fffA-Za-z0-9]', text)
    if len(messy_chars) > 15 and len(messy_chars) > len(text) * 0.2:
        logger.info(f"明顯亂碼: {text}")
        return True

    # 連續無意義字元
    if re.search(r'(.)\1{8,}', text):
        logger.info(f"重複亂碼: {text}")
        return True

    # 很短但全是符號
    if len(text) < 20 and len(messy_chars) > 10:
        logger.info(f"短且符號過多: {text}")
        return True

    return False