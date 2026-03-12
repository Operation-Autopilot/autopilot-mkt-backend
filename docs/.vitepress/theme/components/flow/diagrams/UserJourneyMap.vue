<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="450px" :showMinimap="false" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const dashedStyle = { strokeDasharray: '5 5', strokeWidth: 1.5 }

const nodes = [
  // Storage band (top, y=10)
  {
    id: 'anon-session',
    type: 'layer',
    position: { x: 300, y: 10 },
    data: { label: 'Anonymous Session', sublabel: 'sessions table + cookie', handleLeft: true, handleRight: true },
  },
  {
    id: 'auth-profile',
    type: 'layer',
    position: { x: 900, y: 10 },
    data: { label: 'Discovery Profile', sublabel: 'discovery_profiles table', handleLeft: true, handleRight: true },
  },

  // Main happy path (middle, y=170)
  {
    id: 'visitor',
    type: 'state',
    position: { x: 0, y: 170 },
    data: { label: 'Visitor Arrives', variant: 'start' },
  },
  {
    id: 'discovery',
    type: 'process',
    position: { x: 220, y: 170 },
    data: { step: '1', label: 'Discovery', sublabel: 'Chat Q&A \u00b7 7 questions', handleLeft: true, handleRight: true },
  },
  {
    id: 'roi',
    type: 'process',
    position: { x: 520, y: 170 },
    data: { step: '2', label: 'ROI Analysis', sublabel: 'Top-3 robots \u00b7 savings', handleLeft: true, handleRight: true },
  },
  {
    id: 'greenlight',
    type: 'process',
    position: { x: 800, y: 170 },
    data: { step: '3', label: 'Greenlight', sublabel: 'Team \u00b7 payment method', handleLeft: true, handleRight: true },
  },
  {
    id: 'checkout',
    type: 'process',
    position: { x: 1060, y: 170 },
    data: { step: '4', label: 'Checkout', sublabel: 'Stripe or Gynger', handleLeft: true, handleRight: true },
  },
  {
    id: 'complete',
    type: 'state',
    position: { x: 1300, y: 170 },
    data: { label: 'Order Created', variant: 'end' },
  },

  // Auth branch (bottom, y=350)
  {
    id: 'auth-gate',
    type: 'process',
    position: { x: 800, y: 350 },
    data: { label: 'Auth Required', sublabel: 'Not logged in \u2192 modal', handleLeft: true, handleRight: true },
  },
  {
    id: 'auth-modal',
    type: 'module',
    position: { x: 1020, y: 350 },
    data: { label: 'Signup / Login', sublabel: 'Tokens \u2192 localStorage', handleLeft: true, handleRight: true },
  },
  {
    id: 'claim',
    type: 'module',
    position: { x: 1240, y: 350 },
    data: { label: 'Session Claim', sublabel: 'POST /sessions/claim', handleLeft: true, handleRight: true },
  },
]

const edges = [
  // Main happy path (animated)
  { id: 'e-v-d',    source: 'visitor',    target: 'discovery', targetHandle: 'left', animated: true },
  { id: 'e-d-r',    source: 'discovery',  target: 'roi',       sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e-r-g',    source: 'roi',        target: 'greenlight', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e-g-c',    source: 'greenlight', target: 'checkout',  sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e-c-done', source: 'checkout',   target: 'complete',  sourceHandle: 'right', animated: true },

  // Storage connections (dashed — data persisted here)
  { id: 'e-v-anon', source: 'visitor',   target: 'anon-session', style: dashedStyle, label: 'data here' },
  { id: 'e-d-anon', source: 'discovery', target: 'anon-session', style: dashedStyle },
  { id: 'e-r-anon', source: 'roi',       target: 'anon-session', style: dashedStyle },

  // Auth branch
  { id: 'e-g-auth',     source: 'greenlight', target: 'auth-gate',  label: 'not logged in' },
  { id: 'e-auth-modal', source: 'auth-gate',  target: 'auth-modal', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e-modal-claim',source: 'auth-modal', target: 'claim',      sourceHandle: 'right', targetHandle: 'left', animated: true },

  // Claim merges and routes back
  { id: 'e-claim-profile',  source: 'claim',        target: 'auth-profile', style: dashedStyle, label: 'merged into' },
  { id: 'e-claim-checkout', source: 'claim',         target: 'checkout',    animated: true },
  { id: 'e-profile-checkout',source: 'auth-profile', target: 'checkout',    style: dashedStyle },
]
</script>
