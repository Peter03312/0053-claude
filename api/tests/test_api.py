"""Flask API 测试：健康检查、求解、校验错误、项目版本管理。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config.update(TESTING=True)
    return app.test_client()


def valid_spec():
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


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_solve_ok(client):
    r = client.post("/api/solve", json={"spec": valid_spec()})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["movedCount"] >= 1  # 两泡重叠 1px，必须移动
    assert set(body["positions"]) == {"A", "B"}


def test_solve_validation_error_lists_details(client):
    bad = valid_spec()
    bad["bubbles"][1]["id"] = "A"  # 重复编号
    bad["order"] = ["A", "A"]
    r = client.post("/api/solve", json={"spec": bad})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"]["code"] == "validation"
    assert any("重复" in d for d in body["error"]["details"])


def test_solve_rejects_malformed_body(client):
    assert client.post("/api/solve", json={}).status_code == 400
    assert client.post("/api/solve", data="not json",
                       content_type="application/json").status_code == 400


def test_solve_no_solution_marks_conflict(client):
    s = valid_spec()
    s["bubbles"][0]["locked"] = True
    s["bubbles"][1]["locked"] = True
    s["bubbles"][1]["x"] = 5  # 与 A 重叠且都锁定
    r = client.post("/api/solve", json={"spec": s})
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "no_solution"
    assert {"pair": ["A", "B"]} in body["conflicts"]


def test_project_version_lifecycle(client):
    # 创建
    r = client.post("/api/projects", json={"name": "第一话分镜", "spec": valid_spec()})
    assert r.status_code == 201
    pid = r.get_json()["id"]
    assert r.get_json()["version"] == 1

    # 列表
    r = client.get("/api/projects")
    assert any(p["id"] == pid for p in r.get_json()["projects"])

    # 读取最新
    r = client.get(f"/api/projects/{pid}")
    assert r.get_json()["version"] == 1
    assert r.get_json()["spec"]["order"] == ["A", "B"]

    # 修改 → 新版本
    changed = valid_spec()
    changed["gap"] = 8
    r = client.put(f"/api/projects/{pid}", json={"spec": changed})
    assert r.get_json()["version"] == 2

    # 版本列表与历史版本读取
    r = client.get(f"/api/projects/{pid}/versions")
    assert [v["version_no"] for v in r.get_json()["versions"]] == [2, 1]
    r = client.get(f"/api/projects/{pid}/versions/1")
    assert r.get_json()["spec"]["gap"] == 0
    r = client.get(f"/api/projects/{pid}/versions/2")
    assert r.get_json()["spec"]["gap"] == 8


def test_project_not_found(client):
    assert client.get("/api/projects/999").status_code == 404
    assert client.put("/api/projects/999", json={"spec": {}}).status_code == 404
    assert client.get("/api/projects/999/versions").status_code == 404
    assert client.get("/api/projects/1/versions/3").status_code == 404


def test_project_validation(client):
    assert client.post("/api/projects", json={"name": "", "spec": {}}).status_code == 400
    assert client.post("/api/projects", json={"name": "x"}).status_code == 400
