<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="550px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'profiles',
    type: 'layer',
    position: { x: 250, y: 0 },
    data: { icon: '\uD83D\uDC64', label: 'profiles', sublabel: 'User profile data' },
  },
  {
    id: 'companies',
    type: 'module',
    position: { x: 0, y: 120 },
    data: { label: 'companies', sublabel: 'Via company_members join' },
  },
  {
    id: 'company-members',
    type: 'module',
    position: { x: 0, y: 220 },
    data: { label: 'company_members', sublabel: 'Profile ↔ Company join' },
  },
  {
    id: 'conversations',
    type: 'module',
    position: { x: 180, y: 120 },
    data: { label: 'conversations', sublabel: 'Chat threads' },
  },
  {
    id: 'messages',
    type: 'module',
    position: { x: 180, y: 220 },
    data: { label: 'messages', sublabel: 'Individual messages' },
  },
  {
    id: 'sessions',
    type: 'module',
    position: { x: 350, y: 120 },
    data: { label: 'sessions', sublabel: 'Anonymous sessions' },
  },
  {
    id: 'discovery-profiles',
    type: 'module',
    position: { x: 350, y: 220 },
    data: { label: 'discovery_profiles', sublabel: 'AI-extracted profiles' },
  },
  {
    id: 'orders',
    type: 'module',
    position: { x: 510, y: 120 },
    data: { label: 'orders', sublabel: 'Completed purchases' },
  },
  {
    id: 'robots',
    type: 'layer',
    position: { x: 510, y: 260 },
    data: { icon: '\uD83E\uDD16', label: 'robots', sublabel: 'Standalone catalog' },
  },
]

const edges = [
  { id: 'e1', source: 'profiles', target: 'companies' },
  { id: 'e2', source: 'companies', target: 'company-members' },
  { id: 'e3', source: 'profiles', target: 'conversations' },
  { id: 'e4', source: 'conversations', target: 'messages' },
  { id: 'e5', source: 'profiles', target: 'sessions' },
  { id: 'e6', source: 'profiles', target: 'discovery-profiles' },
  { id: 'e7', source: 'profiles', target: 'orders' },
  { id: 'e8', source: 'orders', target: 'robots', animated: true, label: 'FK robot_id' },
]
</script>
