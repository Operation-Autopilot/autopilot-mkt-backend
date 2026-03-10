<script setup>
import { data as stats } from '../../loaders/project-stats.data.js'

const items = [
  { label: 'Issues tracked', value: stats.dmms?.issues ?? 0 },
  { label: 'Tasks', value: stats.dmms?.tasks ?? 0 },
  { label: 'Audit sessions', value: stats.dmms?.sessions ?? 0 },
  { label: 'Research entries', value: stats.dmms?.research ?? 0 },
  { label: 'Backend services', value: stats.backend?.serviceFiles ?? 0 },
  { label: 'Frontend components', value: stats.frontend?.componentFiles ?? 0 },
  { label: 'Test files', value: stats.tests?.totalTestFiles ?? 0 },
  { label: 'Test cases', value: stats.tests?.testCaseCount ?? 0 },
]
</script>

<template>
  <div class="stats-grid">
    <div v-for="item in items" :key="item.label" class="stat-card">
      <div class="stat-value">{{ item.value }}</div>
      <div class="stat-label">{{ item.label }}</div>
    </div>
  </div>
</template>
