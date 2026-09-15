"""Flask 入口：版本管理与求解 API。"""

import json
import os

from flask import Flask, g, jsonify, request

from . import db as dbmod
from .solver import SearchBudgetExceeded, solve
from .validation import ValidationError, validate_spec


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH") or dbmod.DB_PATH

    def get_db():
        if "db" not in g:
            g.db = dbmod.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.after_request
    def cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
        return resp

    def err(code, message, status, details=None):
        body = {"error": {"code": code, "message": message}}
        if details:
            body["error"]["details"] = details
        return jsonify(body), status

    # ---------- 健康检查 ----------
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    # ---------- 求解 ----------
    @app.post("/api/solve")
    def solve_route():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or "spec" not in payload:
            return err("bad_request", "请求体必须是含 spec 字段的 JSON 对象", 400)
        try:
            result = solve(payload["spec"])
        except ValidationError as e:
            return err("validation", "校样规格不合法", 400, e.details)
        except SearchBudgetExceeded:
            return err(
                "search_budget_exceeded",
                "搜索超出预算：请减小 maxStep、增加锁定或简化布局后重试",
                422,
            )
        return jsonify(result)

    # ---------- 项目与版本 ----------
    @app.post("/api/projects")
    def create_project():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return err("bad_request", "请求体必须是 JSON 对象", 400)
        name = payload.get("name")
        spec = payload.get("spec")
        if not isinstance(name, str) or not name.strip():
            return err("validation", "name 必须是非空字符串", 400)
        if not isinstance(spec, dict):
            return err("validation", "spec 必须是 JSON 对象", 400)
        try:
            validate_spec(spec)
        except ValidationError as e:
            return err("validation", "分镜规格不合法，无法保存", 400, e.details)
        pid, version = dbmod.create_project(get_db(), name.strip(), json.dumps(spec))
        return jsonify({"id": pid, "version": version}), 201

    @app.get("/api/projects")
    def list_projects():
        return jsonify({"projects": dbmod.list_projects(get_db())})

    @app.get("/api/projects/<int:pid>")
    def get_project(pid):
        row = dbmod.get_project(get_db(), pid)
        if row is None:
            return err("not_found", f"项目 {pid} 不存在", 404)
        latest = row["latest"]
        return jsonify(
            {
                "id": row["project"]["id"],
                "name": row["project"]["name"],
                "version": latest["version_no"] if latest else None,
                "spec": json.loads(latest["payload"]) if latest else None,
            }
        )

    @app.put("/api/projects/<int:pid>")
    def put_project(pid):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("spec"), dict):
            return err("validation", "请求体必须包含 spec 对象", 400)
        name = payload.get("name")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            return err("validation", "name 若提供则必须是非空字符串", 400)
        if dbmod.get_project(get_db(), pid) is None:
            return err("not_found", f"项目 {pid} 不存在", 404)
        try:
            validate_spec(payload["spec"])
        except ValidationError as e:
            return err("validation", "分镜规格不合法，无法保存为新版本", 400, e.details)
        version = dbmod.add_version(
            get_db(), pid, json.dumps(payload["spec"]), name.strip() if isinstance(name, str) else None
        )
        if version is None:
            return err("not_found", f"项目 {pid} 不存在", 404)
        return jsonify({"id": pid, "version": version})

    @app.get("/api/projects/<int:pid>/versions")
    def list_versions(pid):
        rows = dbmod.list_versions(get_db(), pid)
        if rows is None:
            return err("not_found", f"项目 {pid} 不存在", 404)
        return jsonify({"versions": rows})

    @app.get("/api/projects/<int:pid>/versions/<int:version_no>")
    def get_version(pid, version_no):
        row = dbmod.get_version(get_db(), pid, version_no)
        if row is None:
            return err("not_found", f"项目 {pid} 的版本 {version_no} 不存在", 404)
        return jsonify(
            {
                "id": pid,
                "version": row["version_no"],
                "created_at": row["created_at"],
                "spec": json.loads(row["payload"]),
            }
        )

    @app.errorhandler(404)
    def not_found(_e):
        return err("not_found", "接口不存在", 404)

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return err("method_not_allowed", "方法不允许", 405)

    @app.errorhandler(500)
    def internal(_e):
        return err("internal", "服务器内部错误", 500)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
