<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="520px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'user-msg',
    type: 'process',
    position: { x: 200, y: 0 },
    data: { step: '1', label: 'User Message' },
  },
  {
    id: 'context',
    type: 'process',
    position: { x: 200, y: 90 },
    data: { step: '2', label: 'Context Reconstruction', sublabel: 'Message history' },
  },
  {
    id: 'embed',
    type: 'layer',
    position: { x: 200, y: 180 },
    data: { icon: '\uD83D\uDD22', label: 'OpenAI Embeddings API', sublabel: 'Text → Vector' },
  },
  {
    id: 'pinecone',
    type: 'layer',
    position: { x: 200, y: 280 },
    data: { icon: '\uD83C\uDF32', label: 'Pinecone Similarity Search', sublabel: 'Top-K product matches' },
  },
  {
    id: 'inject',
    type: 'process',
    position: { x: 200, y: 380 },
    data: { step: '5', label: 'Inject product context', sublabel: 'Into GPT-4o system prompt' },
  },
  {
    id: 'gpt',
    type: 'layer',
    position: { x: 200, y: 470 },
    data: { icon: '\uD83E\uDDE0', label: 'GPT-4o grounded response' },
  },
]

const edges = [
  { id: 'e1', source: 'user-msg', target: 'context' },
  { id: 'e2', source: 'context', target: 'embed', animated: true },
  { id: 'e3', source: 'embed', target: 'pinecone', animated: true },
  { id: 'e4', source: 'pinecone', target: 'inject' },
  { id: 'e5', source: 'inject', target: 'gpt', animated: true },
]
</script>
