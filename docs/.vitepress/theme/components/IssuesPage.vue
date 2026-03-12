<script setup>
import { ref } from 'vue'
import { useDmmsData } from '../composables/useDmmsData.js'
const { data, loading, error, reload } = useDmmsData('issues')
const expanded = ref(new Set())

function toggle(id) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
  expanded.value = new Set(expanded.value)
}
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
        <template v-for="r in data.openRows" :key="r.id">
          <tr :class="{ 'row-clickable': r.description }" @click="r.description && toggle(r.id)">
            <td>{{ r.id }}</td>
            <td>
              {{ r.title }}
              <span v-if="r.description" class="expand-hint">{{ expanded.has(r.id) ? '▾' : '▸' }}</span>
            </td>
            <td><span :class="'badge-' + r.severity">{{ r.severity }}</span></td>
            <td>{{ r.category }}</td>
            <td>{{ r.files || '--' }}</td>
          </tr>
          <tr v-if="expanded.has(r.id) && r.description" class="desc-row">
            <td colspan="5" class="desc-content">{{ r.description }}</td>
          </tr>
        </template>
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
          <template v-for="r in data.resolvedRows" :key="r.id">
            <tr :class="{ 'row-clickable': r.description }" @click="r.description && toggle('r_' + r.id)">
              <td>{{ r.id }}</td>
              <td>
                {{ r.title }}
                <span v-if="r.description" class="expand-hint">{{ expanded.has('r_' + r.id) ? '▾' : '▸' }}</span>
              </td>
              <td><span :class="'badge-' + r.severity">{{ r.severity }}</span></td>
              <td>{{ r.category }}</td>
              <td>{{ r.files || '--' }}</td>
            </tr>
            <tr v-if="expanded.has('r_' + r.id) && r.description" class="desc-row">
              <td colspan="5" class="desc-content">{{ r.description }}</td>
            </tr>
          </template>
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
.row-clickable { cursor: pointer; }
.expand-hint { color: var(--vp-c-text-3); font-size: 0.75rem; margin-left: 0.35rem; }
.desc-row td { background: var(--vp-c-bg-soft); }
.desc-content { white-space: pre-wrap; font-size: 0.8125rem; color: var(--vp-c-text-2); line-height: 1.5; padding: 0.75rem 0.75rem 0.75rem 1.5rem; border-left: 3px solid var(--vp-c-brand-1); }
</style>
