<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="500px" :showMinimap="false" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  // Nested provider groups
  {
    id: 'grp-query',
    type: 'group',
    position: { x: 50, y: 0 },
    style: { width: '480px', height: '420px' },
    data: { label: 'QueryClientProvider', width: 480, height: 420, borderColor: 'rgba(144, 189, 0, 0.3)', bgColor: 'rgba(144, 189, 0, 0.03)' },
  },
  {
    id: 'grp-auth',
    type: 'group',
    position: { x: 30, y: 40 },
    parentNode: 'grp-query',
    expandParent: true,
    style: { width: '420px', height: '340px' },
    data: { label: 'AuthProvider', width: 420, height: 340, borderColor: 'rgba(107, 143, 0, 0.4)', bgColor: 'rgba(107, 143, 0, 0.04)' },
  },
  {
    id: 'grp-session',
    type: 'group',
    position: { x: 30, y: 40 },
    parentNode: 'grp-auth',
    expandParent: true,
    style: { width: '360px', height: '260px' },
    data: { label: 'SessionProvider', width: 360, height: 260, borderColor: 'rgba(212, 255, 59, 0.4)', bgColor: 'rgba(212, 255, 59, 0.04)' },
  },
  {
    id: 'app-routes',
    type: 'layer',
    position: { x: 80, y: 80 },
    parentNode: 'grp-session',
    expandParent: true,
    data: { icon: '\uD83D\uDCF1', label: 'App Routes', sublabel: 'React component tree' },
  },

  // Data flow annotations
  {
    id: 'query-label',
    type: 'process',
    position: { x: 560, y: 40 },
    data: { label: 'TanStack React Query', sublabel: 'Server state cache' },
  },
  {
    id: 'auth-label',
    type: 'process',
    position: { x: 560, y: 150 },
    data: { label: 'Supabase Auth', sublabel: 'User object, tokens' },
  },
  {
    id: 'session-label',
    type: 'process',
    position: { x: 560, y: 260 },
    data: { label: 'Session State', sublabel: 'Phase, answers, selectedRobotId' },
  },
]

const edges = []
</script>
