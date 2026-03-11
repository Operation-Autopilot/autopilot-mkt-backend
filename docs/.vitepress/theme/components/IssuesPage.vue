<script setup>
import { useDmmsData } from '../composables/useDmmsData.js'
const { data, loading, error, reload } = useDmmsData('issues')
</script>

<template>
  <div v-if="loading" class="dmms-loading">Loading live data…</div>
  <div v-else-if="error" class="dmms-error">
    Failed to load live data: {{ error }}.
    <button class="dmms-retry" @click="reload">Retry</button>
  </div>
  <template v-else-if="data">
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-value">{{ data.total }}</div><div class="stat-label">Total</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.open }}</div><div class="stat-label">Open</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.resolved }}</div><div class="stat-label">Resolved</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.critical }}</div><div class="stat-label">Critical</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.high }}</div><div class="stat-label">High</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.medium }}</div><div class="stat-label">Medium</div></div>
      <div class="stat-card"><div class="stat-value">{{ data.low }}</div><div class="stat-label">Low</div></div>
    </div>

    <h2>Open Issues</h2>
    <p v-if="!data.openRows.length"><em>None.</em></p>
    <table v-else class="dmms-table">
      <thead>
        <tr><th>ID</th><th>Title</th><th>Severity</th><th>Category</th><th>Files</th></tr>
      </thead>
      <tbody>
        <tr v-for="r in data.openRows" :key="r.id">
          <td>{{ r.id }}</td>
          <td>{{ r.title }}</td>
          <td><span :class="'badge-' + r.severity">{{ r.severity }}</span></td>
          <td>{{ r.category }}</td>
          <td>{{ r.files || '--' }}</td>
        </tr>
      </tbody>
    </table>

    <details>
      <summary>Show {{ data.resolvedRows.length }} resolved issues</summary>
      <p v-if="!data.resolvedRows.length"><em>None.</em></p>
      <table v-else class="dmms-table">
        <thead>
          <tr><th>ID</th><th>Title</th><th>Severity</th><th>Category</th><th>Files</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in data.resolvedRows" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.title }}</td>
            <td><span :class="'badge-' + r.severity">{{ r.severity }}</span></td>
            <td>{{ r.category }}</td>
            <td>{{ r.files || '--' }}</td>
          </tr>
        </tbody>
      </table>
    </details>
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
.dmms-table { width: 100%; border-collapse: collapse; margin: 0.5rem 0 1rem; font-size: 0.875rem; }
.dmms-table th, .dmms-table td { text-align: left; padding: 0.5rem 0.75rem; border: 1px solid var(--vp-c-divider); }
.dmms-table th { background: var(--vp-c-bg-alt); font-weight: 600; }
.dmms-table tr:hover td { background: var(--vp-c-bg-soft); }
</style>
