"""
Token计数工具，用于计算输入文本的token数量
"""
import os
import shutil

import tiktoken

from utils.file_manager import logger
from utils.tools import ROOT_PATH

tiktoken_cache_dir = os.path.join(ROOT_PATH,"tools")
cache_key = "s9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
target_filename = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
target_filepath = os.path.join(tiktoken_cache_dir, target_filename)
source_filename = "cl100k_base.tiktoken"
source_filepath = os.path.join(tiktoken_cache_dir, source_filename)

if not os.path.exists(target_filepath):
    # 若不存在，则复制当前目录下cl100k_base.tiktoken到目标路径
    shutil.copyfile(source_filepath, target_filepath)
    print(f"复制 {source_filepath} 到 {target_filepath}")
else:
    print(f"{target_filepath} 已存在")

os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# # encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoding = tiktoken.get_encoding("cl100k_base")
print(encoding.encode("Hello, world"))



def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    计算文本的token数量

    Args:
        text: 输入文本
        model: 使用的模型名称

    Returns:
        token数量
    """
    result = len(encoding.encode(text))
    logger.info(f"token count: {result}")
    return result

def validate_token_count(text: str, max_tokens: int, model: str = "gpt-4") -> bool:
    """
    验证文本token数是否超过限制

    Args:
        text: 输入文本
        max_tokens: 最大允许的token数
        model: 使用的模型名称

    Returns:
        如果未超过限制则返回True，否则返回False
    """
    return count_tokens(text, model) <= max_tokens
def truncate_text_by_tokens(text: str, max_tokens: int) -> str:
    """
    根据tiktoken的编码，将文本精确截断到不超过max_tokens。
    它通过直接操作token列表来保证精度，并处理解码时可能出现的边界问题。
    """
    # 编码为token ID列表
    encoded_tokens = encoding.encode(text)

    # 如果本身就没超限，直接返回原文本
    if len(encoded_tokens) <= max_tokens:
        return text

    # 直接截断token列表
    truncated_tokens = encoded_tokens[:max_tokens]

    # 解码被截断的token列表。
    # 使用try-except是因为截断点可能正好在一个多字节字符的中间，导致解码失败。
    # 如果失败，就不断减少最后一个token，直到能成功解码为止。
    while truncated_tokens:
        try:
            # 尝试解码
            truncated_text = encoding.decode(truncated_tokens)
            return truncated_text
        except UnicodeDecodeError:
            # 如果解码失败，移除最后一个token再试
            truncated_tokens = truncated_tokens[:-1]

    # 如果所有token都无法解码（极罕见情况），返回空字符串
    return ""
