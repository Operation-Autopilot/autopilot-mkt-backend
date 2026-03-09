<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="750px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  {
    id: 'user-msg',
    type: 'process',
    position: { x: 200, y: 0 },
    data: { step: '1', label: 'User types message', sublabel: 'Frontend input' },
  },
  {
    id: 'frontend-send',
    type: 'process',
    position: { x: 200, y: 90 },
    data: { step: '2', label: 'useConversation.sendMessage()', sublabel: 'POST /conversations/{session_id}/messages' },
  },
  {
    id: 'router',
    type: 'process',
    position: { x: 200, y: 180 },
    data: { step: '3', label: 'Router: conversations.py', sublabel: 'Validates input, injects auth + supabase' },
  },
  {
    id: 'store-msg',
    type: 'module',
    position: { x: 200, y: 270 },
    data: { label: 'Store user message', sublabel: 'conversations table' },
  },
  {
    id: 'context',
    type: 'module',
    position: { x: 200, y: 350 },
    data: { label: 'Reconstruct context', sublabel: 'History + Profile + Session metadata' },
  },
  {
    id: 'rag',
    type: 'layer',
    position: { x: 0, y: 430 },
    data: { icon: '\uD83D\uDD0D', label: 'RAG Search', sublabel: 'Embed → Pinecone → Top 5 matches' },
  },
  {
    id: 'agent',
    type: 'layer',
    position: { x: 300, y: 430 },
    data: { icon: '\uD83E\uDDE0', label: 'GPT-4o Agent', sublabel: 'System prompt + context + products' },
  },
  {
    id: 'extract',
    type: 'module',
    position: { x: 0, y: 530 },
    data: { label: 'Profile Extraction', sublabel: 'Structured JSON → discovery_profiles' },
  },
  {
    id: 'store-response',
    type: 'module',
    position: { x: 300, y: 530 },
    data: { label: 'Store assistant message', sublabel: 'conversations table' },
  },
  {
    id: 'frontend-render',
    type: 'process',
    position: { x: 200, y: 630 },
    data: { step: '7', label: 'React Query invalidated', sublabel: 'History re-fetched and rendered' },
  },
]

const edges = [
  { id: 'e1', source: 'user-msg', target: 'frontend-send' },
  { id: 'e2', source: 'frontend-send', target: 'router', animated: true },
  { id: 'e3', source: 'router', target: 'store-msg' },
  { id: 'e4', source: 'store-msg', target: 'context' },
  { id: 'e5', source: 'context', target: 'rag' },
  { id: 'e6', source: 'context', target: 'agent' },
  { id: 'e7', source: 'rag', target: 'agent', label: 'product context', animated: true },
  { id: 'e8', source: 'agent', target: 'store-response' },
  { id: 'e9', source: 'rag', target: 'extract' },
  { id: 'e10', source: 'store-response', target: 'frontend-render', animated: true },
  { id: 'e11', source: 'extract', target: 'frontend-render' },
]
</script>
