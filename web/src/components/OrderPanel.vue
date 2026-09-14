<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Spec } from '../types'

const props = defineProps<{ spec: Spec }>()
const emit = defineEmits<{
  (e: 'move', index: number, dir: -1 | 1): void
  (e: 'remove', id: string): void
  (e: 'add', id: string): void
}>()

const pick = ref('')

const missing = computed(() => props.spec.bubbles.filter((b) => !props.spec.order.includes(b.id)))

function addPicked() {
  if (pick.value) {
    emit('add', pick.value)
    pick.value = ''
  }
}
</script>

<template>
  <section class="panel">
    <h2>台词总序</h2>
    <ol class="order">
      <li v-for="(id, i) in spec.order" :key="id">
        <span class="seq">{{ i + 1 }}.</span>
        <span class="id">{{ id }}</span>
        <span class="ops">
          <button :disabled="i === 0" @click="emit('move', i, -1)">↑</button>
          <button :disabled="i === spec.order.length - 1" @click="emit('move', i, 1)">↓</button>
          <button @click="emit('remove', id)">✕</button>
        </span>
      </li>
    </ol>
    <div v-if="missing.length" class="add-row">
      <select v-model="pick">
        <option value="" disabled>选择编号</option>
        <option v-for="b in missing" :key="b.id" :value="b.id">{{ b.id }}</option>
      </select>
      <button :disabled="!pick" @click="addPicked">加入顺序</button>
    </div>
    <p class="hint">求解要求：按此顺序，相邻两泡之间必须能建立“在上 / 在左”关系，且不存在反向关系。</p>
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
.order {
  margin: 0 0 8px;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
li {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 3px 8px;
  font-size: 13px;
}
.seq {
  color: #94a3b8;
  width: 20px;
}
.id {
  font-weight: 700;
  flex: 1;
}
.ops {
  display: flex;
  gap: 4px;
}
.ops button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  padding: 1px 7px;
  font-size: 12px;
  cursor: pointer;
}
.ops button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.add-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
select {
  flex: 1;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 3px 6px;
}
.add-row button {
  border: 1px solid #c4b5fd;
  background: #f5f3ff;
  color: #6d28d9;
  border-radius: 6px;
  padding: 2px 10px;
  font-size: 12px;
  cursor: pointer;
}
.hint {
  margin: 0;
  font-size: 11px;
  color: #94a3b8;
}
</style>
