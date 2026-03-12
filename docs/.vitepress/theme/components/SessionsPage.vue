<script setup>
import { useDmmsData } from '../composables/useDmmsData.js'
const { data, loading, error, reload } = useDmmsData('sessions')
</script>

<template>
  <div v-if="loading" class="dmms-loading">Loading live data…</div>
  <div v-else-if="error" class="dmms-error">
    Failed to load live data: {{ error }}.
    <button class="dmms-retry" @click="reload">Retry</button>
  </div>
  <template v-else-if="data">
    <p v-if="!data.rows.length"><em>No audit sessions yet.</em></p>
    <table v-else class="dmms-table">
      <thead>
        <tr><th>Date</th><th>Type</th><th>Summary</th><th>Issues</th><th>Tasks</th></tr>
      </thead>
      <tbody>
        <tr v-for="(r, i) in data.rows" :key="i">
          <td>{{ r.created_at ? r.created_at.split(' ')[0] : '--' }}</td>
          <td>{{ r.session_type }}</td>
          <td>{{ r.summary }}</td>
          <td>{{ r.issues_logged }}</td>
          <td>{{ r.tasks_created }}</td>
        </tr>
      </tbody>
    </table>
  </template>
  <div v-else class="dmms-empty">
    No data. Run <code>npm run docs:generate</code> to seed.
  </div>
</template>

<style scoped>
.dmms-loading { color: var(--vp-c-text-3); font-style: italic; padding: 1rem 0; }
.dmms-error { color: var(--vp-c-danger-1, #e53e3e); padding: 1rem 0; }
.dmms-retry { cursor: pointer; padding: 0.25rem 0.75rem; border-radius: 4px; border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg-alt); font-size: 0.875rem; margin-left: 0.5rem; }
.dmms-retry:hover { background: var(--vp-c-bg-mute); }
.dmms-empty { color: var(--vp-c-text-3); font-style: italic; padding: 1rem 0; }
.dmms-table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; font-size: 0.875rem; }
.dmms-table th, .dmms-table td { text-align: left; padding: 0.5rem 0.75rem; border: 1px solid var(--vp-c-divider); }
.dmms-table th { background: var(--vp-c-bg-alt); font-weight: 600; }
.dmms-table tr:hover td { background: var(--vp-c-bg-soft); }
</style>
