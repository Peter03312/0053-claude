"""一次性联调冒烟：对运行中的 api / web 服务做端到端检查。

环境变量：
  API_URL  默认 http://api:5000
  WEB_URL  默认 http://web:80
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("API_URL", "http://api:5000").rstrip("/")
WEB = os.environ.get("WEB_URL", "http://web:80").rstrip("/")

checks = 0


def fail(msg):
    print(f"[SMOKE FAIL] {msg}")
    sys.exit(1)


def ok(msg):
    global checks
    checks += 1
    print(f"[smoke ok] {msg}")


def req(method, url, payload=None, expect=200):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            body = resp.read().decode()
            status = resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        status = e.code
    if status != expect:
        fail(f"{method} {url} 期望 HTTP {expect}，实际 {status}：{body[:200]}")
    return json.loads(body) if body else None


def wait_ready():
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{API}/api/health", timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    fail("API 健康检查超时")


def make_spec():
    return {
        "safeArea": {"x": -50, "y": -50, "w": 300, "h": 300},
        "gap": 0,
        "maxStep": 2,
        "protections": [],
        "bubbles": [
            {"id": "A", "x": 0, "y": 0, "w": 10, "h": 10,
             "tail": {"x": 5, "y": 0}, "anchor": {"x": 5, "y": -30}, "locked": False},
            {"id": "B", "x": 9, "y": 0, "w": 10, "h": 10,
             "tail": {"x": 14, "y": 0}, "anchor": {"x": 14, "y": -30}, "locked": False},
        ],
        "order": ["A", "B"],
    }


def main():
    wait_ready()
    ok("API /api/health 就绪")

    r = req("POST", f"{API}/api/solve", {"spec": make_spec()})
    if r.get("status") != "ok" or r.get("movedCount", 0) < 1:
        fail(f"求解冒烟结果异常：{r}")
    ok(f"求解接口返回唯一候选（移动 {r['movedCount']} 泡）")

    bad = make_spec()
    bad["bubbles"][1]["id"] = "A"
    r = req("POST", f"{API}/api/solve", {"spec": bad}, expect=400)
    if "details" not in r.get("error", {}):
        fail(f"校验错误缺少 details：{r}")
    ok("非法规格返回 400 及逐条错误")

    locked = make_spec()
    locked["bubbles"][0]["locked"] = True
    locked["bubbles"][1]["locked"] = True
    locked["bubbles"][1]["x"] = 5
    r = req("POST", f"{API}/api/solve", {"spec": locked})
    if r.get("status") != "no_solution" or not r.get("conflicts"):
        fail(f"锁定重叠应报无解并标冲突边：{r}")
    ok("无解场景返回冲突边")

    r = req("POST", f"{API}/api/projects", {"name": "冒烟分镜", "spec": make_spec()}, expect=201)
    pid = r["id"]
    changed = make_spec()
    changed["gap"] = 8
    r = req("PUT", f"{API}/api/projects/{pid}", {"spec": changed})
    if r.get("version") != 2:
        fail(f"版本递增失败：{r}")
    r = req("GET", f"{API}/api/projects/{pid}/versions/1")
    if r["spec"]["gap"] != 0:
        fail("历史版本内容不正确")
    ok("项目创建 → 新版本 → 历史版本读取")

    bad_save = make_spec()
    bad_save["bubbles"][1]["id"] = "A"
    bad_save["order"] = ["A", "A"]
    req("PUT", f"{API}/api/projects/{pid}", {"spec": bad_save}, expect=400)
    r = req("GET", f"{API}/api/projects/{pid}")
    if r.get("version") != 2:
        fail(f"非法保存污染了版本号：{r}")
    ok("非法分镜被拒绝保存且版本号未受污染")

    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{WEB}/", timeout=3) as resp:
                html = resp.read().decode()
                if resp.status == 200 and 'id="app"' in html:
                    break
        except Exception:
            pass
        time.sleep(1)
    else:
        fail("Web 首页不可访问或缺少 #app 挂载点")
    ok("Web 首页可访问")

    print(f"[SMOKE PASS] 全部 {checks} 项冒烟检查通过")


if __name__ == "__main__":
    main()
