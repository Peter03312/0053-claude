"""校样求解器。

输入一份规范化 spec，搜索所有气泡的整数左上角新位置，使得：
  1. 每个气泡完整落在安全区内，且两两互不接触（贴边也算接触）；
  2. 尾线起点随气泡同量平移，尾线段不得接触/穿越任何其他气泡与保护框；
  3. 每个气泡的曼哈顿位移 |dx|+|dy| 不超过 maxStep，锁定气泡位移为 0；
  4. 由“在上/在左”关系建图后无环，且唯一拓扑序恰为台词总序
     （等价于：总序中相邻泡之间必须存在前向边，且不存在任何反向边）。

目标按字典序最小化：(移动泡数, 总曼哈顿位移, 单泡最大曼哈顿位移)，
仍并列时按气泡编号 Unicode 码点升序排列的候选左上角 (x, y) 序列取字典序最小者，
从而保证结果唯一确定。
"""

from .geometry import derived_edge, inside_safe, segment_hits_rect, separated
from .validation import validate_spec

NODE_BUDGET = 400_000
CONFLICT_PAIR_BUDGET = 2_000_000


class SearchBudgetExceeded(Exception):
    pass


class _Bubble:
    __slots__ = ("id", "w", "h", "ox", "oy", "tail_off", "anchor", "locked", "order_idx")

    def __init__(self, raw, order_idx):
        self.id = raw["id"]
        r = raw["rect"]
        self.ox, self.oy, self.w, self.h = r["x"], r["y"], r["w"], r["h"]
        self.tail_off = (raw["tail"]["x"] - self.ox, raw["tail"]["y"] - self.oy)
        self.anchor = (raw["anchor"]["x"], raw["anchor"]["y"])
        self.locked = raw["locked"]
        self.order_idx = order_idx

    def rect_at(self, pos):
        return {"x": pos[0], "y": pos[1], "w": self.w, "h": self.h}

    def tail_at(self, pos):
        return (pos[0] + self.tail_off[0], pos[1] + self.tail_off[1])


def _gen_domain(b: _Bubble, spec):
    """单泡可行位置：安全区内 + 位移上限/锁定 + 尾线避开所有保护框。"""
    safe = spec["safeArea"]
    max_step = spec["maxStep"]
    protections = spec["protections"]
    if b.locked:
        offsets = [(0, 0)]
    else:
        offsets = [
            (dx, dy)
            for dx in range(-max_step, max_step + 1)
            for dy in range(-max_step, max_step + 1)
            if abs(dx) + abs(dy) <= max_step
        ]
    out = []
    for dx, dy in offsets:
        pos = (b.ox + dx, b.oy + dy)
        rect = b.rect_at(pos)
        if not inside_safe(rect, safe):
            continue
        tail = b.tail_at(pos)
        if any(segment_hits_rect(tail, b.anchor, p) for p in protections):
            continue
        manhattan = abs(dx) + abs(dy)
        out.append((manhattan > 0, manhattan, pos[0], pos[1], pos))
    # 取值顺序：未移动优先，再按位移、再按坐标，保证分支定界尽早拿到优解
    out.sort()
    return [item[4] for item in out]


def _pair_ok(bi, pi, bj, pj, gap):
    """两泡候选位置是否相容：互不接触 + 顺序约束 + 尾线互不侵犯。"""
    ri = bi.rect_at(pi)
    rj = bj.rect_at(pj)
    if not separated(ri, rj):
        return False
    edge = derived_edge(ri, rj, gap)
    if bi.order_idx < bj.order_idx:
        if edge == "ba":  # 反向边 → 成环
            return False
        if bj.order_idx == bi.order_idx + 1 and edge != "ab":
            return False  # 总序相邻泡之间必须有前向边，否则拓扑序不唯一
    else:
        if edge == "ab":
            return False
        if bi.order_idx == bj.order_idx + 1 and edge != "ba":
            return False
    if segment_hits_rect(bi.tail_at(pi), bi.anchor, rj):
        return False
    if segment_hits_rect(bj.tail_at(pj), bj.anchor, ri):
        return False
    return True


def _solve_checked(spec):
    bubbles = [ _Bubble(raw, spec["order"].index(raw["id"])) for raw in spec["bubbles"] ]
    gap = spec["gap"]

    domains = {b.id: _gen_domain(b, spec) for b in bubbles}
    empty = [b.id for b in bubbles if not domains[b.id]]
    if empty:
        return _no_solution(spec, bubbles, domains, empty)

    # 搜索顺序：候选少的先定（锁定泡天然靠前）
    search_order = sorted(bubbles, key=lambda b: (len(domains[b.id]), b.id))
    # 平局裁决序列：按编号 Unicode 码点升序的 (x, y) 元组
    tiebreak_order = sorted(bubbles, key=lambda b: b.id)

    assigned = {}
    best = {"key": None, "positions": None}
    nodes = [0]

    def dfs(k, moved, total, maxd):
        nodes[0] += 1
        if nodes[0] > NODE_BUDGET:
            raise SearchBudgetExceeded()
        if best["key"] is not None and (moved, total, maxd) > best["key"][:3]:
            return
        if k == len(search_order):
            tie = tuple(assigned[b.id] for b in tiebreak_order)
            key = (moved, total, maxd, tie)
            if best["key"] is None or key < best["key"]:
                best["key"] = key
                best["positions"] = dict(assigned)
            return
        b = search_order[k]
        for pos in domains[b.id]:
            dx = pos[0] - b.ox
            dy = pos[1] - b.oy
            m = abs(dx) + abs(dy)
            n_moved = moved + (1 if m else 0)
            n_total = total + m
            n_max = max(maxd, m)
            if best["key"] is not None and (n_moved, n_total, n_max) > best["key"][:3]:
                break  # 域内按代价升序，之后的只会更差
            ok = True
            for other in search_order:
                if other.id in assigned and not _pair_ok(
                    b, pos, other, assigned[other.id], gap
                ):
                    ok = False
                    break
            if not ok:
                continue
            assigned[b.id] = pos
            dfs(k + 1, n_moved, n_total, n_max)
            del assigned[b.id]

    dfs(0, 0, 0, 0)

    if best["positions"] is None:
        return _no_solution(spec, bubbles, domains, empty)

    positions = {bid: {"x": p[0], "y": p[1]} for bid, p in best["positions"].items()}
    edges = []
    rects = {b.id: b.rect_at(best["positions"][b.id]) for b in bubbles}
    for i in range(len(bubbles)):
        for j in range(i + 1, len(bubbles)):
            bi, bj = bubbles[i], bubbles[j]
            e = derived_edge(rects[bi.id], rects[bj.id], gap)
            if e == "ab":
                edges.append({"from": bi.id, "to": bj.id})
            elif e == "ba":
                edges.append({"from": bj.id, "to": bi.id})
    moved, total, maxd = best["key"][0], best["key"][1], best["key"][2]
    return {
        "status": "ok",
        "movedCount": moved,
        "totalDisplacement": total,
        "maxDisplacement": maxd,
        "positions": positions,
        "edges": edges,
    }


def _no_solution(spec, bubbles, domains, empty):
    """无解时给出可定位的反馈：相邻台词对中不存在任何相容位置对的“冲突边”。"""
    gap = spec["gap"]
    by_id = {b.id: b for b in bubbles}
    conflicts = []
    order = spec["order"]
    for a_id, b_id in zip(order, order[1:]):
        a, b = by_id[a_id], by_id[b_id]
        da, db = domains[a_id], domains[b_id]
        # 域过大时按代价升序截断，保证检查有界且确定性
        if len(da) * max(1, len(db)) > CONFLICT_PAIR_BUDGET:
            keep = max(1, int(CONFLICT_PAIR_BUDGET**0.5))
            da, db = da[:keep], db[:keep]
        found = False
        for pa in da:
            for pb in db:
                if _pair_ok(a, pa, b, pb, gap):
                    found = True
                    break
            if found:
                break
        if not found:
            conflicts.append({"pair": [a_id, b_id]})
    parts = []
    if empty:
        parts.append("以下气泡在位移上限与安全区约束下没有任何可行位置: " + ", ".join(empty))
    if conflicts:
        pairs = "、".join(f"{c['pair'][0]}→{c['pair'][1]}" for c in conflicts)
        parts.append("以下相邻台词无法建立所需阅读顺序: " + pairs)
    if not parts:
        parts.append("约束组合过强，未能在搜索预算内找到候选布局")
    return {
        "status": "no_solution",
        "message": "；".join(parts),
        "conflicts": conflicts,
        "emptyDomains": empty,
    }


def solve(spec):
    """校验并求解。校验失败抛 ValidationError，成功返回结果 dict。"""
    checked = validate_spec(spec)
    return _solve_checked(checked)
