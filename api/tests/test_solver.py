"""求解器场景测试：协同移动、尾线阻断、锁定无解、稳定并列及基础规则。

所有几何均在测试内即时构造；断言只验证求解器真实输出，
不存在任何预制答案坐标之外的捷径。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.solver import solve  # noqa: E402
from app.validation import ValidationError, validate_spec  # noqa: E402

BIG_SAFE = {"x": -100, "y": -100, "w": 500, "h": 500}


def bubble(bid, x, y, w=10, h=10, tail=None, anchor=None, locked=False):
    tail = tail if tail is not None else (x + w // 2, y)  # 默认顶边中点
    anchor = anchor if anchor is not None else (x + w // 2, y - 30)  # 默认正上方
    return {
        "id": bid,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "tail": {"x": tail[0], "y": tail[1]},
        "anchor": {"x": anchor[0], "y": anchor[1]},
        "locked": locked,
    }


def spec(bubbles, order, gap=0, max_step=4, protections=None, safe=BIG_SAFE):
    return {
        "safeArea": safe,
        "gap": gap,
        "maxStep": max_step,
        "protections": protections or [],
        "bubbles": bubbles,
        "order": order,
    }


# ---------------------------------------------------------------- 协同移动
def test_cooperative_move_both_bubbles_shift():
    """两泡重叠 1px，maxStep=1 时任何单泡都无法独自脱困，必须两泡各让 1 格。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(5, 0), anchor=(5, -30)),
            bubble("B", 9, 0, tail=(14, 0), anchor=(14, -30)),
        ],
        ["A", "B"],
        max_step=1,
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["movedCount"] == 2  # 单泡移动 1 格无法分离，必须协同
    assert r["totalDisplacement"] == 2
    assert r["maxDisplacement"] == 1
    assert r["positions"]["A"] == {"x": -1, "y": 0}
    assert r["positions"]["B"] == {"x": 10, "y": 0}


def test_single_bubble_escape_impossible_with_step_1():
    """佐证协同的必要性：只允许动一个泡（另一泡锁定）时确实无解。"""
    s = spec(
        [bubble("A", 0, 0, locked=True), bubble("B", 9, 0)],
        ["A", "B"],
        max_step=1,
    )
    assert solve(s)["status"] == "no_solution"


# ---------------------------------------------------------------- 尾线阻断
def test_tail_blocked_by_protection_picks_detour():
    """B 最近的可行位 (14,0) 尾线会擦到保护框，求解器必须绕到次优位。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(5, 10), anchor=(5, 50), locked=True),
            bubble("B", 20, 0, tail=(25, 10), anchor=(25, 50)),
            bubble("C", 25, 0, tail=(30, 10), anchor=(30, 50), locked=True),
        ],
        ["A", "B", "C"],
        max_step=10,
        protections=[{"x": 21, "y": 24, "w": 3, "h": 2}],
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["movedCount"] == 1
    # 若尾线可穿保护框，最优应为 (14,0)、总位移 6；被阻断后只能 (13,0)、总位移 7
    assert r["positions"]["B"] == {"x": 13, "y": 0}
    assert r["totalDisplacement"] == 7
    assert r["positions"]["A"] == {"x": 0, "y": 0}
    assert r["positions"]["C"] == {"x": 25, "y": 0}


def test_tail_may_not_cross_other_bubble():
    """尾线穿越其他气泡同样非法：小泡 D 挡在尾线路径上，B 只能绕行。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(5, 10), anchor=(5, 50), locked=True),
            bubble("B", 20, 0, tail=(25, 10), anchor=(25, 50)),
            bubble("C", 25, 0, tail=(30, 10), anchor=(30, 50), locked=True),
            bubble("D", 21, 24, w=3, h=2, tail=(22, 24), anchor=(22, 60), locked=True),
        ],
        ["A", "B", "C", "D"],
        max_step=10,
    )
    r = solve(s)
    assert r["status"] == "ok"
    # 与保护框场景同构：最近位 (14,0) 的尾线擦到 D，只能去 (13,0)
    assert r["positions"]["B"] == {"x": 13, "y": 0}
    assert r["totalDisplacement"] == 7


# ---------------------------------------------------------------- 锁定无解
def test_locked_overlap_no_solution_reports_conflict_edge():
    """两个锁定泡互相重叠：无解，且必须标出冲突边 A→B。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(2, 0), anchor=(2, -30), locked=True),
            bubble("B", 5, 0, tail=(12, 0), anchor=(12, -30), locked=True),
        ],
        ["A", "B"],
    )
    r = solve(s)
    assert r["status"] == "no_solution"
    assert {"pair": ["A", "B"]} in r["conflicts"]
    assert "A→B" in r["message"]


def test_locked_bubble_never_moves():
    """有锁定时只能动别人：B 必须独自让位。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(2, 0), anchor=(2, -30), locked=True),
            bubble("B", 9, 0, tail=(14, 0), anchor=(14, -30)),
        ],
        ["A", "B"],
        max_step=2,
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["positions"]["A"] == {"x": 0, "y": 0}
    assert r["positions"]["B"] == {"x": 11, "y": 0}
    assert r["movedCount"] == 1


# ---------------------------------------------------------------- 稳定并列
def test_stable_tie_broken_by_id_ordered_positions():
    """两种等优单泡修复方案并列时，按编号序的 (x,y) 序列字典序取唯一解。"""
    s = spec(
        [
            bubble("B", 0, 0, tail=(5, 0), anchor=(5, -30)),
            bubble("C", 9, 0, tail=(14, 0), anchor=(14, -30)),
        ],
        ["B", "C"],
        max_step=2,
    )
    r1 = solve(s)
    r2 = solve(s)
    assert r1["status"] == "ok"
    # 方案一：B 左移 2；方案二：C 右移 2。二者 (1,2,2) 并列，
    # 序列 [(-2,0),(9,0)] < [(0,0),(11,0)]，故动 B。
    assert r1["movedCount"] == 1
    assert r1["totalDisplacement"] == 2
    assert r1["positions"]["B"] == {"x": -2, "y": 0}
    assert r1["positions"]["C"] == {"x": 9, "y": 0}
    assert r1 == r2  # 结果确定可复现


# ---------------------------------------------------------------- 基础规则
def test_already_valid_layout_is_untouched():
    s = spec([bubble("A", 0, 0), bubble("B", 30, 0)], ["A", "B"])
    r = solve(s)
    assert r["status"] == "ok"
    assert r["movedCount"] == 0
    assert r["totalDisplacement"] == 0
    assert r["positions"]["A"] == {"x": 0, "y": 0}
    assert r["positions"]["B"] == {"x": 30, "y": 0}


def test_gap_decides_above_relation():
    """A 底边 + gap ≤ B 顶边才判 A 在上：gap 收紧后同一布局由合法变无解。"""
    bubbles = [
        bubble("A", 0, 0, tail=(5, 0), anchor=(5, -30), locked=True),
        bubble("B", 0, 20, tail=(5, 20), anchor=(5, 60), locked=True),
    ]
    ok = solve(spec(bubbles, ["A", "B"], gap=5, max_step=0))
    assert ok["status"] == "ok"  # 0+10+5 <= 20
    bad = solve(spec(bubbles, ["A", "B"], gap=11, max_step=0))
    assert bad["status"] == "no_solution"  # 0+10+11 > 20，相邻边断裂


def test_backward_edge_violates_declared_order():
    """几何上 A 在 B 之上，但台词总序要求 B 先读 → 反向边 → 无解。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(5, 0), anchor=(5, -30), locked=True),
            bubble("B", 0, 30, tail=(5, 30), anchor=(5, 60), locked=True),
        ],
        ["B", "A"],
        max_step=0,
    )
    r = solve(s)
    assert r["status"] == "no_solution"
    assert {"pair": ["B", "A"]} in r["conflicts"]


def test_touching_edges_count_as_contact():
    """贴边（无重叠）也算接触，必须挪开。"""
    s = spec(
        [bubble("A", 0, 0, locked=True), bubble("B", 10, 0)],
        ["A", "B"],
        max_step=1,
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["positions"]["B"] == {"x": 11, "y": 0}


def test_left_relation_requires_half_height_overlap():
    """纵向重叠不足较矮泡一半时，左右关系不成立。"""
    # A(0,0,10,10)，B(11,6,10,10)：重叠 4 < 5 → 无左序边；maxStep=0 → 无解
    s = spec(
        [
            bubble("A", 0, 0, tail=(5, 0), anchor=(5, -30), locked=True),
            bubble("B", 11, 6, tail=(16, 6), anchor=(16, -30), locked=True),
        ],
        ["A", "B"],
        max_step=0,
    )
    assert solve(s)["status"] == "no_solution"
    # B 上移到重叠 5 → 左右关系成立 → 合法
    s2 = spec(
        [
            bubble("A", 0, 0, tail=(5, 0), anchor=(5, -30), locked=True),
            bubble("B", 11, 5, tail=(16, 5), anchor=(16, -30), locked=True),
        ],
        ["A", "B"],
        max_step=0,
    )
    assert solve(s2)["status"] == "ok"


def test_unique_topological_order_with_three_bubbles():
    """三泡竖排：相邻边齐备时唯一拓扑序即台词总序，原样通过。"""
    s = spec(
        [
            bubble("A", 0, 0, tail=(10, 5), anchor=(40, 5)),
            bubble("B", 0, 30, tail=(10, 35), anchor=(40, 35)),
            bubble("C", 0, 60, tail=(10, 65), anchor=(40, 65)),
        ],
        ["A", "B", "C"],
        gap=4,
        max_step=0,
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["movedCount"] == 0
    edge_pairs = {(e["from"], e["to"]) for e in r["edges"]}
    assert ("A", "B") in edge_pairs and ("B", "C") in edge_pairs


def test_bubble_must_stay_inside_safe_area():
    """位移上限内无法回到安全区 → 该泡无可行位置。"""
    tight = {"x": 0, "y": 0, "w": 30, "h": 30}
    s = spec(
        [bubble("A", 0, 0, locked=True), bubble("B", 40, 0)],
        ["A", "B"],
        max_step=4,
        safe=tight,
    )
    r = solve(s)
    assert r["status"] == "no_solution"
    assert "B" in r["emptyDomains"]


# ---------------------------------------------------------------- 冲突边精确性
def test_conflict_detection_does_not_blame_arrangeable_pair():
    """回归：域很大时也不得误标冲突边。

    A 锁定且横贯安全区 → A→B 只能让 B 下移 31 格（超出旧截断窗口）；
    真正无解的是 B→C（C 锁在左上角，B 无法建立前向边）。
    只有 (B,C) 应被标记，(A,B) 本来可以排列，不得误伤。
    """
    safe = {"x": 0, "y": 0, "w": 400, "h": 400}
    s = spec(
        [
            bubble("A", 0, 20, w=400, h=10, tail=(200, 30), anchor=(200, 60), locked=True),
            bubble("B", 0, 0, tail=(5, 0), anchor=(5, 100)),
            bubble("C", 0, 0, tail=(5, 0), anchor=(5, -30), locked=True),
        ],
        ["A", "B", "C"],
        max_step=100,
        safe=safe,
    )
    r = solve(s)
    assert r["status"] == "no_solution"
    assert r["conflicts"] == [{"pair": ["B", "C"]}]


def test_conflict_witness_may_require_large_steps():
    """相邻对的可行见证可能需要接近上限的大位移，精确检测必须找得到。"""
    safe = {"x": 0, "y": 0, "w": 400, "h": 400}
    # A 锁定横贯，B 在 A 上方：A→B 只能让 B 下移 31 格；C 不挡路（远离）。
    s = spec(
        [
            bubble("A", 0, 20, w=400, h=10, tail=(200, 30), anchor=(200, 60), locked=True),
            bubble("B", 0, 0, tail=(5, 0), anchor=(5, 100)),
            bubble("C", 300, 200, tail=(305, 200), anchor=(305, 170), locked=True),
        ],
        ["A", "B", "C"],
        max_step=100,
        safe=safe,
    )
    r = solve(s)
    assert r["status"] == "ok"
    assert r["positions"]["B"] == {"x": 0, "y": 31}
    assert r["positions"]["A"] == {"x": 0, "y": 20}


# ---------------------------------------------------------------- 校验
def test_validation_rejects_duplicate_and_empty_ids():
    dup = spec([bubble("A", 0, 0), bubble("A", 30, 0)], ["A", "A"])
    try:
        validate_spec(dup)
        assert False, "应当拒绝重复编号"
    except ValidationError as e:
        assert any("重复" in d for d in e.details)

    bad = spec([bubble("", 0, 0), bubble("B", 30, 0)], ["", "B"])
    try:
        validate_spec(bad)
        assert False, "应当拒绝空编号"
    except ValidationError as e:
        assert any("非空" in d for d in e.details)


def test_validation_rejects_bad_bubble_count():
    one = spec([bubble("A", 0, 0)], ["A"])
    try:
        validate_spec(one)
        assert False
    except ValidationError as e:
        assert any("2..12" in d for d in e.details)
    many = spec([bubble(f"b{i}", i * 20, 0) for i in range(13)], [f"b{i}" for i in range(13)])
    try:
        validate_spec(many)
        assert False
    except ValidationError as e:
        assert any("2..12" in d for d in e.details)


def test_validation_rejects_tail_off_edge_and_bad_order():
    b = bubble("A", 0, 0)
    b["tail"] = {"x": 5, "y": 5}  # 内部点，不在泡边
    s = spec([b, bubble("B", 30, 0)], ["A", "B"])
    try:
        validate_spec(s)
        assert False
    except ValidationError as e:
        assert any("泡边" in d for d in e.details)

    s2 = spec([bubble("A", 0, 0), bubble("B", 30, 0)], ["A", "A"])
    try:
        validate_spec(s2)
        assert False
    except ValidationError as e:
        assert any("排列" in d for d in e.details)
