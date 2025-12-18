import re

from config import get_config
from utils.token_counter import count_tokens


def is_html_wrapped(text):
    """判断字符串首尾是否由html tag包裹"""
    # 去掉前后空白
    text = text.strip()
    if not text.startswith('<') or not text.endswith('>'):
        return False
    # 匹配首tag
    match_start = re.match(r'^<(\w+)[^>]*>', text)
    if match_start:
        tag = match_start.group(1)
        # 匹配末尾闭合tag
        match_end = re.search(rf'</{tag}>\s*$', text, re.DOTALL)
        return bool(match_end)
    return False

def get_origin_contents(reranked_results,limit):
    '''
    展开重排结果并直接提取原始内容
    :param results:
    :return:
    '''
    # 根据重排结果提取内容
    temp_dict = {}  # key: (file_name, page_number), value: item
    others = []     # 存放没有页码的项

    for item in reranked_results:
        origin_content_list = item.get('origin_content', [])
        page_numbers_list = item.get('page_number', [])
        file_name = item.get('file_name', '')
        kb_name = item.get('kb_name', '')
        score = item.get('score', 0.0)
        custom_metadata = item.get('custom_metadata', {})
        search_content = item.get('content', "")

        if page_numbers_list and origin_content_list:
            n = min(len(origin_content_list), len(page_numbers_list))
            for i in range(n):
                page_number = page_numbers_list[i]
                key = (file_name, page_number)
                entry = {
                    "search_content": search_content,
                    "origin_content": origin_content_list[i],
                    "score": score,
                    "source": file_name,
                    "file_name": file_name,
                    "kb_name": kb_name,
                    "page_number": page_number,
                    "custom_metadata": custom_metadata
                }
                # 若已存在且score更低则跳过，否则替换
                if key not in temp_dict or score > temp_dict[key]["score"]:
                    temp_dict[key] = entry
        else:
            entry = {
                "search_content": search_content,
                "origin_content": item.get("content", ""),  # 使用content作为默认原始内容
                "score": score,
                "source": file_name,
                "file_name": file_name,
                "kb_name": kb_name,
                "page_number": None,  # 页码为空
                "custom_metadata": custom_metadata
            }
            others.append(entry)

    final_results = list(temp_dict.values()) + others

    # 如果没有找到任何带页码的内容，使用重排结果
    if not final_results and reranked_results:
        for res in reranked_results:
            entry = {
                "search_content": res["content"],
                "origin_content": res["content"],
                "score": res["score"],
                "source": res["file_name"],
                "file_name": res["file_name"],
                "kb_name": res["kb_name"],
                "page_number": None,
                "custom_metadata": res["custom_metadata"]
            }
            final_results.append(entry)

    # # limit 裁剪
    # if limit is not None:
    #     final_results = final_results[:limit]

    return final_results


def analyze_result(results,file_names,MAX_DOC_CONTENT_LENGTH = 30000):
    """
        处理知识库返回的检索结果，拼接内容和收集文档元数据。

        Args:
            results (list[dict]): 检索返回的结果列表，每个元素为文档相关dict。
            file_names (list[str]): 已处理过的文件名列表，会在本函数中追加新文件名。
            MAX_DOC_CONTENT_LENGTH (int): 初始最大内容长度，会根据token限制动态调整。
            max_token (int): 返回内容的最大token限制。

        Returns:
            Tuple[str, list[dict]]:
                content：拼接好的内容字符串，包含若干文档内容及必要的页眉。
                retrieved_docs_metadata：文档元信息列表（如分数、来源、页码等）。
    """
    # 处理返回的结果
    config = get_config()
    max_token = config.MAX_INPUT_TOKENS
    skip_header = False
    retrieved_docs_metadata = []
    file_names_set = set()
    content_body = ""
    for idx,doc in enumerate(results):
        doc_content = doc.get('origin_content', '')
        search_content = doc.get('search_content', "")
        doc_score = doc.get('score', 0.0)
        doc_source = doc.get('source', '')
        file_name = doc.get('file_name', '') or doc.get("file",'')
        page_number = doc.get('page_number',None)
        kb_name = doc.get('kb_name',None)

        retrieved_docs_metadata.append({
            "id":str(idx),
            "content":search_content,
            "score": doc_score,
            "source": doc_source,
            "file_name":file_name,
            "page_number":page_number,
            "kb_name":kb_name
        })
        if file_name and file_name not in file_names_set:
            file_names.append(file_name)
            file_names_set.add(file_name)
        # use_header = True
        if idx > 0:  # 第二次及以后
            if is_html_wrapped(doc_content):
                skip_header = True
            else:
                skip_header = False
        # if skip_header:
        #     use_header = False
        # header = f"-- page[{page_number}]\n" if (page_number is not None) else ""
        content_body += f"\n{doc_content}\n"
    file_names = list(file_names_set)

    current_len = min(MAX_DOC_CONTENT_LENGTH, len(content_body))
    truncated_content = content_body[:current_len]

    # 当token数量未达到上限时，逐步增加内容长度
    while count_tokens(truncated_content) < max_token and current_len < len(content_body):
        next_len = current_len + 3000
        # 如果增加后超过总长度，则直接使用全部内容
        if next_len >= len(content_body):
            truncated_content = content_body
            break

        next_truncated_content = content_body[:next_len]
        # 如果增加后的内容超出了token限制，则停止增加
        if count_tokens(next_truncated_content) >= max_token:
            break

        truncated_content = next_truncated_content
        current_len = next_len

    content_body = truncated_content


    if file_names:
        if len(file_names) > 1:
            file_names_str = ','.join(file_names)
        else:
            file_names_str = file_names[0]
        content = f"《{file_names_str}》\n{content_body}"
    else:
        content = content_body

    return content,retrieved_docs_metadata
