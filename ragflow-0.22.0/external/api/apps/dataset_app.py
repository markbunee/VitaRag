#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#


import logging
from flask import request
from peewee import OperationalError
from external.api.services.document_service import DocumentService
from external.api.services.knowledgebase_service import KnowledgebaseService
from api.db.services.user_service import TenantService
from api.utils.api_utils import get_error_data_result, get_error_permission_result, get_result, remap_dictionary_keys, token_required, get_json_result
from common.constants import RetCode


@manager.route("/list", methods=["POST"])  # noqa: F821
@token_required
def list_datasets(tenant_id):
    """
    List datasets.
    ---
    tags:
      - Datasets
    security:
      - ApiKeyAuth: []
    parameters:
      - in: query
        name: id
        type: string
        required: false
        description: Dataset ID to filter.
      - in: query
        name: name
        type: string
        required: false
        description: Dataset name to filter.
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
      - in: header
        name: Authorization
        type: string
        required: true
        description: Bearer token for authentication.
    responses:
      200:
        description: Successful operation.
        schema:
          type: array
          items:
            type: object
    """
    # args, err = validate_and_parse_request_args(request, ListDatasetReq)
    q = request.json or {}
    page = int(q.get("page", 1))
    page_size = int(q.get("page_size", 30))
    orderby = q.get("orderby", "create_time")
    desc = str(q.get("desc", "true")).strip().lower() != "false"

    try:
        kb_ids = q.get("ids", [])
        name = q.get("name")
        if kb_ids:
            for kb_id in kb_ids:
                if not KnowledgebaseService.accessible(kb_id, tenant_id):
                    return get_error_permission_result(message=f"User '{tenant_id}' lacks permission for dataset '{kb_id}'")
        if name:
            kbs = KnowledgebaseService.get_kb_by_name(name, tenant_id)
            if not kbs:
                return get_error_permission_result(message=f"User '{tenant_id}' lacks permission for dataset '{name}'")

        tenants = TenantService.get_joined_tenants_by_user_id(tenant_id)
        kbs, total = KnowledgebaseService.get_list(
            [m["tenant_id"] for m in tenants],
            tenant_id,
            page,
            page_size,
            orderby,
            desc,
            kb_ids,
            name,
        )

        response_data_list = []
        for kb in kbs:
            # response_data_list.append(remap_dictionary_keys(kb))
            total_size = DocumentService.get_total_size_by_kb_id(kb["id"])
            kb_with_size = {**kb, "total_size": total_size}
            response_data_list.append(remap_dictionary_keys(kb_with_size))

        return get_result(data=response_data_list, total=total)
    except OperationalError as e:
        logging.exception(e)
        return get_error_data_result(message="Database operation failed")


@manager.route("/get_tags", methods=["GET"])  # noqa: F821
@token_required
def get_meta(tenant_id):
    kb_ids = request.args.get("kb_ids", "").split(",")
    for kb_id in kb_ids:
        if not KnowledgebaseService.accessible(kb_id, user_id=tenant_id):
            return get_json_result(data=False, message="No authorization.", code=RetCode.AUTHENTICATION_ERROR)
    data = DocumentService.get_flatted_meta_by_kbs(kb_ids)
    data = list(data["tags"].keys())
    return get_json_result(data={"tags": data})
