<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="450px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  // Phase states
  {
    id: 'discovery',
    type: 'state',
    position: { x: 0, y: 0 },
    data: { label: 'Discovery', variant: 'start', handleRight: true },
  },
  {
    id: 'roi',
    type: 'state',
    position: { x: 280, y: 0 },
    data: { label: 'ROI', handleLeft: true, handleRight: true },
  },
  {
    id: 'greenlight',
    type: 'state',
    position: { x: 560, y: 0 },
    data: { label: 'Greenlight', variant: 'end', handleLeft: true },
  },

  // Discovery components
  {
    id: 'agent-chat-d',
    type: 'module',
    position: { x: 0, y: 110 },
    data: { label: 'AgentChat', sublabel: 'AI asks questions' },
  },
  {
    id: 'robot-marketplace',
    type: 'module',
    position: { x: 0, y: 190 },
    data: { label: 'RobotMarketplace', sublabel: 'Browse catalog' },
  },
  {
    id: 'profile-widget',
    type: 'module',
    position: { x: 0, y: 270 },
    data: { label: 'ProfileWidget', sublabel: 'Editable answer cards' },
  },

  // ROI components
  {
    id: 'agent-chat-r',
    type: 'module',
    position: { x: 280, y: 110 },
    data: { label: 'AgentChat', sublabel: 'Walks through analysis' },
  },
  {
    id: 'roi-view',
    type: 'module',
    position: { x: 280, y: 190 },
    data: { label: 'ROIView', sublabel: 'Savings & payback' },
  },

  // Greenlight components
  {
    id: 'agent-chat-g',
    type: 'module',
    position: { x: 560, y: 110 },
    data: { label: 'AgentChat', sublabel: 'Guides checkout' },
  },
  {
    id: 'greenlight-view',
    type: 'module',
    position: { x: 560, y: 190 },
    data: { label: 'GreenlightView', sublabel: 'Summary & Stripe checkout' },
  },
]

const edges = [
  { id: 'e-d-r', source: 'discovery', target: 'roi', sourceHandle: 'right', targetHandle: 'left', animated: true, label: 'Robot selected' },
  { id: 'e-r-g', source: 'roi', target: 'greenlight', sourceHandle: 'right', targetHandle: 'left', animated: true, label: 'ROI approved' },
  { id: 'e-d-chat', source: 'discovery', target: 'agent-chat-d' },
  { id: 'e-d-mkt', source: 'discovery', target: 'robot-marketplace' },
  { id: 'e-d-prof', source: 'discovery', target: 'profile-widget' },
  { id: 'e-r-chat', source: 'roi', target: 'agent-chat-r' },
  { id: 'e-r-view', source: 'roi', target: 'roi-view' },
  { id: 'e-g-chat', source: 'greenlight', target: 'agent-chat-g' },
  { id: 'e-g-view', source: 'greenlight', target: 'greenlight-view' },
]
</script>
