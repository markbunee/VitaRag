from flask import request
from external.api.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService

from api.utils.api_utils import get_json_result, get_error_data_result, get_result, token_required
from common.constants import RetCode
from api.constants import IMG_BASE64_PREFIX
from api.db.services.user_service import UserTenantService
from flask import jsonify

from api.utils.api_utils import build_error_result
from api.db.services.dialog_service import convert_conditions
from external.api.services.dialog_service import meta_filter


@manager.route("/<dataset_id>/update_tags/<document_id>", methods=["PUT"])  # noqa: F821
@token_required
def update_tags(tenant_id, dataset_id, document_id):
    """
    Update a document within a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: path
        name: document_id
        type: string
        required: true
        description: ID of the document to update.
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
      - in: body
        name: body
        description: Document update parameters.
        required: true
        schema:
          type: object
          properties:
            tags:
              type: list[str]
              description: New tags of the document.

    responses:
      200:
        description: Document updated successfully.
        schema:
          type: object
    """
    tenants = UserTenantService.query(user_id=tenant_id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=dataset_id):
            break
    else:
        return get_error_data_result(message="You don't own the dataset.")

    e, kb = KnowledgebaseService.get_by_id(dataset_id)
    if not e:
        return get_error_data_result(message="Can't find this knowledgebase!")
    doc = DocumentService.query(kb_id=dataset_id, id=document_id)
    if not doc:
        return get_error_data_result(message="The dataset doesn't own the document.")
    doc = doc[0]

    req = request.json
    if not isinstance(req["tags"], list):
        return get_error_data_result(message="meta_fields must be a list")

    new_tags = doc.meta_fields
    new_tags["tags"] = req["tags"]
    updated = DocumentService.update_meta_fields(document_id, new_tags)

    return get_json_result(data={"updated": updated})


@manager.route("/<dataset_id>/search", methods=["POST"])
@token_required
def search_docs(tenant_id, dataset_id):
    """
    按关键词检索
    """
    req = request.json or {}
    keyword = str(req.get("keywords", "")).strip()

    page_number = int(req.get("page", 1))
    items_per_page = int(req.get("page_size", 30))
    orderby = req.get("orderby", "create_time")
    if req.get("desc", "true").lower() == "false":
        desc = False
    else:
        desc = True

    run_status = req.get("run_status", [])
    types = req.get("types", [])
    suffix = req.get("suffix", [])

    ok, kb = KnowledgebaseService.get_by_id(dataset_id)
    if not ok:
        return build_error_result(message="Knowledgebase not found!", code=RetCode.NOT_FOUND)

    metas = DocumentService.get_meta_by_kbs([dataset_id])

    # 从metas中收集名称/标签/摘要带关键字的文档id
    doc_ids_by_kw = None
    if keyword:
        doc_ids_by_kw = set()
        for field in ("name", "tags", "summary"):
            cond = {"conditions": [{"name": field, "comparison_operator": "contains", "value": keyword}]}
            doc_ids_by_kw.update(meta_filter(metas, convert_conditions(cond)))
        if not doc_ids_by_kw:
            return jsonify({"total": 0, "docs": []})

    # 根据文档id获取文件信息后返回
    docs, _ = DocumentService.get_by_kb_id(
        dataset_id,
        page_number=0,
        items_per_page=0,
        orderby=orderby,
        desc=desc,
        keywords="",
        run_status=run_status,
        types=types,
        suffix=suffix,
    )

    if doc_ids_by_kw is not None:
        docs = [d for d in docs if d["id"] in doc_ids_by_kw]

    total = len(docs)

    if page_number and items_per_page:
        start = max(page_number - 1, 0) * items_per_page
        docs = docs[start : start + items_per_page]

    for doc_item in docs:
        if doc_item["thumbnail"] and not str(doc_item["thumbnail"]).startswith(IMG_BASE64_PREFIX):
            doc_item["thumbnail"] = f"/document/image/{dataset_id}-{doc_item['thumbnail']}"
        if doc_item.get("source_type"):
            doc_item["source_type"] = doc_item["source_type"].split("/")[0]

    return jsonify({"total": total, "docs": docs})


@manager.route("/<dataset_id>/metadata/update", methods=["POST"])  # noqa: F821
@token_required
def metadata_update(tenant_id, dataset_id):
    """
    - Method: POST
    - URL: `/api/v1/datasets/{dataset_id}/metadata/update`
    - Headers:
      - `'content-Type: application/json'`
      - `'Authorization: Bearer <YOUR_API_KEY>'`
    - Body:
      - `selector`: `object`, optional
        - `document_ids`: `list[string]`, optional
        - `metadata_condition`: `object`, optional
          - `logic`: `"and"` (default) or `"or"`
          - `conditions`: array of `{ "name": string, "comparison_operator": string, "value": string }`
            - `comparison_operator` supports: `is`, `not is`, `contains`, `not contains`, `in`, `not in`, `start with`, `end with`, `>`, `<`, `≥`, `≤`, `empty`, `not empty`
      - `updates`: `array`, optional
        - items: `{ "key": string, "value": any, "match": any (optional) }`
          - For lists: replace elements equal to `match` (or `value` when `match` omitted) with `value`.
          - For scalars: replace when current value equals `match` (or `value` when `match` omitted).
      - `deletes`: `array`, optional
        - items: `{ "key": string, "value": any (optional) }`
          - For lists: remove elements equal to `value`; if list becomes empty, remove the key.
          - For scalars: remove the key when `value` matches or when `value` is omitted.

    """

    req = request.json or {}
    if not dataset_id:
        return get_json_result(data=False, message='Lack of "KB ID"', code=RetCode.ARGUMENT_ERROR)

    tenants = UserTenantService.query(user_id=tenant_id)
    for tenant in tenants:
        if KnowledgebaseService.query(tenant_id=tenant.tenant_id, id=dataset_id):
            break
    else:
        return get_json_result(data=False, message="Only owner of knowledgebase authorized for this operation.", code=RetCode.OPERATING_ERROR)

    selector = req.get("selector", {}) or {}
    updates = req.get("updates", []) or []
    deletes = req.get("deletes", []) or []

    if not isinstance(selector, dict):
        return get_json_result(data=False, message="selector must be an object.", code=RetCode.ARGUMENT_ERROR)
    if not isinstance(updates, list) or not isinstance(deletes, list):
        return get_json_result(data=False, message="updates and deletes must be lists.", code=RetCode.ARGUMENT_ERROR)

    metadata_condition = selector.get("metadata_condition", {}) or {}
    if metadata_condition and not isinstance(metadata_condition, dict):
        return get_json_result(data=False, message="metadata_condition must be an object.", code=RetCode.ARGUMENT_ERROR)

    document_ids = selector.get("document_ids", []) or []
    if document_ids and not isinstance(document_ids, list):
        return get_json_result(data=False, message="document_ids must be a list.", code=RetCode.ARGUMENT_ERROR)

    for upd in updates:
        if not isinstance(upd, dict) or not upd.get("key") or "value" not in upd:
            return get_json_result(data=False, message="Each update requires key and value.", code=RetCode.ARGUMENT_ERROR)
    for d in deletes:
        if not isinstance(d, dict) or not d.get("key"):
            return get_json_result(data=False, message="Each delete requires key.", code=RetCode.ARGUMENT_ERROR)

    kb_doc_ids = KnowledgebaseService.list_documents_by_ids([dataset_id])
    target_doc_ids = set(kb_doc_ids)
    if document_ids:
        invalid_ids = set(document_ids) - set(kb_doc_ids)
        if invalid_ids:
            return get_json_result(data=False, message=f"These documents do not belong to dataset {dataset_id}: {', '.join(invalid_ids)}", code=RetCode.ARGUMENT_ERROR)
        target_doc_ids = set(document_ids)

    if metadata_condition:
        metas = DocumentService.get_flatted_meta_by_kbs([dataset_id])
        filtered_ids = set(meta_filter(metas, convert_conditions(metadata_condition), metadata_condition.get("logic", "and")))
        target_doc_ids = target_doc_ids & filtered_ids
        if metadata_condition.get("conditions") and not target_doc_ids:
            return get_json_result(data={"updated": 0, "matched_docs": 0})

    target_doc_ids = list(target_doc_ids)
    updated = DocumentService.batch_update_metadata(dataset_id, target_doc_ids, updates, deletes)
    return get_json_result(data={"updated": updated, "matched_docs": len(target_doc_ids)})


@manager.route("/<dataset_id>/list", methods=["POST"])  # noqa: F821
@token_required
def list_docs(dataset_id, tenant_id):
    """
    List documents in a dataset.
    ---
    tags:
      - Documents
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: dataset_id
        type: string
        required: true
        description: ID of the dataset.
      - in: query
        name: id
        type: string
        required: false
        description: Filter by document ID.
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number.
      - in: query
        name: page_size
        type: integer
        required: false
        default: 30
        description: Number of items per page.
      - in: query
        name: orderby
        type: string
        required: false
        default: "create_time"
        description: Field to order by.
      - in: query
        name: desc
        type: boolean
        required: false
        default: true
        description: Order in descending.
      - in: query
        name: create_time_from
        type: integer
        required: false
        default: 0
        description: Unix timestamp for filtering documents created after this time. 0 means no filter.
      - in: query
        name: create_time_to
        type: integer
        required: false
        default: 0
        description: Unix timestamp for filtering documents created before this time. 0 means no filter.
      - in: query
        name: suffix
        type: array
        items:
          type: string
        required: false
        description: Filter by file suffix (e.g., ["pdf", "txt", "docx"]).
      - in: query
        name: run
        type: array
        items:
          type: string
        required: false
        description: Filter by document run status. Supports both numeric ("0", "1", "2", "3", "4") and text formats ("UNSTART", "RUNNING", "CANCEL", "DONE", "FAIL").
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: List of documents.
        schema:
          type: object
          properties:
            total:
              type: integer
              description: Total number of documents.
            docs:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Document ID.
                  name:
                    type: string
                    description: Document name.
                  chunk_count:
                    type: integer
                    description: Number of chunks.
                  token_count:
                    type: integer
                    description: Number of tokens.
                  dataset_id:
                    type: string
                    description: ID of the dataset.
                  chunk_method:
                    type: string
                    description: Chunking method used.
                  run:
                    type: string
                    description: Processing status.
                  minio_url:
                    type: string
                    description: File stream URL for document download/preview. Use this URL to access the document content.
    """
    if not KnowledgebaseService.accessible(kb_id=dataset_id, user_id=tenant_id):
        return get_error_data_result(message=f"You don't own the dataset {dataset_id}. ")

    q = request.json or {}
    name = q.get("name")

    doc_ids = q.get("ids", [])
    for doc_id in doc_ids:
        if not DocumentService.accessible(doc_id, tenant_id):
            return get_error_data_result(message=f"You don't own the document {doc_id}.")
    # docs = DocumentService.get_by_ids(doc_ids)

    if name and not DocumentService.query(name=name, kb_id=dataset_id):
        return get_error_data_result(message=f"You don't own the document {name}.")

    page = int(q.get("page", 1))
    page_size = int(q.get("page_size", 30))
    orderby = q.get("orderby", "create_time")
    desc = str(q.get("desc", "true")).strip().lower() != "false"
    keywords = q.get("keywords", "")

    # filters - align with OpenAPI parameter names
    suffix = q.get("suffix", [])
    run_status = q.get("run", [])
    create_time_from = int(q.get("create_time_from", 0))
    create_time_to = int(q.get("create_time_to", 0))

    # map run status (accept text or numeric) - align with API parameter
    run_status_text_to_numeric = {"UNSTART": "0", "RUNNING": "1", "CANCEL": "2", "DONE": "3", "FAIL": "4"}
    run_status_converted = [run_status_text_to_numeric.get(v, v) for v in run_status]

    docs, total = DocumentService.get_list(dataset_id, page, page_size, orderby, desc, keywords, doc_ids, name, suffix, run_status_converted)

    # time range filter (0 means no bound)
    if create_time_from or create_time_to:
        docs = [d for d in docs if (create_time_from == 0 or d.get("create_time", 0) >= create_time_from) and (create_time_to == 0 or d.get("create_time", 0) <= create_time_to)]

    # rename keys + map run status back to text for output
    key_mapping = {
        "chunk_num": "chunk_count",
        "kb_id": "dataset_id",
        "token_num": "token_count",
        "parser_id": "chunk_method",
    }
    run_status_numeric_to_text = {"0": "UNSTART", "1": "RUNNING", "2": "CANCEL", "3": "DONE", "4": "FAIL"}

    output_docs = []
    for d in docs:
        renamed_doc = {key_mapping.get(k, k): v for k, v in d.items()}
        if "run" in d:
            renamed_doc["run"] = run_status_numeric_to_text.get(str(d["run"]), d["run"])
        if d["thumbnail"] and not str(d["thumbnail"]).startswith(IMG_BASE64_PREFIX):
            renamed_doc["thumbnail"] = f"/document/image/{dataset_id}-{d['thumbnail']}"
        if d.get("source_type"):
            renamed_doc["source_type"] = d["source_type"].split("/")[0]

        d_id = d.get("id")
        if d_id:
            renamed_doc["minio_url"] = f"/document/get/{d_id}"

        output_docs.append(renamed_doc)

    return get_result(data={"total": total, "docs": output_docs})
