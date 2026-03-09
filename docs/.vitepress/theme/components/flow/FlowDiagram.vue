<template>
  <ClientOnly>
    <template #fallback>
      <div class="flow-diagram-fallback">
        <div class="fallback-spinner" />
        <span>Loading diagram...</span>
      </div>
    </template>
    <div class="flow-diagram-wrapper" :style="{ height }">
      <VueFlow
        :nodes="nodes"
        :edges="edges"
        :node-types="nodeTypes"
        :fit-view="fitView"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :zoom-on-scroll="true"
        :pan-on-drag="true"
        :snap-to-grid="true"
        :snap-grid="[10, 10]"
        :min-zoom="0.3"
        :max-zoom="2.5"
        :default-edge-options="defaultEdgeOptions"
        :elevate-edges-on-select="true"
        @node-drag-start="onDragStart"
        @node-drag-stop="onDragStop"
      >
        <Background :gap="20" :size="1.5" pattern-color="var(--flow-grid-color, rgba(107, 143, 0, 0.12))" />
        <Controls v-if="showControls" :show-interactive="false" position="top-left" />
        <MiniMap
          v-if="showMinimap"
          :pannable="true"
          :zoomable="true"
          :node-color="minimapNodeColor"
          :width="120"
          :height="80"
        />
      </VueFlow>
    </div>
  </ClientOnly>
</template>

<script setup>
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

import LayerNode from './nodes/LayerNode.vue'
import ModuleNode from './nodes/ModuleNode.vue'
import StateNode from './nodes/StateNode.vue'
import ProcessNode from './nodes/ProcessNode.vue'
import GroupNode from './nodes/GroupNode.vue'

defineProps({
  nodes: { type: Array, required: true },
  edges: { type: Array, required: true },
  height: { type: String, default: '500px' },
  showMinimap: { type: Boolean, default: true },
  showControls: { type: Boolean, default: true },
  fitView: { type: Boolean, default: true },
})

const nodeTypes = {
  layer: LayerNode,
  module: ModuleNode,
  state: StateNode,
  process: ProcessNode,
  group: GroupNode,
}

const defaultEdgeOptions = {
  type: 'smoothstep',
  animated: false,
  pathOptions: { borderRadius: 12, offset: 15 },
  style: { strokeWidth: 1.5 },
  labelBgStyle: {
    fill: 'var(--flow-edge-label-bg, #fff)',
    fillOpacity: 0.92,
  },
  labelStyle: {
    fontSize: 11,
    fontWeight: 600,
    fontFamily: "'Inter', sans-serif",
    fill: 'var(--flow-edge-label-color, #4a5568)',
  },
  labelBgPadding: [8, 5],
  labelBgBorderRadius: 6,
}

const minimapNodeColor = (node) => {
  const colors = {
    layer: '#6b8f00',
    module: '#4a6b00',
    state: '#D4FF3B',
    process: '#90bd00',
    group: 'rgba(212, 255, 59, 0.3)',
  }
  return colors[node.type] || '#6b8f00'
}

const onDragStart = (event) => {
  const el = event.event?.target?.closest?.('.vue-flow__node')
  if (el) el.classList.add('dragging')
}

const onDragStop = (event) => {
  const el = event.event?.target?.closest?.('.vue-flow__node')
  if (el) el.classList.remove('dragging')
}
</script>
