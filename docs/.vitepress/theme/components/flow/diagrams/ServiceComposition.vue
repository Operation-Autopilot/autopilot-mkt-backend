<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="350px" :showMinimap="false" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'conversation',
    type: 'layer',
    position: { x: 200, y: 0 },
    data: { icon: '\uD83D\uDCAC', label: 'ConversationService' },
  },
  {
    id: 'rag',
    type: 'module',
    position: { x: 0, y: 120 },
    data: { label: 'RagService', sublabel: 'Search product catalog' },
  },
  {
    id: 'agent',
    type: 'module',
    position: { x: 160, y: 120 },
    data: { label: 'AgentService', sublabel: 'Generate AI response' },
  },
  {
    id: 'profile-ext',
    type: 'module',
    position: { x: 320, y: 120 },
    data: { label: 'ProfileExtractionService', sublabel: 'Extract structured data' },
  },
  {
    id: 'session',
    type: 'module',
    position: { x: 480, y: 120 },
    data: { label: 'SessionService', sublabel: 'Update session phase' },
  },
]

const edges = [
  { id: 'e1', source: 'conversation', target: 'rag', animated: true },
  { id: 'e2', source: 'conversation', target: 'agent', animated: true },
  { id: 'e3', source: 'conversation', target: 'profile-ext', animated: true },
  { id: 'e4', source: 'conversation', target: 'session', animated: true },
]
</script>
