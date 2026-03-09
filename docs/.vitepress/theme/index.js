import DefaultTheme from 'vitepress/theme'
import { defineAsyncComponent } from 'vue'
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

    if (typeof window !== 'undefined') {
      app.component('SystemArchitecture', defineAsyncComponent(() =>
        import('./components/flow/diagrams/SystemArchitecture.vue')
      ))
      app.component('ConversationFlow', defineAsyncComponent(() =>
        import('./components/flow/diagrams/ConversationFlow.vue')
      ))
      app.component('RagPipeline', defineAsyncComponent(() =>
        import('./components/flow/diagrams/RagPipeline.vue')
      ))
      app.component('RequestPipeline', defineAsyncComponent(() =>
        import('./components/flow/diagrams/RequestPipeline.vue')
      ))
      app.component('AuthFlow', defineAsyncComponent(() =>
        import('./components/flow/diagrams/AuthFlow.vue')
      ))
      app.component('SessionLifecycle', defineAsyncComponent(() =>
        import('./components/flow/diagrams/SessionLifecycle.vue')
      ))
      app.component('ServiceComposition', defineAsyncComponent(() =>
        import('./components/flow/diagrams/ServiceComposition.vue')
      ))
      app.component('StateProviders', defineAsyncComponent(() =>
        import('./components/flow/diagrams/StateProviders.vue')
      ))
      app.component('CheckoutFlow', defineAsyncComponent(() =>
        import('./components/flow/diagrams/CheckoutFlow.vue')
      ))
      app.component('DatabaseSchema', defineAsyncComponent(() =>
        import('./components/flow/diagrams/DatabaseSchema.vue')
      ))
      app.component('PhaseSystem', defineAsyncComponent(() =>
        import('./components/flow/diagrams/PhaseSystem.vue')
      ))
      app.component('TwoClientPattern', defineAsyncComponent(() =>
        import('./components/flow/diagrams/TwoClientPattern.vue')
      ))
    }
  },
}
