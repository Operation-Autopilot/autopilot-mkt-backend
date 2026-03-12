<script setup>
import { computed } from 'vue'
import { data as stats } from '../../loaders/project-stats.data.js'
import { useDmmsData } from '../composables/useDmmsData.js'

const { data: dmmsStats } = useDmmsData('stats', stats.dmms)

const items = computed(() => [
  { label: 'Issues tracked', value: dmmsStats.value?.issues ?? 0 },
  { label: 'Tasks', value: dmmsStats.value?.tasks ?? 0 },
  { label: 'Audit sessions', value: dmmsStats.value?.sessions ?? 0 },
  { label: 'Research entries', value: dmmsStats.value?.research ?? 0 },
  { label: 'Backend services', value: stats.backend?.serviceFiles ?? 0 },
  { label: 'Frontend components', value: stats.frontend?.componentFiles ?? 0 },
  { label: 'Test files', value: stats.tests?.totalTestFiles ?? 0 },
  { label: 'Test cases', value: stats.tests?.testCaseCount ?? 0 },
])
</script>

<template>
  <div class="stats-grid">
    <div v-for="item in items" :key="item.label" class="stat-card">
      <div class="stat-value">{{ item.value }}</div>
      <div class="stat-label">{{ item.label }}</div>
    </div>
  </div>
</template>
