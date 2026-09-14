"""整数几何原语。

所有坐标均为整数网格。矩形用 dict 表示：{"x", "y", "w", "h"}，
(x, y) 为左上角，w/h 为正整数。边接触（共线/共点）一律视为“接触”，
与本工具“气泡互不接触、尾线不得接触保护框”的语义一致。
"""

Rect = dict  # {"x": int, "y": int, "w": int, "h": int}
Point = tuple  # (x, y)


def inside_safe(r: Rect, safe: Rect) -> bool:
    """矩形完整落在安全区内（允许贴安全区边界）。"""
    return (
        r["x"] >= safe["x"]
        and r["y"] >= safe["y"]
        and r["x"] + r["w"] <= safe["x"] + safe["w"]
        and r["y"] + r["h"] <= safe["y"] + safe["h"]
    )


def separated(a: Rect, b: Rect) -> bool:
    """两矩形在至少一个轴向上严格分离（边贴边也算接触，返回 False）。"""
    return (
        a["x"] + a["w"] < b["x"]
        or b["x"] + b["w"] < a["x"]
        or a["y"] + a["h"] < b["y"]
        or b["y"] + b["h"] < a["y"]
    )


def point_in_rect(px: int, py: int, r: Rect) -> bool:
    """点是否落在闭矩形内（含边界）。"""
    return r["x"] <= px <= r["x"] + r["w"] and r["y"] <= py <= r["y"] + r["h"]


def _orient(a: Point, b: Point, c: Point) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    """p 是否在线段 ab 上（前置条件：三点共线）。"""
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(
        a[1], b[1]
    )


def segments_touch(a: Point, b: Point, c: Point, d: Point) -> bool:
    """线段 ab 与 cd 是否有任意公共点（含端点接触、共线重叠）。"""
    o1 = _orient(a, b, c)
    o2 = _orient(a, b, d)
    o3 = _orient(c, d, a)
    o4 = _orient(c, d, b)
    if o1 == 0 and _on_segment(a, b, c):
        return True
    if o2 == 0 and _on_segment(a, b, d):
        return True
    if o3 == 0 and _on_segment(c, d, a):
        return True
    if o4 == 0 and _on_segment(c, d, b):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def segment_hits_rect(p: Point, q: Point, r: Rect) -> bool:
    """线段 pq 是否接触或穿越闭矩形 r。"""
    if point_in_rect(p[0], p[1], r) or point_in_rect(q[0], q[1], r):
        return True
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    for i in range(4):
        if segments_touch(p, q, corners[i], corners[(i + 1) % 4]):
            return True
    return False


def is_above(a: Rect, b: Rect, gap: int) -> bool:
    """A 底边加阅读间距不超过 B 顶边 → A 在 B 上。"""
    return a["y"] + a["h"] + gap <= b["y"]


def is_left(a: Rect, b: Rect, gap: int) -> bool:
    """纵向重叠不少于较矮泡高度的一半，且 A 右边加间距不超过 B 左边 → A 在 B 左。"""
    overlap = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return 2 * overlap >= min(a["h"], b["h"]) and a["x"] + a["w"] + gap <= b["x"]


def derived_edge(a: Rect, b: Rect, gap: int):
    """由几何关系推出阅读先后：'ab' 表示 a 先读，'ba' 表示 b 先读，None 表示无关。"""
    if is_above(a, b, gap):
        return "ab"
    if is_above(b, a, gap):
        return "ba"
    if is_left(a, b, gap):
        return "ab"
    if is_left(b, a, gap):
        return "ba"
    return None
