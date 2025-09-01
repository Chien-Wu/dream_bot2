"""Text processing utilities."""
import re


def count_chinese_characters(text: str) -> int:
    """
    Count Chinese characters in text.
    
    Args:
        text: Text to count characters
        
    Returns:
        Number of Chinese characters
    """
    # Count Chinese characters (CJK Unified Ideographs and Extensions)
    chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text)
    return len(chinese_chars)