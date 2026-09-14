<script setup lang="ts">
import type { Spec } from '../types'

defineProps<{ spec: Spec }>()
</script>

<template>
  <section class="panel">
    <h2>版面参数</h2>
    <div class="grid">
      <label>安全区 X<input type="number" v-model.number="spec.safeArea.x" /></label>
      <label>安全区 Y<input type="number" v-model.number="spec.safeArea.y" /></label>
      <label>安全区宽<input type="number" v-model.number="spec.safeArea.w" min="1" /></label>
      <label>安全区高<input type="number" v-model.number="spec.safeArea.h" min="1" /></label>
      <label>阅读间距<input type="number" v-model.number="spec.gap" min="0" /></label>
      <label>单泡位移上限<input type="number" v-model.number="spec.maxStep" min="0" max="100" /></label>
    </div>
    <p class="hint">位移上限按曼哈顿距离 |dx|+|dy| 计；阅读间距用于判定“在上 / 在左”。</p>
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
.hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: #94a3b8;
}
</style>
