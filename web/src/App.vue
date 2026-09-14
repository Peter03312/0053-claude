<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ApiError, api } from './api'
import CanvasView from './components/CanvasView.vue'
import BubblePanel from './components/BubblePanel.vue'
import GlobalPanel from './components/GlobalPanel.vue'
import OrderPanel from './components/OrderPanel.vue'
import ProtectionPanel from './components/ProtectionPanel.vue'
import type { ProjectInfo, SolveFail, SolveOk, Spec, VersionInfo } from './types'
import { validateSpec } from './validation'

function emptySpec(): Spec {
  return {
    safeArea: { x: 0, y: 0, w: 360, h: 640 },
    gap: 16,
    maxStep: 6,
    protections: [],
    bubbles: [],
    order: [],
  }
}

const spec = reactive<Spec>(emptySpec())
const selectedId = ref<string | null>(null)
const result = ref<SolveOk | null>(null)
const failure = ref<SolveFail | null>(null)
const serverErrors = ref<string[]>([])
const notice = ref('')
const solving = ref(false)

const projectId = ref<number | null>(null)
const projectName = ref('未命名分镜')
const projects = ref<ProjectInfo[]>([])
const versions = ref<VersionInfo[]>([])
const pickProject = ref('')
const pickVersion = ref('')

// 修改几何 / 顺序后，旧候选立即失效
watch(
  spec,
  () => {
    result.value = null
    failure.value = null
  },
  { deep: true },
)

const clientErrors = computed(() => validateSpec(spec))

function snapshot(): Spec {
  return JSON.parse(JSON.stringify(spec)) as Spec
}

async function guard(fn: () => Promise<void>) {
  serverErrors.value = []
  notice.value = ''
  try {
    await fn()
  } catch (e) {
    serverErrors.value = e instanceof ApiError ? e.details : [String(e)]
  }
}

// ---------------- 求解 ----------------
async function solve() {
  solving.value = true
  await guard(async () => {
    const r = await api.solve(snapshot())
    if (r.status === 'ok') {
      result.value = r
      failure.value = null
      notice.value = `求解成功：移动 ${r.movedCount} 泡，总位移 ${r.totalDisplacement}，单泡最大 ${r.maxDisplacement}`
    } else {
      failure.value = r
      result.value = null
    }
  })
  solving.value = false
}

function applyCandidate() {
  if (!result.value) return
  for (const b of spec.bubbles) {
    const pos = result.value.positions[b.id]
    if (!pos) continue
    const dx = pos.x - b.x
    const dy = pos.y - b.y
    b.x = pos.x
    b.y = pos.y
    b.tail.x += dx // 尾线起点随气泡同量平移
    b.tail.y += dy
  }
  notice.value = '已采用候选布局'
}

function clearCandidate() {
  result.value = null
  failure.value = null
}

// ---------------- 气泡编辑 ----------------
function nextId(): string {
  const used = new Set(spec.bubbles.map((b) => b.id))
  for (let i = 0; i < 26; i++) {
    const c = String.fromCharCode(65 + i)
    if (!used.has(c)) return c
  }
  let n = 1
  while (used.has(`泡${n}`)) n++
  return `泡${n}`
}

function overlaps(x: number, y: number, w: number, h: number): boolean {
  const hit = (r: { x: number; y: number; w: number; h: number }) =>
    x < r.x + r.w && r.x < x + w && y < r.y + r.h && r.y < y + h
  return spec.bubbles.some((b) => hit(b)) || spec.protections.some((p) => hit(p))
}

function freeSpot(w: number, h: number): { x: number; y: number } {
  const s = spec.safeArea
  for (let y = s.y; y + h <= s.y + s.h; y += 8) {
    for (let x = s.x; x + w <= s.x + s.w; x += 8) {
      if (!overlaps(x, y, w, h)) return { x, y }
    }
  }
  return { x: s.x, y: s.y }
}

function addBubble() {
  if (spec.bubbles.length >= 12) return
  const w = 90
  const h = 48
  const { x, y } = freeSpot(w, h)
  const id = nextId()
  spec.bubbles.push({
    id,
    x,
    y,
    w,
    h,
    tail: { x: x + Math.floor(w / 2), y: y + h },
    anchor: { x: x + Math.floor(w / 2), y: y + h + 56 },
    locked: false,
  })
  spec.order.push(id)
  selectedId.value = id
}

function removeBubble(id: string) {
  spec.bubbles = spec.bubbles.filter((b) => b.id !== id)
  spec.order = spec.order.filter((o) => o !== id)
  if (selectedId.value === id) selectedId.value = null
}

function renameBubble(oldId: string, newId: string) {
  const idx = spec.order.indexOf(oldId)
  if (idx >= 0) spec.order.splice(idx, 1, newId)
  const b = spec.bubbles.find((v) => v.id === oldId)
  if (b) b.id = newId
  if (selectedId.value === oldId) selectedId.value = newId
}

function moveBubble(id: string, x: number, y: number) {
  const b = spec.bubbles.find((v) => v.id === id)
  if (!b) return
  const dx = x - b.x
  const dy = y - b.y
  b.x = x
  b.y = y
  b.tail.x += dx
  b.tail.y += dy
}

function moveAnchor(id: string, x: number, y: number) {
  const b = spec.bubbles.find((v) => v.id === id)
  if (!b) return
  b.anchor.x = x
  b.anchor.y = y
}

// ---------------- 顺序 ----------------
function moveOrder(index: number, dir: -1 | 1) {
  const j = index + dir
  if (j < 0 || j >= spec.order.length) return
  const [id] = spec.order.splice(index, 1)
  spec.order.splice(j, 0, id)
}

function removeFromOrder(id: string) {
  spec.order = spec.order.filter((o) => o !== id)
}

function addToOrder(id: string) {
  if (!spec.order.includes(id)) spec.order.push(id)
}

// ---------------- 保护框 ----------------
function addProtection() {
  const s = spec.safeArea
  spec.protections.push({
    x: s.x + Math.floor(s.w / 2) - 30,
    y: s.y + Math.floor(s.h / 2) - 20,
    w: 60,
    h: 40,
  })
}

function removeProtection(index: number) {
  spec.protections.splice(index, 1)
}

// ---------------- 项目与版本 ----------------
async function refreshProjects() {
  await guard(async () => {
    projects.value = (await api.listProjects()).projects
  })
}

function loadSpec(loaded: Spec, name: string, pid: number) {
  const fresh = emptySpec()
  Object.assign(fresh, JSON.parse(JSON.stringify(loaded)))
  Object.assign(spec, fresh)
  projectName.value = name
  projectId.value = pid
  selectedId.value = null
}

async function save() {
  await guard(async () => {
    const name = projectName.value.trim() || '未命名分镜'
    if (projectId.value == null) {
      const r = await api.createProject(name, snapshot())
      projectId.value = r.id
      notice.value = `已创建项目 #${r.id}（版本 1）`
    } else {
      const r = await api.putProject(projectId.value!, name, snapshot())
      notice.value = `已保存为版本 ${r.version}`
    }
    projects.value = (await api.listProjects()).projects
    versions.value = (await api.listVersions(projectId.value!)).versions
  })
}

async function saveAsNew() {
  await guard(async () => {
    const name = projectName.value.trim() || '未命名分镜'
    const r = await api.createProject(name, snapshot())
    projectId.value = r.id
    notice.value = `已另存为新项目 #${r.id}`
    projects.value = (await api.listProjects()).projects
    versions.value = (await api.listVersions(r.id)).versions
  })
}

async function loadProject() {
  const id = Number(pickProject.value)
  if (!id) return
  await guard(async () => {
    const p = await api.getProject(id)
    loadSpec(p.spec, p.name, p.id)
    versions.value = (await api.listVersions(id)).versions
    notice.value = `已加载项目 #${id} 的最新版本（v${p.version}）`
  })
}

async function loadVersion() {
  const v = Number(pickVersion.value)
  if (!v || projectId.value == null) return
  await guard(async () => {
    const r = await api.getVersion(projectId.value!, v)
    loadSpec(r.spec, projectName.value, projectId.value!)
    notice.value = `已回滚载入版本 v${r.version}（再次保存会生成新版本）`
  })
}

function resetAll() {
  Object.assign(spec, emptySpec())
  selectedId.value = null
  projectId.value = null
  projectName.value = '未命名分镜'
  versions.value = []
  notice.value = '已清空画布'
}

onMounted(refreshProjects)
</script>

<template>
  <div class="app">
    <header>
      <h1>条漫对白校样台</h1>
      <div class="project-bar">
        <input v-model="projectName" placeholder="分镜名称" class="name" />
        <button @click="save">保存（{{ projectId == null ? '新建项目' : '新版本' }}）</button>
        <button @click="saveAsNew">另存为新项目</button>
        <select v-model="pickProject">
          <option value="" disabled>选择项目</option>
          <option v-for="p in projects" :key="p.id" :value="String(p.id)">
            #{{ p.id }} {{ p.name }}（{{ p.versions }} 版）
          </option>
        </select>
        <button :disabled="!pickProject" @click="loadProject">加载</button>
        <select v-model="pickVersion" :disabled="!versions.length">
          <option value="" disabled>历史版本</option>
          <option v-for="v in versions" :key="v.version_no" :value="String(v.version_no)">
            v{{ v.version_no }} · {{ v.created_at }}
          </option>
        </select>
        <button :disabled="!pickVersion" @click="loadVersion">载入该版本</button>
        <button class="ghost" @click="resetAll">清空画布</button>
      </div>
    </header>

    <main>
      <aside class="left">
        <GlobalPanel :spec="spec" />
        <BubblePanel
          :spec="spec"
          :selected-id="selectedId"
          @select="selectedId = $event"
          @add="addBubble"
          @remove="removeBubble"
          @rename="renameBubble"
        />
        <OrderPanel
          :spec="spec"
          @move="moveOrder"
          @remove="removeFromOrder"
          @add="addToOrder"
        />
        <ProtectionPanel :spec="spec" @add="addProtection" @remove="removeProtection" />
      </aside>

      <section class="stage">
        <CanvasView
          :spec="spec"
          :result="result"
          :failure="failure"
          :selected-id="selectedId"
          @select="selectedId = $event"
          @move-bubble="moveBubble"
          @move-anchor="moveAnchor"
        />
      </section>

      <aside class="right">
        <section class="panel solve">
          <h2>校样求解</h2>
          <button class="primary" :disabled="solving || clientErrors.length > 0" @click="solve">
            {{ solving ? '求解中…' : '求解排版' }}
          </button>
          <button v-if="result" class="primary ok" @click="applyCandidate">采用此候选</button>
          <button v-if="result || failure" class="ghost" @click="clearCandidate">清除候选</button>
          <p v-if="notice" class="notice">{{ notice }}</p>
          <div v-if="result" class="stats">
            <p>移动泡数：<b>{{ result.movedCount }}</b></p>
            <p>总曼哈顿位移：<b>{{ result.totalDisplacement }}</b></p>
            <p>单泡最大位移：<b>{{ result.maxDisplacement }}</b></p>
          </div>
          <div v-if="failure" class="failure">
            <p class="fail-title">无解</p>
            <p>{{ failure.message }}</p>
            <p v-for="c in failure.conflicts" :key="c.pair.join('>')" class="conflict-item">
              冲突边：{{ c.pair[0] }} → {{ c.pair[1] }}
            </p>
          </div>
        </section>

        <section v-if="clientErrors.length || serverErrors.length" class="panel errors">
          <h2>需要修正</h2>
          <ul>
            <li v-for="(e, i) in clientErrors" :key="'c' + i">{{ e }}</li>
            <li v-for="(e, i) in serverErrors" :key="'s' + i" class="server">{{ e }}</li>
          </ul>
        </section>

        <section class="panel legend">
          <h2>图例</h2>
          <p><span class="sw bubble-sw"></span>对白泡（粉点＝角色落点，可拖动）</p>
          <p><span class="sw prot-sw"></span>保护框（尾线不可触碰）</p>
          <p><span class="sw cand-sw"></span>候选位置（绿色虚线）</p>
          <p><span class="sw conf-sw"></span>无解冲突边（红色虚线）</p>
        </section>
      </aside>
    </main>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', system-ui, sans-serif;
  background: #fdf6ec;
  color: #0f172a;
}
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
header {
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f1e3d3;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
h1 {
  font-size: 18px;
  margin: 0;
  color: #be185d;
}
.project-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.project-bar .name {
  width: 140px;
}
input,
select {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 13px;
}
button {
  border: 1px solid #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  border-radius: 8px;
  padding: 5px 12px;
  font-size: 13px;
  cursor: pointer;
}
button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
button.ghost {
  background: #fff;
  border-color: #e2e8f0;
  color: #64748b;
}
main {
  flex: 1;
  display: grid;
  grid-template-columns: 300px 1fr 280px;
  gap: 12px;
  padding: 12px;
  min-height: 0;
}
aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}
.stage {
  min-height: 70vh;
}
.panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
}
.panel h2 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #7c3aed;
}
.solve .primary {
  width: 100%;
  margin-bottom: 6px;
  background: #7c3aed;
  color: #fff;
  border-color: #7c3aed;
  font-weight: 700;
}
.solve .primary.ok {
  background: #16a34a;
  border-color: #16a34a;
}
.solve .ghost {
  width: 100%;
}
.notice {
  font-size: 12px;
  color: #16a34a;
  margin: 6px 0 0;
}
.stats {
  margin-top: 8px;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stats p {
  margin: 0;
}
.failure {
  margin-top: 8px;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  color: #b91c1c;
}
.fail-title {
  font-weight: 700;
  margin: 0 0 4px;
}
.failure p {
  margin: 2px 0;
}
.conflict-item {
  font-weight: 700;
}
.errors ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #b91c1c;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.errors .server {
  color: #9a3412;
}
.legend p {
  margin: 4px 0;
  font-size: 12px;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sw {
  display: inline-block;
  width: 18px;
  height: 12px;
  border-radius: 3px;
}
.bubble-sw {
  border: 1.6px solid #0f172a;
  background: #fff;
}
.prot-sw {
  border: 1.2px dashed #ef4444;
  background: rgba(239, 68, 68, 0.14);
}
.cand-sw {
  border: 1.8px dashed #16a34a;
  background: rgba(34, 197, 94, 0.14);
}
.conf-sw {
  border-top: 2.5px dashed #dc2626;
  height: 0;
}
</style>
