<template>
  <div
    class="flow-node-state"
    :class="{
      'state-start': data.variant === 'start',
      'state-end': data.variant === 'end',
    }"
  >
    <Handle type="target" :position="Position.Top" />
    <div v-if="data.variant === 'start'" class="state-dot start-dot" />
    <div v-else-if="data.variant === 'end'" class="state-dot end-dot" />
    <div class="state-label">{{ data.label }}</div>
    <div v-if="data.sublabel" class="state-sublabel">{{ data.sublabel }}</div>
    <Handle type="source" :position="Position.Bottom" />
    <Handle v-if="data.handleRight" type="source" :position="Position.Right" :id="'right'" />
    <Handle v-if="data.handleRightTarget" type="target" :position="Position.Right" :id="'right-in'" />
    <Handle v-if="data.handleLeft" type="target" :position="Position.Left" :id="'left'" />
    <Handle v-if="data.handleLeftSource" type="source" :position="Position.Left" :id="'left-out'" />
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'

defineProps({ data: { type: Object, required: true } })
</script>

<style scoped>
.flow-node-state {
  background: linear-gradient(145deg, #fafaf0, #f4f4e0);
  color: #2d3436;
  padding: 10px 20px;
  border-radius: 24px;
  border: 2.5px solid #D4FF3B;
  font-family: 'Inter', sans-serif;
  min-width: 120px;
  text-align: center;
  box-shadow:
    0 2px 8px rgba(212, 255, 59, 0.15),
    0 1px 2px rgba(0, 0, 0, 0.06);
  cursor: grab;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
.flow-node-state:hover {
  transform: translateY(-2px) scale(1.02);
  border-color: #90bd00;
  box-shadow:
    0 6px 18px rgba(212, 255, 59, 0.25),
    0 0 8px rgba(212, 255, 59, 0.15);
}
.flow-node-state:active {
  cursor: grabbing;
  transform: translateY(0) scale(1);
}

/* Start variant */
.state-start {
  border-color: #6b8f00;
  background: linear-gradient(145deg, #f0f4e0, #e0e8c0);
  box-shadow:
    0 2px 8px rgba(107, 143, 0, 0.2),
    0 0 0 3px rgba(107, 143, 0, 0.08);
}
.state-start:hover {
  border-color: #5a7f00;
  box-shadow:
    0 6px 18px rgba(107, 143, 0, 0.3),
    0 0 0 4px rgba(107, 143, 0, 0.12);
}

/* End variant */
.state-end {
  border-color: #e17055;
  background: linear-gradient(145deg, #fbe9e7, #ffccbc);
  box-shadow:
    0 2px 8px rgba(225, 112, 85, 0.2),
    0 0 0 3px rgba(225, 112, 85, 0.08);
}
.state-end:hover {
  border-color: #c0392b;
  box-shadow:
    0 6px 18px rgba(225, 112, 85, 0.3),
    0 0 0 4px rgba(225, 112, 85, 0.12);
}

.state-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.start-dot {
  background: #6b8f00;
  box-shadow: 0 0 6px rgba(107, 143, 0, 0.5);
  animation: pulse-lime 2s ease-in-out infinite;
}
.end-dot {
  background: #e17055;
  box-shadow: 0 0 6px rgba(225, 112, 85, 0.5);
}

@keyframes pulse-lime {
  0%, 100% { box-shadow: 0 0 4px rgba(107, 143, 0, 0.4); }
  50% { box-shadow: 0 0 12px rgba(107, 143, 0, 0.7); }
}

.state-label {
  font-weight: 700;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}
.state-sublabel {
  width: 100%;
  font-size: 10px;
  color: #4a5568;
  margin-top: 2px;
  font-family: 'Inter', sans-serif;
}
</style>
