<script setup lang="ts">
import type { Spec } from '../types'

defineProps<{ spec: Spec }>()
const emit = defineEmits<{
  (e: 'add'): void
  (e: 'remove', index: number): void
}>()
</script>

<template>
  <section class="panel">
    <h2>保护框（{{ spec.protections.length }}）</h2>
    <p class="hint">保护框覆盖角色表情等关键画面：尾线接触或穿越即非法。</p>
    <div v-for="(p, i) in spec.protections" :key="i" class="prot">
      <div class="grid">
        <label>X<input type="number" v-model.number="p.x" /></label>
        <label>Y<input type="number" v-model.number="p.y" /></label>
        <label>宽<input type="number" v-model.number="p.w" min="1" /></label>
        <label>高<input type="number" v-model.number="p.h" min="1" /></label>
      </div>
      <button class="danger" @click="emit('remove', i)">删除</button>
    </div>
    <button class="add" @click="emit('add')">＋添加保护框</button>
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
.hint {
  margin: 0 0 8px;
  font-size: 11px;
  color: #94a3b8;
}
.prot {
  border-top: 1px dashed #e2e8f0;
  padding-top: 8px;
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
input {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 13px;
  width: 100%;
  box-sizing: border-box;
}
.danger {
  align-self: flex-start;
  border: 1px solid #fca5a5;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 8px;
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}
.add {
  border: 1px dashed #c4b5fd;
  background: #fff;
  color: #6d28d9;
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
}
</style>
