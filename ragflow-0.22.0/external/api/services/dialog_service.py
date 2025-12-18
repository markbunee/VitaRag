# 元数据筛选 支持或逻辑
def meta_filter(metas: dict, filters: list[dict], logic: str = "and"):
    doc_ids = set([])

    def filter_out(v2docs, operator, value):
        ids = []
        for input, docids in v2docs.items():
            if operator in ["=", "≠", ">", "<", "≥", "≤"]:
                try:
                    input = float(input)
                    value = float(value)
                except Exception:
                    input = str(input)
                    value = str(value)

            for conds in [
                (operator == "contains", str(value).lower() in str(input).lower()),
                (operator == "not contains", str(value).lower() not in str(input).lower()),
                (operator == "in", str(input).lower() in str(value).lower()),
                (operator == "not in", str(input).lower() not in str(value).lower()),
                (operator == "start with", str(input).lower().startswith(str(value).lower())),
                (operator == "end with", str(input).lower().endswith(str(value).lower())),
                (operator == "empty", not input),
                (operator == "not empty", input),
                (operator == "=", input == value),
                (operator == "≠", input != value),
                (operator == ">", input > value),
                (operator == "<", input < value),
                (operator == "≥", input >= value),
                (operator == "≤", input <= value),
            ]:
                try:
                    if all(conds):
                        ids.extend(docids)
                        break
                except Exception:
                    pass
        return ids

    for k, v2docs in metas.items():
        for f in filters:
            if k != f["key"]:
                continue
            ids = filter_out(v2docs, f["op"], f["value"])
            if not doc_ids:
                doc_ids = set(ids)
            else:
                if logic == "and":
                    doc_ids = doc_ids & set(ids)
                else:
                    doc_ids = doc_ids | set(ids)
            if not doc_ids:
                return []
    return list(doc_ids)
