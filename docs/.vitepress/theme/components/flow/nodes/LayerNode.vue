<template>
  <div class="flow-node-layer">
    <Handle type="target" :position="Position.Top" />
    <div v-if="data.icon" class="layer-icon">{{ data.icon }}</div>
    <div class="layer-content">
      <div class="layer-label">{{ data.label }}</div>
      <div v-if="data.sublabel" class="layer-sublabel">{{ data.sublabel }}</div>
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
.flow-node-layer {
  background: linear-gradient(135deg, #5a7f00 0%, #6b8f00 50%, #90bd00 100%);
  color: #fff;
  padding: 14px 20px;
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.15);
  font-family: 'Inter', sans-serif;
  min-width: 180px;
  text-align: center;
  box-shadow:
    0 4px 16px rgba(107, 143, 0, 0.3),
    0 1px 3px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(4px);
  cursor: grab;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
}
.flow-node-layer:hover {
  transform: translateY(-2px);
  box-shadow:
    0 8px 24px rgba(107, 143, 0, 0.4),
    0 2px 6px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
}
.flow-node-layer:active {
  cursor: grabbing;
  transform: translateY(0);
}
.layer-icon {
  font-size: 20px;
  line-height: 1;
  flex-shrink: 0;
}
.layer-content {
}
.layer-label {
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 0.01em;
  white-space: nowrap;
}
.layer-sublabel {
  font-size: 10.5px;
  opacity: 0.8;
  margin-top: 3px;
  line-height: 1.3;
}
</style>
