import re

def clean_references(text: str) -> str:
    """
    移除所有 ChatGPT 回覆來源引用標記。
    包含 【數字:數字†xxx】、〖數字:數字†xxx〗，以及單純的【數字:數字】或〖數字:數字〗。
    """
    text = re.sub(r'[【〖]\d+:\d+†.*?[】〗]', '', text)
    text = re.sub(r'[【〖]\d+:\d+[】〗]', '', text)
    return re.sub(r'\s{2,}', ' ', text).strip()