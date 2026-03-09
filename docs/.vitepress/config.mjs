import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Autopilot Marketplace',
  description: 'Agent-led procurement platform for enterprise robotic cleaning solutions — AI discovery, ROI visualization, and Stripe checkout',

  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap', rel: 'stylesheet' }],
  ],

  themeConfig: {
    siteTitle: 'Autopilot Marketplace',

    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Architecture', link: '/architecture/' },
      { text: 'Frontend', link: '/frontend/' },
      { text: 'Backend', link: '/backend/' },
      { text: 'API Reference', link: '/api-reference/' },
      { text: 'Testing', link: '/testing/' },
      { text: 'Status', link: '/status/' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Guide',
          items: [
            { text: 'Overview', link: '/guide/' },
            { text: 'Quick Start', link: '/guide/quickstart' },
            { text: 'Philosophy', link: '/guide/philosophy' },
            { text: 'Contributing', link: '/guide/contributing' },
          ],
        },
      ],
      '/architecture/': [
        {
          text: 'Architecture',
          items: [
            { text: 'Overview', link: '/architecture/' },
            { text: 'API Layer', link: '/architecture/api-layer' },
            { text: 'Service Layer', link: '/architecture/service-layer' },
            { text: 'State Management', link: '/architecture/state-management' },
            { text: 'Data Flow', link: '/architecture/data-flow' },
            { text: 'Authentication', link: '/architecture/authentication' },
          ],
        },
      ],
      '/frontend/': [
        {
          text: 'Frontend',
          items: [
            { text: 'Overview', link: '/frontend/' },
            { text: 'Components', link: '/frontend/components' },
            { text: 'State Management', link: '/frontend/state-management' },
            { text: 'UI Phases', link: '/frontend/ui-phases' },
            { text: 'Hooks', link: '/frontend/hooks' },
            { text: 'Mobile', link: '/frontend/mobile' },
            { text: 'Styling', link: '/frontend/styling' },
          ],
        },
      ],
      '/backend/': [
        {
          text: 'Backend',
          items: [
            { text: 'Overview', link: '/backend/' },
            { text: 'Routes', link: '/backend/routes' },
            { text: 'Services', link: '/backend/services' },
            { text: 'Schemas', link: '/backend/schemas' },
            { text: 'Database', link: '/backend/database' },
            { text: 'Supabase', link: '/backend/supabase' },
            { text: 'Stripe', link: '/backend/stripe' },
            { text: 'RAG', link: '/backend/rag' },
          ],
        },
      ],
      '/api-reference/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api-reference/' },
            { text: 'Auth', link: '/api-reference/auth' },
            { text: 'Sessions', link: '/api-reference/sessions' },
            { text: 'Conversations', link: '/api-reference/conversations' },
            { text: 'Profiles', link: '/api-reference/profiles' },
            { text: 'Companies', link: '/api-reference/companies' },
            { text: 'Robots', link: '/api-reference/robots' },
            { text: 'Checkout', link: '/api-reference/checkout' },
            { text: 'Discovery', link: '/api-reference/discovery' },
            { text: 'Webhooks', link: '/api-reference/webhooks' },
          ],
        },
      ],
      '/testing/': [
        {
          text: 'Testing',
          items: [
            { text: 'Overview', link: '/testing/' },
            { text: 'Backend Tests', link: '/testing/backend' },
            { text: 'Frontend Tests', link: '/testing/frontend' },
            { text: 'Patterns', link: '/testing/patterns' },
          ],
        },
      ],
      '/status/': [
        {
          text: 'Project Status',
          items: [
            { text: 'Overview', link: '/status/' },
            { text: 'Issues', link: '/status/issues' },
            { text: 'Sprints', link: '/status/sprints' },
            { text: 'Sessions', link: '/status/sessions' },
            { text: 'Research', link: '/status/research' },
            { text: 'Roadmap', link: '/status/roadmap' },
          ],
        },
      ],
    },

    search: {
      provider: 'local',
    },

    footer: {
      message: 'Built with VitePress. Autopilot Marketplace Documentation.',
      copyright: 'Autopilot',
    },

    outline: {
      level: [2, 3],
    },
  },

  markdown: {
    lineNumbers: true,
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
  },

  vite: {
    server: {
      port: 5174,
    },
    ssr: {
      noExternal: ['@vue-flow/core', '@vue-flow/background', '@vue-flow/controls', '@vue-flow/minimap'],
    },
  },
})
