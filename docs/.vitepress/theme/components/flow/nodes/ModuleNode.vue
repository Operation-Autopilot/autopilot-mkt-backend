<template>
  <div class="flow-node-module" :class="{ 'has-badge': data.lines }">
    <Handle type="target" :position="Position.Top" />
    <div class="module-accent" />
    <div class="module-body">
      <div class="module-label">{{ data.label }}</div>
      <div v-if="data.sublabel" class="module-sublabel">{{ data.sublabel }}</div>
    </div>
    <span v-if="data.lines" class="module-badge">{{ data.lines }}</span>
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
.flow-node-module {
  background: #1a2400;
  color: #f0f4e0;
  padding: 0;
  border-radius: 10px;
  border: 1.5px solid #3a5a00;
  font-family: 'Inter', sans-serif;
  text-align: left;
  position: relative;
  box-shadow:
    0 3px 12px rgba(26, 36, 0, 0.4),
    0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: grab;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
}
.flow-node-module:hover {
  transform: translateY(-2px);
  border-color: #90bd00;
  box-shadow:
    0 6px 20px rgba(26, 36, 0, 0.5),
    0 0 12px rgba(212, 255, 59, 0.2);
}
.flow-node-module:active {
  cursor: grabbing;
  transform: translateY(0);
}
.module-accent {
  width: 4px;
  min-height: 100%;
  background: linear-gradient(to bottom, #90bd00, #D4FF3B);
  flex-shrink: 0;
  border-top-left-radius: 8px;
  border-bottom-left-radius: 8px;
}
.module-body {
  padding: 10px 14px;
}
.module-label {
  font-weight: 600;
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
}
.module-sublabel {
  font-size: 10px;
  opacity: 0.65;
  margin-top: 3px;
  font-family: 'Inter', sans-serif;
}
.module-badge {
  position: absolute;
  top: -7px;
  right: -7px;
  background: linear-gradient(135deg, #D4FF3B, #b8e000);
  color: #1a2400;
  font-size: 9px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 10px;
  border: 1.5px solid #1a2400;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  font-family: 'JetBrains Mono', monospace;
}
</style>
