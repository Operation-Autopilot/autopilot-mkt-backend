<script setup>
import { data as stats } from '../../loaders/project-stats.data.js'

const inventory = stats.backend?.serviceInventory || []
</script>

<template>
  <table v-if="inventory.length">
    <thead>
      <tr>
        <th>Service</th>
        <th>Lines</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="svc in inventory" :key="svc.file">
        <td><code>{{ svc.file }}</code></td>
        <td>{{ svc.lines }}</td>
        <td>{{ svc.description }}</td>
      </tr>
    </tbody>
  </table>
  <p v-else><em>No service inventory data available. Run <code>npm run docs:generate</code>.</em></p>
</template>
