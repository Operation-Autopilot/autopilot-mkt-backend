<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="550px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'client',
    type: 'process',
    position: { x: 200, y: 0 },
    data: { step: '1', label: 'Client Request' },
  },
  {
    id: 'middleware',
    type: 'process',
    position: { x: 200, y: 100 },
    data: { step: '2', label: 'Middleware', sublabel: 'CORS, error handling' },
  },
  {
    id: 'router',
    type: 'process',
    position: { x: 200, y: 200 },
    data: { step: '3', label: 'Router', sublabel: 'Route matching, input validation' },
  },
  {
    id: 'depends',
    type: 'process',
    position: { x: 200, y: 300 },
    data: { step: '4', label: 'Depends()', sublabel: 'Auth verification, client injection' },
  },
  {
    id: 'service',
    type: 'layer',
    position: { x: 200, y: 400 },
    data: { icon: '\u2699\uFE0F', label: 'Service Layer', sublabel: 'Business logic' },
  },
  {
    id: 'response',
    type: 'state',
    position: { x: 200, y: 500 },
    data: { label: 'JSON Response', variant: 'end' },
  },
]

const edges = [
  { id: 'e1', source: 'client', target: 'middleware' },
  { id: 'e2', source: 'middleware', target: 'router' },
  { id: 'e3', source: 'router', target: 'depends' },
  { id: 'e4', source: 'depends', target: 'service', animated: true },
  { id: 'e5', source: 'service', target: 'response', animated: true },
]
</script>
