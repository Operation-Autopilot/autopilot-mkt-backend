<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="480px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'browser',
    type: 'layer',
    position: { x: 0, y: 0 },
    data: { icon: '\uD83C\uDF10', label: 'Browser', sublabel: '1. Login request', handleRight: true },
  },
  {
    id: 'fastapi',
    type: 'layer',
    position: { x: 250, y: 0 },
    data: { icon: '\u26A1', label: 'FastAPI /auth/*', sublabel: '2. Forward credentials', handleLeft: true, handleRight: true },
  },
  {
    id: 'supabase-auth',
    type: 'layer',
    position: { x: 500, y: 0 },
    data: { icon: '\uD83D\uDD10', label: 'Supabase Auth', sublabel: '3. Verify credentials, 4. Return JWT', handleLeft: true },
  },
  {
    id: 'store-token',
    type: 'state',
    position: { x: 0, y: 130 },
    data: { label: '5. Store token', sublabel: 'Browser stores JWT' },
  },
  {
    id: 'label-subsequent',
    type: 'process',
    position: { x: 0, y: 240 },
    data: { label: 'Subsequent requests', sublabel: 'Authorization: Bearer <jwt>' },
  },
  {
    id: 'protected-route',
    type: 'layer',
    position: { x: 0, y: 340 },
    data: { icon: '\uD83D\uDD12', label: 'FastAPI Protected Route', handleRight: true },
  },
  {
    id: 'verify-jwt',
    type: 'layer',
    position: { x: 350, y: 340 },
    data: { icon: '\u2705', label: 'Supabase auth.get_user()', sublabel: 'Verify JWT', handleLeft: true },
  },
]

const edges = [
  { id: 'e1', source: 'browser', target: 'fastapi', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e2', source: 'fastapi', target: 'supabase-auth', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e3', source: 'browser', target: 'store-token' },
  { id: 'e4', source: 'store-token', target: 'label-subsequent' },
  { id: 'e5', source: 'label-subsequent', target: 'protected-route' },
  { id: 'e6', source: 'protected-route', target: 'verify-jwt', sourceHandle: 'right', targetHandle: 'left', animated: true },
]
</script>
