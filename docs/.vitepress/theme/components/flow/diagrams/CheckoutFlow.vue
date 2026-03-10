<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="300px" :showMinimap="false" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'frontend',
    type: 'process',
    position: { x: 0, y: 50 },
    data: { step: '1', label: 'Frontend', sublabel: 'Initiate checkout', handleRight: true },
  },
  {
    id: 'checkout-svc',
    type: 'module',
    position: { x: 200, y: 50 },
    data: { label: 'CheckoutService', sublabel: 'Create session', handleLeft: true, handleRight: true },
  },
  {
    id: 'stripe',
    type: 'layer',
    position: { x: 400, y: 50 },
    data: { icon: '\uD83D\uDCB3', label: 'Stripe', sublabel: 'Hosted checkout page', handleLeft: true, handleRight: true },
  },
  {
    id: 'webhook',
    type: 'layer',
    position: { x: 600, y: 50 },
    data: { icon: '\uD83D\uDD14', label: 'Webhook', sublabel: 'Confirm payment', handleLeft: true },
  },
  {
    id: 'update-order',
    type: 'state',
    position: { x: 600, y: 170 },
    data: { label: 'Update order status', variant: 'end' },
  },
]

const edges = [
  { id: 'e1', source: 'frontend', target: 'checkout-svc', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e2', source: 'checkout-svc', target: 'stripe', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e3', source: 'stripe', target: 'webhook', sourceHandle: 'right', targetHandle: 'left', animated: true },
  { id: 'e4', source: 'webhook', target: 'update-order' },
]
</script>
