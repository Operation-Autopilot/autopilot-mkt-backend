import DefaultTheme from 'vitepress/theme'
import './custom.css'

import StatsGrid from './components/StatsGrid.vue'
import ProductHierarchy from './components/ProductHierarchy.vue'
import ServiceInventoryTable from './components/ServiceInventoryTable.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('StatsGrid', StatsGrid)
    app.component('ProductHierarchy', ProductHierarchy)
    app.component('ServiceInventoryTable', ServiceInventoryTable)
  },
}
