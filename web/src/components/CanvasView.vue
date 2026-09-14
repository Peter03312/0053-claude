<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SolveFail, SolveOk, Spec } from '../types'

const props = defineProps<{
  spec: Spec
  result: SolveOk | null
  failure: SolveFail | null
  selectedId: string | null
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'move-bubble', id: string, x: number, y: number): void
  (e: 'move-anchor', id: string, x: number, y: number): void
}>()

const svgRef = ref<SVGSVGElement | null>(null)

const viewBox = computed(() => {
  const xs: number[] = []
  const ys: number[] = []
  const push = (x: number, y: number) => {
    xs.push(x)
    ys.push(y)
  }
  const s = props.spec.safeArea
  push(s.x, s.y)
  push(s.x + s.w, s.y + s.h)
  for (const p of props.spec.protections) {
    push(p.x, p.y)
    push(p.x + p.w, p.y + p.h)
  }
  for (const b of props.spec.bubbles) {
    push(b.x, b.y)
    push(b.x + b.w, b.y + b.h)
    push(b.anchor.x, b.anchor.y)
    const pos = props.result?.positions[b.id]
    if (pos) {
      push(pos.x, pos.y)
      push(pos.x + b.w, pos.y + b.h)
    }
  }
  if (!xs.length) return '0 0 400 300'
  const minX = Math.min(...xs) - 24
  const minY = Math.min(...ys) - 24
  const maxX = Math.max(...xs) + 24
  const maxY = Math.max(...ys) + 24
  return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`
})

const orderIndex = computed(() => {
  const m = new Map<string, number>()
  props.spec.order.forEach((id, i) => m.set(id, i + 1))
  return m
})

interface Candidate {
  id: string
  x: number
  y: number
  w: number
  h: number
  tailX: number
  tailY: number
  anchorX: number
  anchorY: number
  fromCX: number
  fromCY: number
  moved: boolean
}

const candidates = computed<Candidate[]>(() => {
  if (!props.result) return []
  const out: Candidate[] = []
  for (const b of props.spec.bubbles) {
    const pos = props.result.positions[b.id]
    if (!pos) continue
    out.push({
      id: b.id,
      x: pos.x,
      y: pos.y,
      w: b.w,
      h: b.h,
      tailX: pos.x + (b.tail.x - b.x),
      tailY: pos.y + (b.tail.y - b.y),
      anchorX: b.anchor.x,
      anchorY: b.anchor.y,
      fromCX: b.x + b.w / 2,
      fromCY: b.y + b.h / 2,
      moved: pos.x !== b.x || pos.y !== b.y,
    })
  }
  return out
})

const conflictPairs = computed(() => {
  if (!props.failure) return []
  const byId = new Map(props.spec.bubbles.map((b) => [b.id, b]))
  return props.failure.conflicts
    .map((c) => {
      const a = byId.get(c.pair[0])
      const b = byId.get(c.pair[1])
      if (!a || !b) return null
      return {
        key: c.pair.join('>'),
        x1: a.x + a.w / 2,
        y1: a.y + a.h / 2,
        x2: b.x + b.w / 2,
        y2: b.y + b.h / 2,
        label: `${c.pair[0]}→${c.pair[1]}`,
      }
    })
    .filter((v): v is NonNullable<typeof v> => v !== null)
})

const emptyIds = computed(() => new Set(props.failure?.emptyDomains ?? []))

// ---------------- 拖拽 ----------------
interface DragState {
  kind: 'bubble' | 'anchor'
  id: string
  dx: number
  dy: number
}
let drag: DragState | null = null

function toSvg(evt: PointerEvent): { x: number; y: number } {
  const svg = svgRef.value
  if (!svg) return { x: 0, y: 0 }
  const ctm = svg.getScreenCTM()
  if (!ctm) return { x: 0, y: 0 }
  const pt = new DOMPoint(evt.clientX, evt.clientY).matrixTransform(ctm.inverse())
  return { x: Math.round(pt.x), y: Math.round(pt.y) }
}

function startDrag(evt: PointerEvent, kind: 'bubble' | 'anchor', id: string) {
  const b = props.spec.bubbles.find((v) => v.id === id)
  if (!b || !svgRef.value) return
  emit('select', id)
  const p = toSvg(evt)
  const origin = kind === 'bubble' ? { x: b.x, y: b.y } : { x: b.anchor.x, y: b.anchor.y }
  drag = { kind, id, dx: p.x - origin.x, dy: p.y - origin.y }
  svgRef.value.setPointerCapture(evt.pointerId)
  evt.preventDefault()
}

function onMove(evt: PointerEvent) {
  if (!drag) return
  const p = toSvg(evt)
  const x = p.x - drag.dx
  const y = p.y - drag.dy
  if (drag.kind === 'bubble') emit('move-bubble', drag.id, x, y)
  else emit('move-anchor', drag.id, x, y)
}

function endDrag() {
  drag = null
}
</script>

<template>
  <svg
    ref="svgRef"
    :viewBox="viewBox"
    class="canvas"
    @pointermove="onMove"
    @pointerup="endDrag"
    @pointercancel="endDrag"
  >
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 1 L 9 5 L 0 9 z" fill="#16a34a" />
      </marker>
    </defs>

    <!-- 安全区 -->
    <rect
      :x="spec.safeArea.x"
      :y="spec.safeArea.y"
      :width="spec.safeArea.w"
      :height="spec.safeArea.h"
      class="safe"
    />
    <text :x="spec.safeArea.x + 6" :y="spec.safeArea.y + 16" class="safe-label">安全区</text>

    <!-- 保护框 -->
    <g v-for="(p, i) in spec.protections" :key="'prot' + i">
      <rect :x="p.x" :y="p.y" :width="p.w" :height="p.h" class="protection" />
      <text :x="p.x + 4" :y="p.y + 13" class="protection-label">保护</text>
    </g>

    <!-- 无解冲突边 -->
    <g v-for="c in conflictPairs" :key="'conflict' + c.key">
      <line :x1="c.x1" :y1="c.y1" :x2="c.x2" :y2="c.y2" class="conflict-line" />
      <text :x="(c.x1 + c.x2) / 2" :y="(c.y1 + c.y2) / 2 - 6" class="conflict-label">⚠ {{ c.label }}</text>
    </g>

    <!-- 气泡（原位） -->
    <g
      v-for="b in spec.bubbles"
      :key="b.id"
      class="bubble-group"
      :class="{ selected: b.id === selectedId, empty: emptyIds.has(b.id) }"
      @pointerdown="startDrag($event, 'bubble', b.id)"
    >
      <line :x1="b.tail.x" :y1="b.tail.y" :x2="b.anchor.x" :y2="b.anchor.y" class="tail" />
      <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="10" class="bubble" />
      <text :x="b.x + b.w / 2" :y="b.y + b.h / 2 + 5" class="bubble-id">{{ b.id }}</text>
      <template v-if="orderIndex.get(b.id)">
        <circle :cx="b.x + 12" :cy="b.y + 12" r="9" class="order-badge" />
        <text :x="b.x + 12" :y="b.y + 16" class="order-num">{{ orderIndex.get(b.id) }}</text>
      </template>
      <text v-if="b.locked" :x="b.x + b.w - 16" :y="b.y + 15" class="lock">🔒</text>
      <circle :cx="b.tail.x" :cy="b.tail.y" r="3.5" class="tail-dot" />
      <circle
        :cx="b.anchor.x"
        :cy="b.anchor.y"
        r="5.5"
        class="anchor"
        @pointerdown.stop="startDrag($event, 'anchor', b.id)"
      />
    </g>

    <!-- 候选叠加 -->
    <g v-for="c in candidates" :key="'cand' + c.id" class="candidate-group">
      <line
        v-if="c.moved"
        :x1="c.fromCX"
        :y1="c.fromCY"
        :x2="c.x + c.w / 2"
        :y2="c.y + c.h / 2"
        class="move-arrow"
        marker-end="url(#arrow)"
      />
      <line :x1="c.tailX" :y1="c.tailY" :x2="c.anchorX" :y2="c.anchorY" class="candidate-tail" />
      <rect :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="10" class="candidate" />
      <text :x="c.x + c.w / 2" :y="c.y + c.h / 2 + 5" class="candidate-id">{{ c.id }}</text>
      <circle :cx="c.tailX" :cy="c.tailY" r="3" class="candidate-tail-dot" />
    </g>
  </svg>
</template>

<style scoped>
.canvas {
  width: 100%;
  height: 100%;
  background: #fdf6ec;
  border-radius: 12px;
  touch-action: none;
  user-select: none;
}
.safe {
  fill: #ffffff;
  stroke: #94a3b8;
  stroke-width: 1.5;
}
.safe-label {
  font-size: 12px;
  fill: #94a3b8;
}
.protection {
  fill: rgba(239, 68, 68, 0.14);
  stroke: #ef4444;
  stroke-width: 1.2;
  stroke-dasharray: 5 3;
}
.protection-label {
  font-size: 10px;
  fill: #ef4444;
}
.conflict-line {
  stroke: #dc2626;
  stroke-width: 2.5;
  stroke-dasharray: 3 3;
}
.conflict-label {
  font-size: 12px;
  fill: #dc2626;
  font-weight: 700;
  text-anchor: middle;
}
.bubble-group {
  cursor: grab;
}
.bubble {
  fill: #ffffff;
  stroke: #0f172a;
  stroke-width: 1.6;
}
.bubble-group.selected .bubble {
  stroke: #7c3aed;
  stroke-width: 2.6;
}
.bubble-group.empty .bubble {
  stroke: #dc2626;
  stroke-dasharray: 4 3;
}
.bubble-id {
  font-size: 14px;
  font-weight: 700;
  fill: #0f172a;
  text-anchor: middle;
  pointer-events: none;
}
.order-badge {
  fill: #f472b6;
  stroke: #be185d;
  stroke-width: 1;
}
.order-num {
  font-size: 11px;
  fill: #ffffff;
  text-anchor: middle;
  font-weight: 700;
  pointer-events: none;
}
.lock {
  font-size: 11px;
  pointer-events: none;
}
.tail {
  stroke: #0f172a;
  stroke-width: 1.4;
}
.tail-dot {
  fill: #0f172a;
}
.anchor {
  fill: #f472b6;
  stroke: #be185d;
  stroke-width: 1.4;
  cursor: move;
}
.candidate {
  fill: rgba(34, 197, 94, 0.14);
  stroke: #16a34a;
  stroke-width: 1.8;
  stroke-dasharray: 6 4;
}
.candidate-id {
  font-size: 14px;
  font-weight: 700;
  fill: #16a34a;
  text-anchor: middle;
  pointer-events: none;
}
.candidate-tail {
  stroke: #16a34a;
  stroke-width: 1.4;
  stroke-dasharray: 5 3;
}
.candidate-tail-dot {
  fill: #16a34a;
}
.move-arrow {
  stroke: #16a34a;
  stroke-width: 1.4;
  stroke-dasharray: 2 2;
}
</style>
