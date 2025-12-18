import os
import shutil
import tempfile

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

import pandas as pd

from config import get_config, logger
import logging

from fastapi import UploadFile

async def extract_document_content(file_paths: List[str], api_url: str = None, force_ocr: Optional[bool] = None,kb_token = None) -> str:
    """
    提取文档内容：优先本地解析可处理的文件，剩余文件调用外部API。
    Args:
        file_paths: 上传的文件路径列表
        api_url: API端点URL，如果为None，则仅进行本地处理
        force_ocr: 是否强制使用OCR，如果为None则使用全局配置
    Returns:
        提取的文档内容
    """
    config = get_config()
    # TOKEN = config.TOKEN
    # FILE_EXTRACTION_API = config.FILE_EXTRACTION_API
    try:

        if not file_paths:
            return ""

        # 可本地处理的文件类型
        LOCAL_PROCESSABLE_EXTENSIONS = {
            '.txt', '.md', '.json', '.log', '.html', '.htm',
            '.csv',  # CSV文件
            # '.xlsx', '.xls',  # Excel文件
        }

        # 图片文件类型，这些类型需要OCR处理
        IMAGE_EXTENSIONS = {
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'
        }

        local_contents = []
        files_to_send_to_api = []

        for file_path in file_paths:
            file_ext = os.path.splitext(file_path)[1].lower()
            content = ""

            try:
                if file_ext in LOCAL_PROCESSABLE_EXTENSIONS:
                    # 处理纯文本文件
                    if file_ext in ['.txt', '.md', '.json', '.log', '.html', '.htm']:
                        encodings = ['utf-8', 'latin-1', 'cp1252', 'gb18030', 'gbk', 'big5']
                        for encoding in encodings:
                            try:
                                with open(file_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                                break  # 读取成功就跳出
                            except UnicodeDecodeError:
                                continue  # 失败就尝试下一个编码
                        if not content:
                            raise UnicodeDecodeError("utf-8", b"", 0, 1, "No suitable encoding found")

                    # 处理Excel文件
                    elif file_ext in ['.xlsx', '.xls']:
                        dfs = pd.read_excel(file_path, sheet_name=None)
                        content = "\n\n".join([
                            f"Sheet: {sheet_name}\n{df.to_string(index=False)}"
                            for sheet_name, df in dfs.items()
                        ])

                    # 处理CSV文件
                    elif file_ext == '.csv':
                        encodings = ['utf-8', 'latin-1', 'cp1252', 'gb18030', 'gbk', 'big5']
                        for encoding in encodings:
                            try:
                                df = pd.read_csv(file_path, encoding=encoding)
                                content = df.to_string(index=False)
                                break
                            except UnicodeDecodeError:
                                continue
                        if not content:
                            raise UnicodeDecodeError("utf-8", b"", 0, 1, "No suitable encoding found for CSV")

                    if content:
                        local_contents.append(f"FILE: {os.path.basename(file_path)}\n{content}")
                    else:
                        raise Exception(f"No content extracted from {file_path}")

                else:
                    # 不能本地解析的文件加入 API 处理列表
                    files_to_send_to_api.append(file_path)

            except Exception as e:
                logger.error(f"Failed to process {file_path} locally: {str(e)}")
                files_to_send_to_api.append(file_path)  # 失败的文件也交给API处理

        api_content = ""
        if files_to_send_to_api:
            if not api_url:
                unsupported_files = [os.path.basename(fp) for fp in files_to_send_to_api]
                raise Exception(
                    f"Cannot process files: {', '.join(unsupported_files)}. "
                    "These file types require an external API, but no API URL was provided."
                )
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                for file_path in files_to_send_to_api:
                    # 正确地添加文件到FormData
                    file_name = os.path.basename(file_path)
                    data.add_field(
                        'files',
                        open(file_path, 'rb'),
                        filename=file_name,
                        content_type='application/octet-stream'  # 设置适当的内容类型
                    )

                # 确定是否启用OCR
                should_use_ocr = config.OCR_ENABLED  # 默认使用全局配置

                # 检查是否有图片文件需要OCR处理
                has_image_files = any(os.path.splitext(fp)[1].lower() in IMAGE_EXTENSIONS for fp in files_to_send_to_api)

                # 检查OCR配置冲突
                if force_ocr is True and should_use_ocr is False:
                    error_msg = "OCR功能已在全局配置中禁用，无法强制启用OCR。请联系管理员修改全局配置。"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # 确定最终的OCR设置
                # 1. 如果force_ocr参数明确指定了值且不与全局配置冲突，使用该值
                # 2. 如果有图片文件且全局OCR启用，则使用OCR
                # 3. 如果全局OCR禁用，则不使用OCR
                final_use_ocr = force_ocr if force_ocr is not None else (has_image_files and should_use_ocr)

                # 添加其他参数
                data.add_field('tables', "True")
                data.add_field('start_page', "0")
                data.add_field('end_page', "300")
                data.add_field('force_ocr', str(final_use_ocr))

                # 记录OCR使用情况
                logger.info(f"OCR使用情况: 全局设置={should_use_ocr}, 有图片文件={has_image_files}, 最终设置={final_use_ocr}")

                # 只设置Authorization头，不设置Content-Type
                if not kb_token:
                    kb_token = config.TOKEN
                headers = {
                    "Authorization": f"Bearer {kb_token}"
                }

                # 发送请求
                async with session.post(api_url, data=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Document extraction failed: {error_text}")
                        raise Exception(f"Document extraction failed with status {response.status}: {error_text}")
                    result = await response.json()
                    api_content = result.get("content", "")

        # 组合本地及API的结果
        return "\n\n---\n\n".join(filter(None, local_contents + [api_content]))

    except Exception as e:
        logger.exception("Error extracting document content")
        raise Exception(f"Error extracting document content: {str(e)}")



async def query_knowledge_base(
        kb_names: List[str],
        file_names: Any,  # 兼容 str 或 List
        top_k: int,
        top_n: int,
        key_weight: float,
        querys: List[str],
        api_url: str,
        kb_token: str,
        custom_filters: Any
) -> List[Dict[str, Any]]:
    """
    调用知识库API进行查询
    Args:
        kb_names: 知识库名称列表
        file_names: 文件名 (支持字符串或列表)
        top_k: 检索分片数量
        top_n: 重排后保留的文档分片数量
        key_weight: 关键词权重
        query: 查询文本
        api_url: API端点URL
        kb_token: 后台知识库所用到的token
    Returns:
        List[Dict]: 包含多个检索结果，每个结果包含content, score, source等字段
    """
    # config = get_config()  # ✅ 动态获取配置
    # TOKEN = config.TOKEN
    # DIFY_compatible = config.DIFY_compatible
    try:
        config = get_config()
        async with aiohttp.ClientSession() as session:
            # 确保 file_names 是 List
            if isinstance(file_names, str):
                file_names = [file_names]
            elif isinstance(file_names, list):
                file_names = [name for name in file_names if name.strip()]

            payload = {
                "kb_names": kb_names,
                "file_names": file_names,
                "custom_filters": custom_filters,
                "top_k": top_k,
                "n": top_n,
                "key_weight": key_weight,
                "querys": querys,
                "rerank_model":config.RERANK_MODEL
            }

            headers = {
                "Authorization": f"Bearer {kb_token}",
                "Content-Type": "application/json"
            }

            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Knowledge base query failed: {error_text}")
                    raise Exception(f"Knowledge base query failed with status {response.status}: {error_text}")

                result = await response.json()

                # final_results = []
                #
                # for res in result:
                #     content = res.get('content', '')
                #     score = res.get('score', 0.0)
                #     source = res.get('source', '未知来源')  # source 字段已经是 display_name
                #
                #     final_results.append({
                #         'content': content,
                #         'score': score,
                #         'source': source
                #     })

                # 直接返回结果列表
                return result

    except Exception as e:
        logger.exception("Error querying knowledge base")
        raise Exception(f"Error querying knowledge base: {str(e)}")
