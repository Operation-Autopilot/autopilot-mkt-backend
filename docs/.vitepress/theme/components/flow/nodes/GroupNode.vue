<template>
  <div class="flow-node-group" :style="groupStyle">
    <div class="group-header" :style="headerStyle">
      <span class="group-title">{{ data.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })

const defaultBorder = 'rgba(212, 255, 59, 0.4)'
const defaultBg = 'rgba(212, 255, 59, 0.04)'

const groupStyle = computed(() => ({
  width: (props.data.width || 280) + 'px',
  height: (props.data.height || 200) + 'px',
  '--group-border': props.data.borderColor || defaultBorder,
  '--group-bg': props.data.bgColor || defaultBg,
  borderColor: props.data.borderColor || defaultBorder,
  backgroundColor: props.data.bgColor || defaultBg,
}))

const headerStyle = computed(() => ({
  borderColor: props.data.borderColor || defaultBorder,
}))
</script>

<style scoped>
.flow-node-group {
  border: 2px dashed;
  border-radius: 14px;
  position: relative;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}
.flow-node-group:hover {
  filter: brightness(1.1);
  opacity: 0.95;
}
.group-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 6px 14px;
  border-bottom: 1px dashed;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  background: linear-gradient(
    to right,
    rgba(212, 255, 59, 0.08),
    transparent
  );
}
.group-title {
  color: #6b8f00;
  font-size: 11px;
  font-weight: 700;
  font-family: 'Inter', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
</style>
