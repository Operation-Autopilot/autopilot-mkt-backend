<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="450px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  // Problem side
  {
    id: 'grp-problem',
    type: 'group',
    position: { x: 0, y: 0 },
    style: { width: '280px', height: '380px' },
    data: { label: 'Problem: Single Client', width: 280, height: 380, borderColor: 'rgba(225, 112, 85, 0.4)', bgColor: 'rgba(225, 112, 85, 0.04)' },
  },
  {
    id: 'sign-in',
    type: 'process',
    position: { x: 40, y: 40 },
    parentNode: 'grp-problem',
    expandParent: true,
    data: { step: '1', label: 'sign_in(user_creds)' },
  },
  {
    id: 'set-session',
    type: 'process',
    position: { x: 40, y: 120 },
    parentNode: 'grp-problem',
    expandParent: true,
    data: { step: '2', label: 'set_session(user_jwt)', sublabel: 'Header OVERWRITTEN' },
  },
  {
    id: 'query-fail',
    type: 'state',
    position: { x: 40, y: 210 },
    parentNode: 'grp-problem',
    expandParent: true,
    data: { label: 'table("admin_data")', sublabel: 'FAILS: RLS denies access', variant: 'end' },
  },

  // Solution side
  {
    id: 'grp-solution',
    type: 'group',
    position: { x: 340, y: 0 },
    style: { width: '360px', height: '380px' },
    data: { label: 'Solution: Two Clients', width: 360, height: 380, borderColor: 'rgba(144, 189, 0, 0.4)', bgColor: 'rgba(144, 189, 0, 0.04)' },
  },
  {
    id: 'singleton',
    type: 'layer',
    position: { x: 20, y: 50 },
    parentNode: 'grp-solution',
    expandParent: true,
    data: { icon: '\uD83D\uDDC4\uFE0F', label: 'Singleton Client', sublabel: 'service_role_key → bypasses RLS' },
  },
  {
    id: 'fresh-client',
    type: 'layer',
    position: { x: 20, y: 160 },
    parentNode: 'grp-solution',
    expandParent: true,
    data: { icon: '\uD83D\uDD11', label: 'Fresh Auth Client', sublabel: 'sign_in → returns JWT → discarded' },
  },
  {
    id: 'query-ok',
    type: 'state',
    position: { x: 50, y: 270 },
    parentNode: 'grp-solution',
    expandParent: true,
    data: { label: 'WORKS', sublabel: 'No header contamination', variant: 'start' },
  },
]

const edges = [
  { id: 'e1', source: 'sign-in', target: 'set-session' },
  { id: 'e2', source: 'set-session', target: 'query-fail', animated: true },
  { id: 'e3', source: 'singleton', target: 'query-ok' },
  { id: 'e4', source: 'fresh-client', target: 'query-ok' },
]
</script>
