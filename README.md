# 条漫对白校样台

面向漫画社团的竖屏条漫对白排版校样工具：在画布上录入安全区、保护框、
2–12 个带唯一编号的对白泡（含泡边尾线起点与角色落点）、台词总序、阅读间距、
锁定项与单泡最大曼哈顿位移，求解器给出**不遮画面且只有一种对白读序**的
候选布局；无解时标出冲突边，帮助社团在发布前修正分镜。

- 前端：Vue 3 + TypeScript + Vite（SVG 画布，气泡/落点可拖拽，候选绿色虚线叠加）
- 后端：Flask + SQLite（项目版本管理 + 求解 API）
- 联调：Docker Compose（web / api / 一次性 verify）

## 快速开始

```bash
docker compose up --build
```

- Web：<http://localhost:8080>
- API：<http://localhost:5001/api/health>

宿主端口可用环境变量覆盖：

```bash
APP_PORT=9000 API_PORT=9001 docker compose up --build
```

一次性验证（运行后端测试、构建前端镜像、对运行中服务做接口冒烟）：

```bash
docker compose up --build --abort-on-container-exit --exit-code-from verify verify
# 或完整拉起后单独跑：docker compose up --build verify
```

`verify` 服务依次执行：`pytest` 后端测试套件 → 对 api 做健康/求解/校验/版本冒烟 →
检查 web 首页可访问，全部通过才以 0 退出。

## 排版规则（与求解器严格一致）

1. **阅读关系建图**
   - A 底边 + 阅读间距 ≤ B 顶边 ⇒ 判 A 在 B 上（A 先读）；
   - 纵向重叠 ≥ 较矮泡高度一半，且 A 右边 + 阅读间距 ≤ B 左边 ⇒ 判 A 在 B 左（A 先读）。
2. 建图后必须**无环且唯一拓扑序 = 台词总序**。等价判定：总序中相邻泡之间必须
   存在前向边，且任意泡对之间不得存在反向边。
3. 每个气泡完整落在安全区内；气泡两两互不接触（贴边也算接触）。
4. 气泡移动时尾线起点同量平移；尾线段**接触或穿越其他气泡、保护框均非法**。
5. 每泡位移满足 |dx|+|dy| ≤ 单泡上限；锁定泡位移恒为 0。
6. 候选按字典序最小化：(移动泡数, 总曼哈顿位移, 单泡最大曼哈顿位移)；
   仍并列时，按气泡编号 Unicode 码点升序排列的候选左上角 (x, y) 序列取字典序
   最小者 —— 结果唯一确定、可复现。

无解时返回**冲突边**（台词总序中找不到任何相容位置的相邻泡对）与无可行位置的
气泡列表，前端以红色虚线标出；修改任何几何或顺序后，旧候选叠加立即清除。

## 本地开发

```bash
# 后端（Python 3.11+）
cd api
pip install -r requirements.txt
python -m app.main            # http://localhost:5000

# 前端（Node 20+）
cd web
npm ci
npm run dev                   # http://localhost:5173，/api 代理到 5000
```

## 测试

```bash
cd api && python -m pytest tests -q     # 求解器场景 + API 测试
cd web && npm run build                 # vue-tsc 类型检查 + 产物构建
```

求解器测试覆盖：协同移动（单泡位移不足、两泡各让一格）、尾线阻断（保护框与
其他气泡两类）、锁定无解（冲突边回报）、稳定并列（等优方案按编号序 (x,y)
字典序取唯一解，且重复求解结果一致），以及间距判定、半高重叠、贴边接触、
安全区约束与入参校验。

## API 摘要

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/solve` | 求解，body：`{"spec": …}` |
| POST | `/api/projects` | 新建项目（版本 1），body：`{"name", "spec"}` |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/<id>` | 最新版本 |
| PUT | `/api/projects/<id>` | 保存为新版本，body：`{"name"?, "spec"}` |
| GET | `/api/projects/<id>/versions` | 版本列表 |
| GET | `/api/projects/<id>/versions/<n>` | 读取历史版本 |

求解成功：`{"status":"ok","movedCount","totalDisplacement","maxDisplacement","positions","edges"}`；
无解：`{"status":"no_solution","message","conflicts":[{"pair":[idA,idB]}],"emptyDomains"}`；
规格非法：HTTP 400，`error.details` 为逐条中文错误。

### spec 数据模型

```json
{
  "safeArea": {"x": 0, "y": 0, "w": 360, "h": 640},
  "gap": 16,
  "maxStep": 6,
  "protections": [{"x": 40, "y": 200, "w": 60, "h": 40}],
  "bubbles": [
    {"id": "A", "x": 40, "y": 40, "w": 90, "h": 48,
     "tail": {"x": 85, "y": 88}, "anchor": {"x": 85, "y": 144}, "locked": false}
  ],
  "order": ["A", "B"]
}
```

- 坐标均为整数；`tail` 必须落在所属气泡的矩形边界上；
- `bubbles` 2–12 个，`id` 唯一非空；`order` 必须是全部编号的一个排列；
- `locked: true` 的气泡求解时不可移动。

## 目录结构

```
├── docker-compose.yml      # web / api / verify 联调
├── api/                    # Flask + SQLite 后端
│   ├── app/
│   │   ├── geometry.py     # 整数几何：矩形分离、线段-矩形相交、在上/在左
│   │   ├── validation.py   # spec 校验（中文逐条错误）
│   │   ├── solver.py       # 分支定界求解器 + 冲突边定位
│   │   ├── db.py           # 项目/版本 SQLite 存取
│   │   └── main.py         # HTTP API
│   └── tests/              # pytest：四大场景 + 规则与接口
├── web/                    # Vue 3 + TS 前端（SVG 画布）
└── verify/                 # 一次性验证：pytest + 接口冒烟
```
