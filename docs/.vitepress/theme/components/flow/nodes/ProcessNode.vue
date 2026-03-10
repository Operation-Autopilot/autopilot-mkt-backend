<template>
  <div class="flow-node-process">
    <Handle type="target" :position="Position.Top" />
    <span v-if="data.step" class="process-step">{{ data.step }}</span>
    <div class="process-body">
      <div class="process-label">{{ data.label }}</div>
      <div v-if="data.sublabel" class="process-sublabel">{{ data.sublabel }}</div>
    </div>
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
.flow-node-process {
  background: #fff;
  color: #2d3436;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1.5px solid #d9e8b0;
  font-family: 'Inter', sans-serif;
  min-width: 140px;
  text-align: left;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.06),
    0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: grab;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  align-items: center;
  gap: 10px;
}
.flow-node-process:hover {
  transform: translateY(-2px);
  border-color: #90bd00;
  box-shadow:
    0 6px 18px rgba(144, 189, 0, 0.15),
    0 2px 4px rgba(0, 0, 0, 0.06);
}
.flow-node-process:active {
  cursor: grabbing;
  transform: translateY(0);
}
.process-step {
  background: linear-gradient(135deg, #6b8f00, #90bd00);
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
  box-shadow: 0 2px 4px rgba(107, 143, 0, 0.3);
}
.process-body {
}
.process-label {
  font-weight: 600;
  font-size: 12px;
  white-space: nowrap;
}
.process-sublabel {
  font-size: 10px;
  color: #718096;
  margin-top: 3px;
  line-height: 1.3;
}
</style>
