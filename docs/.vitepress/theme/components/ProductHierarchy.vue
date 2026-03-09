<script setup>
import { data } from '../../loaders/product-hierarchy.data.js'
import { withBase } from 'vitepress'

function progressPercent(completed, total) {
  if (!total) return 0
  return Math.round((completed / total) * 100)
}
</script>

<template>
  <div class="product-hierarchy" v-if="data.products.length">
    <div v-for="product in data.products" :key="product.id" class="hierarchy-product">
      <details open>
        <summary class="hierarchy-summary product-summary">
          <span class="hierarchy-icon">&#x1F680;</span>
          <strong>{{ product.name }}</strong>
          <span :class="'badge-' + product.status">{{ product.status }}</span>
          <span class="hierarchy-meta" v-if="product.description">{{ product.description }}</span>
        </summary>

        <div class="hierarchy-children">
          <div v-for="project in product.projects" :key="project.id" class="hierarchy-project">
            <details open>
              <summary class="hierarchy-summary project-summary">
                <span class="hierarchy-icon">&#x1F4C1;</span>
                <strong>{{ project.name }}</strong>
                <span :class="'badge-' + project.status">{{ project.status }}</span>
                <span class="hierarchy-count" v-if="project.taskCount">
                  {{ project.completedTasks }}/{{ project.taskCount }} tasks
                </span>
              </summary>

              <div class="hierarchy-children">
                <div
                  v-if="project.taskCount"
                  class="progress-bar-container"
                >
                  <div
                    class="progress-bar-fill"
                    :style="{ width: progressPercent(project.completedTasks, project.taskCount) + '%' }"
                  ></div>
                  <span class="progress-bar-label">{{ progressPercent(project.completedTasks, project.taskCount) }}%</span>
                </div>

                <div v-for="feature in project.features" :key="feature.id" class="hierarchy-feature">
                  <div class="hierarchy-summary feature-summary">
                    <span class="hierarchy-icon">&#x2699;&#xFE0F;</span>
                    <span>{{ feature.name }}</span>
                    <span :class="'badge-' + feature.status">{{ feature.status }}</span>
                    <span class="hierarchy-count" v-if="feature.taskCount">
                      {{ feature.completedTasks }}/{{ feature.taskCount }} tasks
                    </span>
                  </div>
                </div>

                <div v-if="!project.features.length" class="hierarchy-empty">
                  No features defined yet
                </div>
              </div>
            </details>
          </div>
        </div>
      </details>
    </div>

    <div class="hierarchy-stats">
      <a class="stat-pill" :href="withBase('/status/sprints')"><strong>{{ data.stats.totalTasks }}</strong> tasks</a>
      <a class="stat-pill" :href="withBase('/status/sprints')"><strong>{{ data.stats.completedTasks }}</strong> completed</a>
      <a class="stat-pill" :href="withBase('/status/roadmap')"><strong>{{ data.stats.totalFeatures }}</strong> features</a>
      <a class="stat-pill" :href="withBase('/status/issues')"><strong>{{ data.stats.totalIssues }}</strong> issues tracked</a>
      <a class="stat-pill" :href="withBase('/status/issues')"><strong>{{ data.stats.resolvedIssues }}</strong> resolved</a>
    </div>
  </div>
  <div v-else class="hierarchy-empty">
    No hierarchy data available. Run <code>node scripts/generate-dmms-docs.mjs</code> to generate.
  </div>
</template>

<style scoped>
.product-hierarchy { margin: 1rem 0; }
.hierarchy-summary { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; padding: 0.5rem 0; cursor: pointer; list-style: none; }
.hierarchy-summary::-webkit-details-marker { display: none; }
details > .hierarchy-summary::before { content: '\25B6'; font-size: 0.65rem; transition: transform 0.15s; color: var(--vp-c-text-3); }
details[open] > .hierarchy-summary::before { transform: rotate(90deg); }
.product-summary { font-size: 1.1rem; border-bottom: 2px solid var(--vp-c-divider); padding-bottom: 0.75rem; margin-bottom: 0.25rem; }
.project-summary { font-size: 0.95rem; }
.feature-summary { font-size: 0.875rem; cursor: default; padding: 0.25rem 0; }
.hierarchy-icon { font-size: 1rem; flex-shrink: 0; }
.hierarchy-meta { font-size: 0.8rem; color: var(--vp-c-text-3); font-style: italic; }
.hierarchy-count { font-size: 0.75rem; color: var(--vp-c-text-2); margin-left: auto; }
.hierarchy-children { padding-left: 1.5rem; border-left: 1px solid var(--vp-c-divider); margin-left: 0.5rem; }
.hierarchy-empty { font-size: 0.8rem; color: var(--vp-c-text-3); padding: 0.25rem 0; font-style: italic; }
.progress-bar-container { position: relative; height: 6px; background: var(--vp-c-bg-soft); border-radius: 3px; margin: 0.25rem 0 0.5rem; overflow: hidden; }
.progress-bar-fill { height: 100%; background: var(--vp-c-brand-1); border-radius: 3px; transition: width 0.3s ease; }
.progress-bar-label { position: absolute; right: 0; top: -1rem; font-size: 0.65rem; color: var(--vp-c-text-3); }
.hierarchy-stats { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid var(--vp-c-divider); }
.stat-pill { font-size: 0.75rem; padding: 0.25rem 0.75rem; border-radius: 999px; background: var(--vp-c-bg-soft); color: var(--vp-c-text-2); text-decoration: none; transition: background 0.2s ease; cursor: pointer; }
.stat-pill:hover { background: var(--vp-c-bg-mute); text-decoration: underline; }
.stat-pill strong { color: var(--vp-c-text-1); }
</style>
