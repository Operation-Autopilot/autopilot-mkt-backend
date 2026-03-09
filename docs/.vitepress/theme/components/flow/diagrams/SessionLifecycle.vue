<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="200px" :showMinimap="false" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'discovery',
    type: 'state',
    position: { x: 0, y: 50 },
    data: { label: 'Discovery', sublabel: 'Needs assessment', variant: 'start', handleRight: true },
  },
  {
    id: 'roi',
    type: 'state',
    position: { x: 250, y: 50 },
    data: { label: 'ROI', sublabel: 'Cost analysis', handleLeft: true, handleRight: true },
  },
  {
    id: 'greenlight',
    type: 'state',
    position: { x: 500, y: 50 },
    data: { label: 'Greenlight', sublabel: 'Purchase decision', variant: 'end', handleLeft: true },
  },
]

const edges = [
  { id: 'e1', source: 'discovery', target: 'roi', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e2', source: 'roi', target: 'greenlight', sourceHandle: 'right', targetHandle: 'left', animated: true },
]
</script>
