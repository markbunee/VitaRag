from flask import request
from api.utils.api_utils import get_result, get_error_data_result, token_required
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.document_service import DocumentService


@manager.route("/<dataset_id>/documents/<doc_id>/logs", methods=["GET"])  # noqa: F821
@token_required
def get_document_logs(dataset_id, doc_id, tenant_id):
    e, kb = KnowledgebaseService.get_by_id(dataset_id)
    if not e or kb.tenant_id != tenant_id:
        return get_error_data_result(message="Dataset not found or unauthorized")
    e, doc = DocumentService.get_by_id(doc_id)
    if not e or doc.kb_id != dataset_id:
        return get_error_data_result(message="Document not found")

    max_lines = int(request.args.get("max_lines", 200))
    msg = doc.progress_msg or ""
    if max_lines > 0:
        lines = msg.splitlines()
        msg = "\n".join(lines[-max_lines:])

    run_mapping = {
        "0": "UNSTART",
        "1": "RUNNING",
        "2": "CANCEL",
        "3": "DONE",
        "4": "FAIL",
    }

    data = {
        "document_id": doc.id,
        "dataset_id": doc.kb_id,
        "name": doc.name,
        "run": run_mapping.get(str(doc.run), "UNSTART"),
        "progress": float(doc.progress or 0.0),
        "progress_msg": msg,
    }
    return get_result(data=data)
