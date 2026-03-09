<template>
  <FlowDiagram :nodes="nodes" :edges="edges" height="700px" />
</template>

<script setup>
import FlowDiagram from '../FlowDiagram.vue'

const nodes = [
  // Browser group
  {
    id: 'grp-browser',
    type: 'group',
    position: { x: 60, y: 0 },
    style: { width: '520px', height: '110px' },
    data: { label: 'Browser', width: 520, height: 110 },
  },
  {
    id: 'react-spa',
    type: 'layer',
    position: { x: 80, y: 35 },
    parentNode: 'grp-browser',
    expandParent: true,
    data: { icon: '\u269B', label: 'React 18 SPA', sublabel: 'React Query + Context (Session, Auth)' },
  },

  // FastAPI group
  {
    id: 'grp-fastapi',
    type: 'group',
    position: { x: 60, y: 170 },
    style: { width: '520px', height: '160px' },
    data: {
      label: 'FastAPI Application Server',
      width: 520,
      height: 160,
      borderColor: 'rgba(144, 189, 0, 0.4)',
      bgColor: 'rgba(144, 189, 0, 0.04)',
    },
  },
  {
    id: 'routers',
    type: 'module',
    position: { x: 20, y: 40 },
    parentNode: 'grp-fastapi',
    expandParent: true,
    data: { label: 'Routers', sublabel: 'routes/' },
  },
  {
    id: 'services',
    type: 'module',
    position: { x: 180, y: 40 },
    parentNode: 'grp-fastapi',
    expandParent: true,
    data: { label: 'Service Layer', sublabel: 'services/' },
  },
  {
    id: 'ext-clients',
    type: 'module',
    position: { x: 340, y: 40 },
    parentNode: 'grp-fastapi',
    expandParent: true,
    data: { label: 'External Clients' },
  },
  {
    id: 'middleware',
    type: 'process',
    position: { x: 20, y: 100 },
    parentNode: 'grp-fastapi',
    expandParent: true,
    data: { label: 'Middleware', sublabel: 'Auth / Error handling' },
  },

  // External services
  {
    id: 'supabase',
    type: 'layer',
    position: { x: 0, y: 400 },
    data: { icon: '\uD83D\uDDC4\uFE0F', label: 'Supabase PostgreSQL', sublabel: 'Profiles, Sessions, Conversations, RLS' },
  },
  {
    id: 'pinecone',
    type: 'layer',
    position: { x: 260, y: 400 },
    data: { icon: '\uD83C\uDF32', label: 'Pinecone', sublabel: 'Product embeddings, Semantic search' },
  },
  {
    id: 'openai',
    type: 'layer',
    position: { x: 0, y: 510 },
    data: { icon: '\uD83E\uDDE0', label: 'OpenAI GPT-4o', sublabel: 'Agent, Profile extraction, RAG' },
  },
  {
    id: 'stripe',
    type: 'layer',
    position: { x: 260, y: 510 },
    data: { icon: '\uD83D\uDCB3', label: 'Stripe', sublabel: 'Checkout, Payments, Webhooks' },
  },
]

const edges = [
  { id: 'e-react-routers', source: 'react-spa', target: 'routers', label: 'HTTPS REST', animated: true },
  { id: 'e-routers-services', source: 'routers', target: 'services' },
  { id: 'e-services-ext', source: 'services', target: 'ext-clients' },
  { id: 'e-ext-supabase', source: 'ext-clients', target: 'supabase', animated: true },
  { id: 'e-ext-pinecone', source: 'ext-clients', target: 'pinecone', animated: true },
  { id: 'e-ext-openai', source: 'ext-clients', target: 'openai', animated: true },
  { id: 'e-ext-stripe', source: 'ext-clients', target: 'stripe', animated: true },
]
</script>
