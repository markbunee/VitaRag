import os
import json
import asyncio
import tempfile

from api.db.services.document_service import DocumentService
from api.db.services.file2document_service import File2DocumentService
from common import settings

from graph.event_emitter import EventEmitter
from graph.workflow.node_functions import (
    document_preprocessing_node,
    summary_extraction_node,
    summary_generator_node,
    final_response_node,
)
from common.misc_utils import get_uuid


async def _run_and_collect(state, flow: str):
    emitter = EventEmitter(get_uuid(), "")
    if state.get("file_paths"):
        async for _ in document_preprocessing_node(state, emitter):
            pass

    if flow == "extract":
        state["classification"] = "论文类型"
        async for _ in summary_extraction_node(state, emitter):
            pass
    else:
        state["classification"] = "其他类型"
        async for _ in summary_generator_node(state, emitter):
            pass

    final = None
    async for event in final_response_node(state, emitter):
        if event.get("event") == "message":
            data = json.loads(event.get("data", "{}"))
            if data.get("events") == "final_message":
                final = data.get("content")
                break
    return final


def summarize_input(text=None, doc_id=None, file_bytes=None, filename=None, flow="extract"):
    temp_paths = []
    try:
        state = {}
        if text:
            state["extracted_texts"] = [text]
            state["processed_text"] = text
        elif doc_id:
            e, doc = DocumentService.get_by_id(doc_id)
            if not e:
                raise LookupError("Document not found!")
            b, n = File2DocumentService.get_storage_address(doc_id=doc_id)
            blob = settings.STORAGE_IMPL.get(b, n)
            suffix = os.path.splitext(getattr(doc, "name", ""))[1]
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tf.write(blob)
            tf.close()
            temp_paths.append(tf.name)
            state["file_paths"] = temp_paths
        elif file_bytes is not None:
            suffix = os.path.splitext(filename or "")[1] or ".txt"
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tf.write(file_bytes)
            tf.close()
            temp_paths.append(tf.name)
            state["file_paths"] = temp_paths
        else:
            return {}
        content = asyncio.run(_run_and_collect(state, flow=flow))
        for p in temp_paths or []:
            try:
                os.unlink(p)
            except Exception:
                pass
        if not content:
            return {}
        try:
            return json.loads(content)
        except Exception:
            if flow == "extract":
                return {"type": "论文类型", "summary": content, "keywords": []}
            return {"type": "其他类型", "summary": content}
    except Exception:
        return {}
