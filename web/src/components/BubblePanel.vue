<script setup lang="ts">
import { computed } from 'vue'
import type { Spec } from '../types'

const props = defineProps<{ spec: Spec; selectedId: string | null }>()
const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'add'): void
  (e: 'remove', id: string): void
  (e: 'rename', oldId: string, newId: string): void
}>()

const selected = computed(() => props.spec.bubbles.find((b) => b.id === props.selectedId) ?? null)

function onRename(evt: Event, oldId: string) {
  const v = (evt.target as HTMLInputElement).value
  emit('rename', oldId, v)
}
</script>

<template>
  <section class="panel">
    <h2>对白泡（{{ spec.bubbles.length }}/12）</h2>
    <div class="chips">
      <button
        v-for="b in spec.bubbles"
        :key="b.id"
        class="chip"
        :class="{ active: b.id === selectedId }"
        @click="emit('select', b.id)"
      >
        {{ b.id }}<span v-if="b.locked">🔒</span>
      </button>
      <button class="chip add" :disabled="spec.bubbles.length >= 12" @click="emit('add')">＋添加</button>
    </div>

    <div v-if="selected" class="editor">
      <label>编号
        <input :value="selected.id" @change="onRename($event, selected.id)" />
      </label>
      <div class="grid">
        <label>X<input type="number" v-model.number="selected.x" /></label>
        <label>Y<input type="number" v-model.number="selected.y" /></label>
        <label>宽<input type="number" v-model.number="selected.w" min="1" /></label>
        <label>高<input type="number" v-model.number="selected.h" min="1" /></label>
        <label>尾线 X<input type="number" v-model.number="selected.tail.x" /></label>
        <label>尾线 Y<input type="number" v-model.number="selected.tail.y" /></label>
        <label>落点 X<input type="number" v-model.number="selected.anchor.x" /></label>
        <label>落点 Y<input type="number" v-model.number="selected.anchor.y" /></label>
      </div>
      <label class="row">
        <input type="checkbox" v-model="selected.locked" /> 锁定（求解时禁止移动）
      </label>
      <button class="danger" @click="emit('remove', selected.id)">删除此气泡</button>
    </div>
    <p v-else class="hint">点击画布或上方编号选择一个气泡进行编辑；也可以直接在画布上拖动气泡与粉色落点。</p>
  </section>
</template>

<style scoped>
.panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
}
h2 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #7c3aed;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.chip {
  border: 1px solid #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}
.chip.active {
  background: #7c3aed;
  color: #fff;
}
.chip.add {
  border-style: dashed;
  background: #fff;
}
.chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
}
label {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #475569;
  gap: 2px;
}
label.row {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}
input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}
input[type='checkbox'] {
  width: auto;
}
.danger {
  align-self: flex-start;
  border: 1px solid #fca5a5;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}
.hint {
  margin: 0;
  font-size: 11px;
  color: #94a3b8;
}
</style>
