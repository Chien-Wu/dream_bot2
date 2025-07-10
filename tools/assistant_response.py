import json
from typing import Tuple

def parse_assistant_response(response: str) -> Tuple[str, float]:
    """
    解析 Assistant 回傳的 JSON 格式，回傳 (文字, 信心分數)
    """
    try:
        data = json.loads(response)
        text = data.get("text", "").strip()
        confidence = float(data.get("confidence", 0))
        return text, confidence
    except Exception:
        return "", 0.0
