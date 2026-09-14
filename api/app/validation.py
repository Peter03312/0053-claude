"""校样规格（spec）的入参校验。

校验通过返回规范化后的 spec（补齐默认值）；失败抛出 ValidationError，
details 为人类可读的中文错误列表，供前端逐条展示。
"""

MAX_BUBBLES = 12
MIN_BUBBLES = 2
MAX_COORD = 1_000_000
MAX_GAP = 100_000
MAX_STEP = 100


class ValidationError(Exception):
    def __init__(self, details):
        super().__init__("; ".join(details))
        self.details = list(details)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_rect(r, label, errors):
    if not isinstance(r, dict):
        errors.append(f"{label} 必须是对象")
        return None
    for k in ("x", "y", "w", "h"):
        if not _is_int(r.get(k)):
            errors.append(f"{label}.{k} 必须是整数")
            return None
    if r["w"] <= 0 or r["h"] <= 0:
        errors.append(f"{label} 的宽和高必须为正整数")
        return None
    for k in ("x", "y", "w", "h"):
        if abs(r[k]) > MAX_COORD:
            errors.append(f"{label}.{k} 超出允许范围 ±{MAX_COORD}")
            return None
    return {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]}


def _check_point(p, label, errors):
    if not isinstance(p, dict) or not _is_int(p.get("x")) or not _is_int(p.get("y")):
        errors.append(f"{label} 必须是含整数 x、y 的对象")
        return None
    if abs(p["x"]) > MAX_COORD or abs(p["y"]) > MAX_COORD:
        errors.append(f"{label} 超出允许范围 ±{MAX_COORD}")
        return None
    return {"x": p["x"], "y": p["y"]}


def _on_perimeter(rect, p) -> bool:
    on_x_edge = rect["x"] <= p["x"] <= rect["x"] + rect["w"] and (
        p["y"] == rect["y"] or p["y"] == rect["y"] + rect["h"]
    )
    on_y_edge = rect["y"] <= p["y"] <= rect["y"] + rect["h"] and (
        p["x"] == rect["x"] or p["x"] == rect["x"] + rect["w"]
    )
    return on_x_edge or on_y_edge


def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValidationError(["请求体必须是 JSON 对象"])
    errors = []

    safe = _check_rect(spec.get("safeArea"), "safeArea", errors)

    gap = spec.get("gap")
    if not _is_int(gap) or gap < 0 or gap > MAX_GAP:
        errors.append(f"gap 必须是 0..{MAX_GAP} 的整数")
        gap = None

    max_step = spec.get("maxStep")
    if not _is_int(max_step) or max_step < 0 or max_step > MAX_STEP:
        errors.append(f"maxStep 必须是 0..{MAX_STEP} 的整数")
        max_step = None

    protections = spec.get("protections", [])
    if not isinstance(protections, list):
        errors.append("protections 必须是数组")
        protections = []
    norm_protections = []
    for i, p in enumerate(protections):
        pr = _check_rect(p, f"protections[{i}]", errors)
        if pr is not None:
            norm_protections.append(pr)

    bubbles = spec.get("bubbles")
    if not isinstance(bubbles, list):
        errors.append("bubbles 必须是数组")
        bubbles = []
    if not (MIN_BUBBLES <= len(bubbles) <= MAX_BUBBLES):
        errors.append(f"对白泡数量必须在 {MIN_BUBBLES}..{MAX_BUBBLES} 之间，当前 {len(bubbles)} 个")

    norm_bubbles = []
    seen_ids = set()
    for i, b in enumerate(bubbles):
        label = f"bubbles[{i}]"
        if not isinstance(b, dict):
            errors.append(f"{label} 必须是对象")
            continue
        bid = b.get("id")
        if not isinstance(bid, str) or not bid.strip():
            errors.append(f"{label}.id 必须是非空字符串")
            bid = None
        elif bid in seen_ids:
            errors.append(f"气泡编号 {bid!r} 重复")
            bid = None
        else:
            seen_ids.add(bid)
        rect = _check_rect(b, f"{label}({bid if bid else '?'})", errors)
        tail = _check_point(b.get("tail"), f"{label}.tail", errors)
        anchor = _check_point(b.get("anchor"), f"{label}.anchor", errors)
        locked = b.get("locked", False)
        if not isinstance(locked, bool):
            errors.append(f"{label}.locked 必须是布尔值")
            locked = False
        if rect is not None and tail is not None and not _on_perimeter(rect, tail):
            errors.append(f"气泡 {bid if bid else i} 的尾线起点必须落在泡边（矩形边界）上")
        if bid is not None and rect is not None and tail is not None and anchor is not None:
            norm_bubbles.append(
                {
                    "id": bid,
                    "rect": rect,
                    "tail": tail,
                    "anchor": anchor,
                    "locked": locked,
                }
            )

    order = spec.get("order")
    norm_order = None
    if not isinstance(order, list) or any(not isinstance(o, str) for o in (order or [])):
        errors.append("order 必须是气泡编号字符串组成的数组")
    else:
        bubble_ids = [b["id"] for b in norm_bubbles]
        if len(order) != len(bubble_ids) or set(order) != set(bubble_ids):
            errors.append("order 必须恰好是所有气泡编号的一个排列（不多不少不重复）")
        elif len(set(order)) != len(order):
            errors.append("order 中存在重复编号")
        else:
            norm_order = list(order)

    if errors:
        raise ValidationError(errors)

    return {
        "safeArea": safe,
        "gap": gap,
        "maxStep": max_step,
        "protections": norm_protections,
        "bubbles": norm_bubbles,
        "order": norm_order,
    }
